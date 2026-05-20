#!/usr/bin/env python3
"""Build deterministic realistic-mode optimization frontier artifacts (F1.1)."""

from __future__ import annotations

import argparse
import copy
import math
import sys
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_json, write_json
except ImportError:
    from script_io import load_json, render_json, write_json
from typing import Any, Dict, List, Mapping, Sequence, Tuple

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.dag import contracts
from mission.baseline import build_output, load_claims_map
from mission.optimization import risk_envelope
from scripts.ci import parameter_evidence_validate

DEFAULT_OBJECTIVE_CONTRACT = Path("mission/objectives/objective_contract.v1.json")
DEFAULT_RISK_SPEC = Path("mission/objectives/risk_envelope.v1.json")
DEFAULT_BASELINE_SCENARIO = Path("mission/BASELINE_SCENARIO_v1.json")
DEFAULT_PARAMETER_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_PARAMETER_CLAIMS = Path("parameters/registry/parameter_claims.v1.json")
DEFAULT_EVIDENCE_SOURCES = Path("parameters/registry/evidence_sources.v1.json")
DEFAULT_FAILURE_SURFACE = Path("artifacts/failure_surface_baseline.v1.json")
DEFAULT_DETERMINISM_STATUS = Path("artifacts/determinism_status.json")
DEFAULT_SEARCH_SPACE_OUTPUT = Path("artifacts/optimization_search_space.v1.json")
DEFAULT_FRONTIER_OUTPUT = Path("artifacts/optimization_frontier_realistic.v1.json")

ALLOWED_TRUST = {"A", "B", "C"}
INTERNAL_PARAMETER_PREFIXES = ("code_literal.",)
PUBLIC_VISIBILITY = "public"
PUBLIC_SURFACE_OPTIMIZATION = "optimization"


def _is_internal_parameter_id(parameter_id: str) -> bool:
    return any(parameter_id.startswith(prefix) for prefix in INTERNAL_PARAMETER_PREFIXES)


def _public_surfaces(parameter: Mapping[str, Any]) -> set[str]:
    surfaces = parameter.get("public_surfaces")
    if not isinstance(surfaces, list):
        return set()
    return {str(surface) for surface in surfaces if isinstance(surface, str)}


def _has_visibility_metadata(parameter: Mapping[str, Any]) -> bool:
    return "visibility" in parameter or "public_surfaces" in parameter or "audit_scope" in parameter


def _is_audit_only_parameter(parameter: Mapping[str, Any]) -> bool:
    parameter_id = parameter.get("parameter_id")
    if isinstance(parameter_id, str) and _is_internal_parameter_id(parameter_id):
        return True
    return parameter.get("visibility") == "internal" or parameter.get("audit_scope") == "code_literal"


def _is_public_optimization_parameter(parameter: Mapping[str, Any]) -> bool:
    parameter_id = parameter.get("parameter_id")
    if not isinstance(parameter_id, str) or _is_internal_parameter_id(parameter_id):
        return False
    if not _has_visibility_metadata(parameter):
        return True
    return (
        parameter.get("visibility") == PUBLIC_VISIBILITY
        and PUBLIC_SURFACE_OPTIMIZATION in _public_surfaces(parameter)
    )


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _is_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _get_path(payload: Mapping[str, Any], dotted: str) -> float:
    cursor: Any = payload
    for key in dotted.split("."):
        cursor = cursor[key]
    if not _is_number(cursor):
        raise TypeError(f"{dotted} is not numeric")
    return float(cursor)


def _set_path(payload: Dict[str, Any], dotted: str, value: float) -> None:
    cursor: Any = payload
    keys = dotted.split(".")
    for key in keys[:-1]:
        cursor = cursor[key]
    cursor[keys[-1]] = float(value)


def _metric_available(contract: Mapping[str, Any], mode: str, metric: str) -> bool:
    objective_sets = contract.get("objective_sets", {})
    definitions = contract.get("definitions", {})
    mode_set = objective_sets.get(mode, {}) if isinstance(objective_sets, Mapping) else {}
    aggregation = mode_set.get("aggregation", {}) if isinstance(mode_set, Mapping) else {}
    dimensions = aggregation.get("dimensions")
    if isinstance(dimensions, list):
        metrics = dimensions
    else:
        metrics = aggregation.get("order", []) if isinstance(aggregation, Mapping) else []
    if metric not in metrics:
        return False

    definition = definitions.get(metric, {}) if isinstance(definitions, Mapping) else {}
    definition_status = definition.get("status") if isinstance(definition, Mapping) else None
    if definition_status == "N/A_v1":
        return False

    secondary = mode_set.get("secondary", []) if isinstance(mode_set, Mapping) else []
    if isinstance(secondary, list):
        for item in secondary:
            if isinstance(item, Mapping) and item.get("metric") == metric and item.get("status") == "N/A_v1":
                return False
    return True


def _available_metrics(contract: Mapping[str, Any], mode: str) -> List[str]:
    objective_sets = contract.get("objective_sets", {})
    mode_set = objective_sets.get(mode, {}) if isinstance(objective_sets, Mapping) else {}
    aggregation = mode_set.get("aggregation", {}) if isinstance(mode_set, Mapping) else {}
    dimensions = aggregation.get("dimensions")
    ordered = dimensions if isinstance(dimensions, list) else aggregation.get("order", [])
    if not isinstance(ordered, list):
        return []
    return [metric for metric in ordered if isinstance(metric, str) and _metric_available(contract, mode, metric)]


def _metric_directions(contract: Mapping[str, Any], mode: str) -> Dict[str, bool]:
    objective_sets = contract.get("objective_sets", {})
    mode_set = objective_sets.get(mode, {}) if isinstance(objective_sets, Mapping) else {}

    out: Dict[str, bool] = {}
    primary = mode_set.get("primary") if isinstance(mode_set, Mapping) else None
    if isinstance(primary, Mapping) and isinstance(primary.get("metric"), str):
        out[str(primary["metric"])] = bool(primary.get("maximize", True))

    secondary = mode_set.get("secondary", []) if isinstance(mode_set, Mapping) else []
    if isinstance(secondary, list):
        for item in secondary:
            if isinstance(item, Mapping) and isinstance(item.get("metric"), str):
                out[str(item["metric"])] = bool(item.get("maximize", True))

    return out


def _search_space(
    *,
    baseline: Mapping[str, Any],
    parameter_registry: Mapping[str, Any],
    parameter_claims: Mapping[str, Any],
    mode: str,
    seed: int,
) -> Dict[str, Any]:
    claim_by_id: Dict[str, Dict[str, Any]] = {
        str(item["parameter_id"]): dict(item)
        for item in parameter_claims.get("claims", [])
        if isinstance(item, Mapping) and isinstance(item.get("parameter_id"), str)
    }

    considered: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    excluded_internal_parameter_count = 0

    for entry in sorted(
        [item for item in parameter_registry.get("parameters", []) if isinstance(item, Mapping)],
        key=lambda item: str(item.get("parameter_id", "")),
    ):
        parameter_id = entry.get("parameter_id")
        if not isinstance(parameter_id, str) or not parameter_id:
            continue
        if not _is_public_optimization_parameter(entry):
            if _is_audit_only_parameter(entry):
                excluded_internal_parameter_count += 1
                continue
            excluded.append(
                {
                    "parameter_id": parameter_id,
                    "exclusion_reason": ["public_surface_not_optimization"],
                    "trust_grade": "UNKNOWN",
                    "domain": str(entry.get("domain", "")),
                }
            )
            continue
        if _is_internal_parameter_id(parameter_id):
            excluded_internal_parameter_count += 1
            continue

        reasons: List[str] = []
        claim = claim_by_id.get(parameter_id)

        if not bool(entry.get("affects_core_probability", False)):
            reasons.append("affects_core_probability_false")

        if str(entry.get("domain", "")) != mode:
            reasons.append("domain_not_realistic")

        if claim is None:
            reasons.append("missing_claim")
            trust_grade = "UNKNOWN"
            claim_mode = "UNKNOWN"
        else:
            trust_grade = str(claim.get("trust_grade", ""))
            claim_mode = str(claim.get("mode", ""))
            if trust_grade not in ALLOWED_TRUST:
                reasons.append("trust_not_ABC")
            if claim_mode not in {"realistic", "both"}:
                reasons.append("claim_mode_not_realistic")

        bounds = entry.get("bounds")
        if not (isinstance(bounds, list) and len(bounds) == 2 and _is_number(bounds[0]) and _is_number(bounds[1])):
            reasons.append("invalid_bounds")
            low = high = None
        else:
            low = float(bounds[0])
            high = float(bounds[1])
            if not math.isfinite(low) or not math.isfinite(high):
                reasons.append("non_finite_bounds")
            elif low >= high:
                reasons.append("non_expandable_bounds")

        baseline_value: float | None = None
        try:
            baseline_value = _get_path(baseline, parameter_id)
        except Exception:  # noqa: BLE001
            reasons.append("baseline_path_not_numeric")

        if reasons:
            excluded.append(
                {
                    "parameter_id": parameter_id,
                    "exclusion_reason": sorted(set(reasons)),
                    "trust_grade": trust_grade,
                    "domain": str(entry.get("domain", "")),
                }
            )
            continue

        considered.append(
            {
                "parameter_id": parameter_id,
                "bounds": [_round(low), _round(high)],
                "baseline_value": _round(float(baseline_value)),
                "trust_grade": trust_grade,
                "domain": mode,
                "affects_core_probability": True,
            }
        )

    if not considered:
        raise ValueError("realistic optimization search space is empty after contract filters")

    return {
        "schema_version": "optimization_search_space.v1",
        "objective_contract_ref": str(DEFAULT_OBJECTIVE_CONTRACT),
        "mode": mode,
        "seed": int(seed),
        "trust_filter": "A|B|C",
        "excluded_internal_parameter_count": excluded_internal_parameter_count,
        "internal_parameter_prefixes_excluded": list(INTERNAL_PARAMETER_PREFIXES),
        "parameters_considered": considered,
        "excluded_parameters": excluded,
    }


def _coprime_step(modulus: int, seed: int) -> int:
    if modulus <= 1:
        return 1
    step = (seed % modulus) or 1
    while math.gcd(step, modulus) != 1:
        step += 1
        if step >= modulus:
            step = 1
    return step


def _candidate_parameters(
    *,
    considered: Sequence[Mapping[str, Any]],
    max_points: int,
    seed: int,
) -> List[Dict[str, float]]:
    count = max(1, int(max_points))
    if not considered:
        return [{}]

    grid: List[Dict[str, float]] = []
    for point_index in range(count):
        values: Dict[str, float] = {}
        for param_index, item in enumerate(considered):
            parameter_id = str(item["parameter_id"])
            low = float(item["bounds"][0])
            high = float(item["bounds"][1])

            step = _coprime_step(count, seed + (param_index + 1) * 13)
            offset = (seed * (param_index + 1) + param_index * 17) % count
            bin_index = (offset + point_index * step) % count
            fraction = (bin_index + 0.5) / count
            value = low + fraction * (high - low)
            values[parameter_id] = _round(value)
        grid.append(dict(sorted(values.items())))

    baseline_point = {str(item["parameter_id"]): _round(float(item["baseline_value"])) for item in considered}
    grid[0] = dict(sorted(baseline_point.items()))
    return grid


def _score_point(
    *,
    contract: Mapping[str, Any],
    mission_output: Mapping[str, Any],
    risk_score: Mapping[str, Any],
    mode: str,
) -> Dict[str, Any]:
    metrics = _available_metrics(contract, mode)

    p_success = _round(float(mission_output.get("p_success", 0.0)))
    risk_value = _round(float(risk_score["risk_envelope"]))
    values: Dict[str, float] = {
        "p_success": p_success,
        "risk_envelope": risk_value,
    }

    vector: List[float] = []
    for metric in metrics:
        if metric in values:
            vector.append(values[metric])

    return {
        "p_success": p_success,
        "risk_envelope": risk_value,
        "risk_meta": {
            "method": str(risk_score.get("method", "lower_quantile")),
            "quantile": _round(float(risk_score.get("quantile", 0.05))),
            "distribution_size": int(risk_score.get("distribution_size", 0)),
            "q_value": _round(float(risk_score.get("q_value", 0.0))),
        },
        "objective_vector": vector,
        "rank_key": "pareto",
    }


def _dominance(
    *,
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    metrics: Sequence[str],
    maximize_by_metric: Mapping[str, bool],
) -> bool:
    better_or_equal_all = True
    strictly_better_any = False

    for metric in metrics:
        left_score = float(left["scores"][metric]) if metric in left["scores"] else None
        right_score = float(right["scores"][metric]) if metric in right["scores"] else None
        if left_score is None or right_score is None:
            continue

        maximize = bool(maximize_by_metric.get(metric, True))
        if maximize:
            if left_score < right_score - 1e-12:
                better_or_equal_all = False
                break
            if left_score > right_score + 1e-12:
                strictly_better_any = True
        else:
            if left_score > right_score + 1e-12:
                better_or_equal_all = False
                break
            if left_score < right_score - 1e-12:
                strictly_better_any = True

    return better_or_equal_all and strictly_better_any


def _pareto_indices(points: Sequence[Mapping[str, Any]], metrics: Sequence[str], maximize_by_metric: Mapping[str, bool]) -> List[int]:
    indices: List[int] = []
    for i, left in enumerate(points):
        dominated = False
        for j, right in enumerate(points):
            if i == j:
                continue
            if _dominance(left=right, right=left, metrics=metrics, maximize_by_metric=maximize_by_metric):
                dominated = True
                break
        if not dominated:
            indices.append(i)
    return indices


def build_payloads(
    *,
    repo_root: Path,
    objective_contract_path: Path,
    risk_spec_path: Path,
    baseline_scenario_path: Path,
    parameter_registry_path: Path,
    parameter_claims_path: Path,
    evidence_sources_path: Path,
    failure_surface_path: Path,
    determinism_status_path: Path,
    mode: str,
    seed: int,
    max_points: int,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if mode != "realistic":
        raise ValueError("F1 supports only realistic mode")

    contract = load_json(repo_root / objective_contract_path)
    if contract.get("schema_version") != "objective_contract.v1":
        raise ValueError("objective contract schema_version must be objective_contract.v1")
    contract_modes = contract.get("modes")
    if not isinstance(contract_modes, list) or "realistic" not in contract_modes:
        raise ValueError("objective contract must declare realistic mode")
    primary_metric = (
        contract.get("objective_sets", {})
        .get("realistic", {})
        .get("primary", {})
        .get("metric")
    )
    if primary_metric != "p_success":
        raise ValueError("objective contract realistic primary metric must be p_success")
    realistic_aggregation = (
        contract.get("objective_sets", {})
        .get("realistic", {})
        .get("aggregation", {})
    )
    if realistic_aggregation.get("type") != "pareto":
        raise ValueError("objective contract realistic aggregation.type must be pareto")
    if realistic_aggregation.get("dimensions") != ["p_success", "risk_envelope"]:
        raise ValueError("objective contract realistic aggregation.dimensions must be ['p_success','risk_envelope']")

    baseline = load_json(repo_root / baseline_scenario_path)
    risk_spec = load_json(repo_root / risk_spec_path)
    parameter_registry = load_json(repo_root / parameter_registry_path)
    parameter_claims = load_json(repo_root / parameter_claims_path)
    failure_surface = load_json(repo_root / failure_surface_path)
    determinism_status = load_json(repo_root / determinism_status_path)

    evidence_result = parameter_evidence_validate.validate(
        parameter_registry=parameter_registry,
        evidence_sources_payload=load_json(repo_root / evidence_sources_path),
        parameter_claims_payload=parameter_claims,
    )
    if evidence_result.get("status") != "PASS":
        raise ValueError("parameter evidence validation must pass before building optimization frontier")

    search_space = _search_space(
        baseline=baseline,
        parameter_registry=parameter_registry,
        parameter_claims=parameter_claims,
        mode=mode,
        seed=seed,
    )
    search_space["objective_contract_ref"] = str(objective_contract_path)

    considered = list(search_space["parameters_considered"])
    candidates = _candidate_parameters(
        considered=considered,
        max_points=max_points,
        seed=seed,
    )

    claims_map = load_claims_map(repo_root)
    risk_quantile = risk_envelope.parse_quantile_from_spec(risk_spec)
    risk_samples = risk_envelope.parse_samples_from_spec(risk_spec, default=64)

    driver_method = str(failure_surface.get("dominant_drivers", {}).get("method", "OAT"))
    top3 = list(failure_surface.get("dominant_drivers", {}).get("top3", []))
    driver_ids = [str(item.get("parameter_id", "")) for item in top3 if isinstance(item, Mapping)]

    points: List[Dict[str, Any]] = []
    for index, params in enumerate(candidates):
        scenario = copy.deepcopy(baseline)
        for parameter_id, value in params.items():
            _set_path(scenario, parameter_id, value)

        output = build_output(
            scenario,
            mode=mode,
            claims_map=claims_map,
        )

        if output.get("speculative_parameters_used"):
            raise ValueError(f"realistic run used speculative parameters at point {index}")

        risk_score = risk_envelope.risk_envelope_from_scenario(
            scenario=scenario,
            claims_map=claims_map,
            mode=mode,
            seed=int(seed),
            samples=int(risk_samples),
            quantile=float(risk_quantile),
        )
        scores = _score_point(
            contract=contract,
            mission_output=output,
            risk_score=risk_score,
            mode=mode,
        )
        point = {
            "candidate_id": f"pt-{index:03d}",
            "parameters": dict(sorted(params.items())),
            "scores": scores,
            "dominant_drivers": {
                "method": driver_method,
                "parameter_ids": sorted(driver_ids),
            },
            "constraint_status": {
                "no_D_grade_influence": "PASS",
                "evidence_completeness_1.0": "PASS",
                "bounds": "PASS",
            },
        }
        points.append(point)

    metrics = _available_metrics(contract, mode)
    maximize_by_metric = _metric_directions(contract, mode)

    points.sort(
        key=lambda item: (
            -float(item["scores"]["p_success"]),
            float(item["scores"]["risk_envelope"]),
            item["candidate_id"],
        )
    )

    pareto = _pareto_indices(points=points, metrics=metrics, maximize_by_metric=maximize_by_metric)

    frontier = {
        "schema_version": "optimization_frontier.v1",
        "objective_contract_ref": str(objective_contract_path),
        "engine_commit": str(determinism_status.get("last_verified_commit_sha", "unknown")),
        "mode": mode,
        "seed": int(seed),
        "method": "deterministic_latin_hypercube",
        "dimensions": list(metrics),
        "risk_envelope_spec_ref": str(risk_spec_path),
        "evaluation_count": len(points),
        "points": points,
        "pareto_frontier_indices": pareto,
    }

    signature_basis = {
        "mode": frontier["mode"],
        "seed": frontier["seed"],
        "method": frontier["method"],
        "dimensions": frontier["dimensions"],
        "evaluation_count": frontier["evaluation_count"],
        "points": frontier["points"],
        "pareto_frontier_indices": frontier["pareto_frontier_indices"],
    }
    frontier["determinism_signature"] = contracts.sha256_hex(contracts.canonical_json(signature_basis))

    return search_space, frontier


def build_and_write(
    *,
    repo_root: Path,
    objective_contract_path: Path,
    risk_spec_path: Path,
    baseline_scenario_path: Path,
    parameter_registry_path: Path,
    parameter_claims_path: Path,
    evidence_sources_path: Path,
    failure_surface_path: Path,
    determinism_status_path: Path,
    search_space_output: Path,
    frontier_output: Path,
    mode: str,
    seed: int,
    max_points: int,
) -> Dict[str, Any]:
    search_space, frontier = build_payloads(
        repo_root=repo_root,
        objective_contract_path=objective_contract_path,
        risk_spec_path=risk_spec_path,
        baseline_scenario_path=baseline_scenario_path,
        parameter_registry_path=parameter_registry_path,
        parameter_claims_path=parameter_claims_path,
        evidence_sources_path=evidence_sources_path,
        failure_surface_path=failure_surface_path,
        determinism_status_path=determinism_status_path,
        mode=mode,
        seed=seed,
        max_points=max_points,
    )

    write_json(repo_root / search_space_output, search_space)
    write_json(repo_root / frontier_output, frontier)

    return {
        "status": "PASS",
        "search_space_output": str(search_space_output),
        "frontier_output": str(frontier_output),
        "mode": mode,
        "seed": seed,
        "method": frontier["method"],
        "dimensions": list(frontier["dimensions"]),
        "evaluation_count": frontier["evaluation_count"],
        "considered_parameters": len(search_space["parameters_considered"]),
        "excluded_parameters": len(search_space["excluded_parameters"]),
        "excluded_internal_parameters": search_space["excluded_internal_parameter_count"],
        "pareto_size": len(frontier["pareto_frontier_indices"]),
        "frontier_sha256": contracts.sha256_hex(contracts.canonical_json(frontier)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--objective-contract", default=str(DEFAULT_OBJECTIVE_CONTRACT))
    parser.add_argument("--risk-spec", default=str(DEFAULT_RISK_SPEC))
    parser.add_argument("--baseline-scenario", default=str(DEFAULT_BASELINE_SCENARIO))
    parser.add_argument("--parameter-registry", default=str(DEFAULT_PARAMETER_REGISTRY))
    parser.add_argument("--parameter-claims", default=str(DEFAULT_PARAMETER_CLAIMS))
    parser.add_argument("--evidence-sources", default=str(DEFAULT_EVIDENCE_SOURCES))
    parser.add_argument("--failure-surface", default=str(DEFAULT_FAILURE_SURFACE))
    parser.add_argument("--determinism-status", default=str(DEFAULT_DETERMINISM_STATUS))
    parser.add_argument("--search-space-output", default=str(DEFAULT_SEARCH_SPACE_OUTPUT))
    parser.add_argument("--frontier-output", default=str(DEFAULT_FRONTIER_OUTPUT))
    parser.add_argument("--mode", choices=("realistic",), default="realistic")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-points", type=int, default=20)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_and_write(
            repo_root=Path(args.repo_root).resolve(),
            objective_contract_path=Path(args.objective_contract),
            risk_spec_path=Path(args.risk_spec),
            baseline_scenario_path=Path(args.baseline_scenario),
            parameter_registry_path=Path(args.parameter_registry),
            parameter_claims_path=Path(args.parameter_claims),
            evidence_sources_path=Path(args.evidence_sources),
            failure_surface_path=Path(args.failure_surface),
            determinism_status_path=Path(args.determinism_status),
            search_space_output=Path(args.search_space_output),
            frontier_output=Path(args.frontier_output),
            mode=str(args.mode),
            seed=int(args.seed),
            max_points=int(args.max_points),
        )
        if args.format == "json":
            print(render_json(result))
        else:
            print("PASS: optimization frontier artifacts")
            print(f"- search_space_output: {result['search_space_output']}")
            print(f"- frontier_output: {result['frontier_output']}")
            print(f"- mode: {result['mode']}")
            print(f"- seed: {result['seed']}")
            print(f"- method: {result['method']}")
            print(f"- dimensions: {','.join(result['dimensions'])}")
            print(f"- evaluation_count: {result['evaluation_count']}")
            print(f"- considered_parameters: {result['considered_parameters']}")
            print(f"- excluded_parameters: {result['excluded_parameters']}")
            print(f"- excluded_internal_parameters: {result['excluded_internal_parameters']}")
            print(f"- pareto_size: {result['pareto_size']}")
            print(f"- frontier_sha256: {result['frontier_sha256']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
