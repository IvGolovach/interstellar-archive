#!/usr/bin/env python3
"""Validate deterministic optimization frontier contract (F1)."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text
from typing import Any, Dict, List, Mapping, Sequence

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from mission.dag import contracts
from scripts import build_optimization_frontier

EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_OBJECTIVE_CONTRACT = Path("mission/objectives/objective_contract.v1.json")
DEFAULT_RISK_SPEC = Path("mission/objectives/risk_envelope.v1.json")
DEFAULT_PARAMETER_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_PARAMETER_CLAIMS = Path("parameters/registry/parameter_claims.v1.json")
DEFAULT_BASELINE_SCENARIO = Path("mission/BASELINE_SCENARIO_v1.json")
DEFAULT_EVIDENCE_SOURCES = Path("parameters/registry/evidence_sources.v1.json")
DEFAULT_FAILURE_SURFACE = Path("artifacts/failure_surface_baseline.v1.json")
DEFAULT_DETERMINISM_STATUS = Path("artifacts/determinism_status.json")
DEFAULT_SEARCH_SPACE = Path("artifacts/optimization_search_space.v1.json")
DEFAULT_FRONTIER = Path("artifacts/optimization_frontier_realistic.v1.json")
INTERNAL_PARAMETER_PREFIX = "code_literal."
PUBLIC_VISIBILITY = "public"
PUBLIC_SURFACE_OPTIMIZATION = "optimization"


def _public_surfaces(parameter: Mapping[str, Any]) -> set[str]:
    surfaces = parameter.get("public_surfaces")
    if not isinstance(surfaces, list):
        return set()
    return {str(surface) for surface in surfaces if isinstance(surface, str)}


def _has_visibility_metadata(parameter: Mapping[str, Any]) -> bool:
    return "visibility" in parameter or "public_surfaces" in parameter or "audit_scope" in parameter


def _is_public_optimization_parameter(parameter: Mapping[str, Any]) -> bool:
    parameter_id = parameter.get("parameter_id")
    if isinstance(parameter_id, str) and parameter_id.startswith(INTERNAL_PARAMETER_PREFIX):
        return False
    if not _has_visibility_metadata(parameter):
        return True
    return (
        parameter.get("visibility") == PUBLIC_VISIBILITY
        and PUBLIC_SURFACE_OPTIMIZATION in _public_surfaces(parameter)
    )


def _is_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


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
    if isinstance(definition, Mapping) and definition.get("status") == "N/A_v1":
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


def _dominates(
    *,
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    metrics: Sequence[str],
    maximize_by_metric: Mapping[str, bool],
) -> bool:
    better_or_equal_all = True
    strictly_better_any = False
    for metric in metrics:
        left_scores = left.get("scores")
        right_scores = right.get("scores")
        if not isinstance(left_scores, Mapping) or not isinstance(right_scores, Mapping):
            return False
        if metric not in left_scores or metric not in right_scores:
            return False
        try:
            lv = float(left_scores[metric])
            rv = float(right_scores[metric])
        except Exception:  # noqa: BLE001
            return False
        maximize = bool(maximize_by_metric.get(metric, True))
        if maximize:
            if lv < rv - 1e-12:
                better_or_equal_all = False
                break
            if lv > rv + 1e-12:
                strictly_better_any = True
        else:
            if lv > rv + 1e-12:
                better_or_equal_all = False
                break
            if lv < rv - 1e-12:
                strictly_better_any = True
    return better_or_equal_all and strictly_better_any


def _expected_pareto(points: Sequence[Mapping[str, Any]], metrics: Sequence[str], maximize_by_metric: Mapping[str, bool]) -> List[int]:
    out: List[int] = []
    for i, point in enumerate(points):
        dominated = False
        for j, other in enumerate(points):
            if i == j:
                continue
            if _dominates(left=other, right=point, metrics=metrics, maximize_by_metric=maximize_by_metric):
                dominated = True
                break
        if not dominated:
            out.append(i)
    return out


def validate(
    *,
    contract: Mapping[str, Any],
    parameter_registry: Mapping[str, Any],
    parameter_claims: Mapping[str, Any],
    risk_spec: Mapping[str, Any],
    search_space: Mapping[str, Any],
    frontier: Mapping[str, Any],
    objective_contract_path: Path,
    risk_spec_path: Path,
    search_space_path: Path,
) -> Dict[str, Any]:
    errors: List[str] = []

    if search_space.get("schema_version") != "optimization_search_space.v1":
        errors.append("search_space.schema_version must be optimization_search_space.v1")

    if frontier.get("schema_version") != "optimization_frontier.v1":
        errors.append("frontier.schema_version must be optimization_frontier.v1")

    if search_space.get("objective_contract_ref") != str(objective_contract_path):
        errors.append(
            f"search_space.objective_contract_ref must equal '{objective_contract_path}'"
        )

    if frontier.get("objective_contract_ref") != str(objective_contract_path):
        errors.append(
            f"frontier.objective_contract_ref must equal '{objective_contract_path}'"
        )
    if frontier.get("risk_envelope_spec_ref") != str(risk_spec_path):
        errors.append(
            f"frontier.risk_envelope_spec_ref must equal '{risk_spec_path}'"
        )

    if search_space.get("mode") != "realistic":
        errors.append("search_space.mode must be realistic")
    excluded_internal_parameter_count = search_space.get("excluded_internal_parameter_count")
    if not isinstance(excluded_internal_parameter_count, int) or excluded_internal_parameter_count < 0:
        errors.append("search_space.excluded_internal_parameter_count must be int >= 0")
    internal_prefixes = search_space.get("internal_parameter_prefixes_excluded")
    if not isinstance(internal_prefixes, list) or INTERNAL_PARAMETER_PREFIX not in internal_prefixes:
        errors.append("search_space.internal_parameter_prefixes_excluded must include code_literal.")

    if frontier.get("mode") != "realistic":
        errors.append("frontier.mode must be realistic")

    if risk_spec.get("schema_version") != "risk_envelope.v1":
        errors.append("risk spec schema_version must be risk_envelope.v1")
    if risk_spec.get("method") != "lower_quantile":
        errors.append("risk spec method must be lower_quantile")
    quantile = risk_spec.get("quantile")
    if not _is_number(quantile):
        errors.append("risk spec quantile must be numeric")
        quantile = 0.05
    elif float(quantile) <= 0.0 or float(quantile) >= 1.0:
        errors.append("risk spec quantile must be in (0,1)")

    metrics = _available_metrics(contract, "realistic")
    maximize_by_metric = _metric_directions(contract, "realistic")
    dimensions = frontier.get("dimensions")
    if dimensions != metrics:
        errors.append(f"frontier.dimensions must match active objective metrics: {metrics}")

    considered = search_space.get("parameters_considered")
    if not isinstance(considered, list):
        errors.append("search_space.parameters_considered must be list")
        considered = []

    claim_by_id = {
        str(item["parameter_id"]): item
        for item in parameter_claims.get("claims", [])
        if isinstance(item, Mapping) and isinstance(item.get("parameter_id"), str)
    }
    registry_by_id = {
        str(item["parameter_id"]): item
        for item in parameter_registry.get("parameters", [])
        if isinstance(item, Mapping) and isinstance(item.get("parameter_id"), str)
    }

    considered_bounds: Dict[str, Sequence[float]] = {}
    for index, item in enumerate(considered):
        prefix = f"search_space.parameters_considered[{index}]"
        if not isinstance(item, Mapping):
            errors.append(f"{prefix} must be object")
            continue

        parameter_id = item.get("parameter_id")
        if not isinstance(parameter_id, str) or not parameter_id:
            errors.append(f"{prefix}.parameter_id must be non-empty string")
            continue
        if parameter_id.startswith(INTERNAL_PARAMETER_PREFIX):
            errors.append(f"{prefix}.parameter_id must not publish internal code literal {parameter_id!r}")
            continue

        claim = claim_by_id.get(parameter_id)
        if not isinstance(claim, Mapping):
            errors.append(f"{prefix}: missing parameter claim for {parameter_id}")
        else:
            trust = claim.get("trust_grade")
            if trust not in {"A", "B", "C"}:
                errors.append(f"{prefix}: realistic search cannot include trust {trust!r}")

        registry = registry_by_id.get(parameter_id)
        if not isinstance(registry, Mapping):
            errors.append(f"{prefix}: missing parameter registry entry for {parameter_id}")
        else:
            if not _is_public_optimization_parameter(registry):
                errors.append(
                    f"{prefix}: registry visibility metadata must allow public optimization surface"
                )
            if registry.get("domain") != "realistic":
                errors.append(f"{prefix}: registry domain must be realistic")
            if not bool(registry.get("affects_core_probability", False)):
                errors.append(f"{prefix}: affects_core_probability must be true")

        bounds = item.get("bounds")
        if not (isinstance(bounds, list) and len(bounds) == 2 and _is_number(bounds[0]) and _is_number(bounds[1])):
            errors.append(f"{prefix}.bounds must be numeric [min,max]")
            continue
        if float(bounds[0]) >= float(bounds[1]):
            errors.append(f"{prefix}.bounds must have min < max")
            continue
        considered_bounds[parameter_id] = [float(bounds[0]), float(bounds[1])]

    excluded = search_space.get("excluded_parameters")
    if not isinstance(excluded, list):
        errors.append("search_space.excluded_parameters must be list")
        excluded = []
    for index, item in enumerate(excluded):
        prefix = f"search_space.excluded_parameters[{index}]"
        if not isinstance(item, Mapping):
            errors.append(f"{prefix} must be object")
            continue
        parameter_id = item.get("parameter_id")
        if not isinstance(parameter_id, str) or not parameter_id:
            errors.append(f"{prefix}.parameter_id must be non-empty string")
            continue
        if parameter_id.startswith(INTERNAL_PARAMETER_PREFIX):
            errors.append(f"{prefix}.parameter_id must not publish internal code literal {parameter_id!r}")
            continue
        registry = registry_by_id.get(parameter_id)
        if isinstance(registry, Mapping) and not _is_public_optimization_parameter(registry):
            errors.append(
                f"{prefix}: registry visibility metadata must allow public optimization surface"
            )

    points = frontier.get("points")
    if not isinstance(points, list) or not points:
        errors.append("frontier.points must be a non-empty list")
        points = []

    for index, point in enumerate(points):
        prefix = f"frontier.points[{index}]"
        if not isinstance(point, Mapping):
            errors.append(f"{prefix} must be object")
            continue

        parameters = point.get("parameters")
        if not isinstance(parameters, Mapping):
            errors.append(f"{prefix}.parameters must be object")
            continue

        for parameter_id, value in parameters.items():
            if parameter_id not in considered_bounds:
                errors.append(f"{prefix}: parameter {parameter_id!r} not present in search space")
                continue
            if not _is_number(value):
                errors.append(f"{prefix}: parameter {parameter_id!r} value must be numeric")
                continue
            low, high = considered_bounds[parameter_id]
            numeric = float(value)
            if numeric < low - 1e-12 or numeric > high + 1e-12:
                errors.append(
                    f"{prefix}: parameter {parameter_id!r}={numeric} outside bounds [{low}, {high}]"
                )

        scores = point.get("scores")
        if not isinstance(scores, Mapping):
            errors.append(f"{prefix}.scores must be object")
            continue

        p_success = scores.get("p_success")
        if not _is_number(p_success):
            errors.append(f"{prefix}.scores.p_success must be numeric")
        else:
            p_success_num = float(p_success)
            if p_success_num < -1e-12 or p_success_num > 1.0 + 1e-12:
                errors.append(f"{prefix}.scores.p_success must be in [0,1]")

        risk_value = scores.get("risk_envelope")
        if not _is_number(risk_value):
            errors.append(f"{prefix}.scores.risk_envelope must be numeric")
        else:
            risk_num = float(risk_value)
            if risk_num < -1e-12 or risk_num > 1.0 + 1e-12:
                errors.append(f"{prefix}.scores.risk_envelope must be in [0,1]")

        risk_meta = scores.get("risk_meta")
        if not isinstance(risk_meta, Mapping):
            errors.append(f"{prefix}.scores.risk_meta must be object")
        else:
            if risk_meta.get("method") != "lower_quantile":
                errors.append(f"{prefix}.scores.risk_meta.method must be lower_quantile")
            if not _is_number(risk_meta.get("quantile")):
                errors.append(f"{prefix}.scores.risk_meta.quantile must be numeric")
            elif abs(float(risk_meta.get("quantile")) - float(quantile)) > 1e-12:
                errors.append(f"{prefix}.scores.risk_meta.quantile must match risk spec quantile")
            if not isinstance(risk_meta.get("distribution_size"), int) or int(risk_meta.get("distribution_size")) <= 1:
                errors.append(f"{prefix}.scores.risk_meta.distribution_size must be int > 1")
            if not _is_number(risk_meta.get("q_value")):
                errors.append(f"{prefix}.scores.risk_meta.q_value must be numeric")
            else:
                q_value = float(risk_meta.get("q_value"))
                if q_value < -1e-12 or q_value > 1.0 + 1e-12:
                    errors.append(f"{prefix}.scores.risk_meta.q_value must be in [0,1]")
                if _is_number(risk_value) and abs(float(risk_value) - (1.0 - q_value)) > 1e-9:
                    errors.append(
                        f"{prefix}.scores.risk_envelope must equal 1 - q_value (got {risk_value} vs q={q_value})"
                    )

        vector = scores.get("objective_vector")
        if not isinstance(vector, list) or any(not _is_number(item) for item in vector):
            errors.append(f"{prefix}.scores.objective_vector must be numeric list")
        elif len(vector) != len(metrics):
            errors.append(
                f"{prefix}.scores.objective_vector length mismatch: expected {len(metrics)}, got {len(vector)}"
            )
        else:
            for metric_index, metric in enumerate(metrics):
                if metric not in scores or not _is_number(scores[metric]):
                    errors.append(f"{prefix}.scores missing metric {metric!r} required by objective contract")
                    continue
                expected_value = float(scores[metric])
                if abs(float(vector[metric_index]) - expected_value) > 1e-12:
                    errors.append(
                        f"{prefix}.scores.objective_vector[{metric_index}] must equal {metric} ({expected_value})"
                    )

        constraint_status = point.get("constraint_status")
        if not isinstance(constraint_status, Mapping):
            errors.append(f"{prefix}.constraint_status must be object")
        else:
            for cid in ("no_D_grade_influence", "evidence_completeness_1.0"):
                if constraint_status.get(cid) != "PASS":
                    errors.append(f"{prefix}.constraint_status.{cid} must be PASS")

    pareto = frontier.get("pareto_frontier_indices")
    if not isinstance(pareto, list) or any(not isinstance(item, int) for item in pareto):
        errors.append("frontier.pareto_frontier_indices must be integer list")
        pareto = []

    expected_pareto = _expected_pareto(points=points, metrics=metrics, maximize_by_metric=maximize_by_metric)
    if pareto != expected_pareto:
        errors.append(
            "frontier.pareto_frontier_indices mismatch: "
            f"expected {expected_pareto}, got {pareto}"
        )

    sorted_points = sorted(
        points,
        key=lambda item: (
            -float(item.get("scores", {}).get("p_success", 0.0)),
            float(item.get("scores", {}).get("risk_envelope", 1.0)),
            str(item.get("candidate_id", "")),
        ),
    )
    if points != sorted_points:
        errors.append("frontier.points must be sorted by p_success desc, risk_envelope asc, candidate_id asc")

    evaluation_count = frontier.get("evaluation_count")
    if not isinstance(evaluation_count, int):
        errors.append("frontier.evaluation_count must be int")
    elif evaluation_count != len(points):
        errors.append(
            f"frontier.evaluation_count mismatch: expected {len(points)}, got {evaluation_count}"
        )

    return {
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "metrics": metrics,
        "evaluation_count": len(points),
        "pareto_size": len(expected_pareto),
    }


def _render_text(result: Mapping[str, Any]) -> str:
    lines = [
        f"{result['status']}: optimization frontier validation",
        f"- error_count: {result['error_count']}",
        f"- metrics: {','.join(result['metrics']) if result['metrics'] else '(none)'}",
        f"- evaluation_count: {result['evaluation_count']}",
        f"- pareto_size: {result['pareto_size']}",
    ]
    if result["errors"]:
        lines.append("- errors:")
        for item in result["errors"]:
            lines.append(f"  - {item}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--objective-contract", default=str(DEFAULT_OBJECTIVE_CONTRACT))
    parser.add_argument("--risk-spec", default=str(DEFAULT_RISK_SPEC))
    parser.add_argument("--parameter-registry", default=str(DEFAULT_PARAMETER_REGISTRY))
    parser.add_argument("--parameter-claims", default=str(DEFAULT_PARAMETER_CLAIMS))
    parser.add_argument("--baseline-scenario", default=str(DEFAULT_BASELINE_SCENARIO))
    parser.add_argument("--evidence-sources", default=str(DEFAULT_EVIDENCE_SOURCES))
    parser.add_argument("--failure-surface", default=str(DEFAULT_FAILURE_SURFACE))
    parser.add_argument("--determinism-status", default=str(DEFAULT_DETERMINISM_STATUS))
    parser.add_argument("--search-space", default=str(DEFAULT_SEARCH_SPACE))
    parser.add_argument("--frontier", default=str(DEFAULT_FRONTIER))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    try:
        objective_contract_path = Path(args.objective_contract)
        search_space_path = Path(args.search_space)
        frontier_path = Path(args.frontier)

        contract = load_json(repo_root / objective_contract_path)
        risk_spec_path = Path(args.risk_spec)
        risk_spec = load_json(repo_root / risk_spec_path)
        parameter_registry = load_json(repo_root / Path(args.parameter_registry))
        parameter_claims = load_json(repo_root / Path(args.parameter_claims))
        search_space = load_json(repo_root / search_space_path)
        frontier = load_json(repo_root / frontier_path)

        result = validate(
            contract=contract,
            parameter_registry=parameter_registry,
            parameter_claims=parameter_claims,
            risk_spec=risk_spec,
            search_space=search_space,
            frontier=frontier,
            objective_contract_path=objective_contract_path,
            risk_spec_path=risk_spec_path,
            search_space_path=search_space_path,
        )

        try:
            expected_search, expected_frontier = build_optimization_frontier.build_payloads(
                repo_root=repo_root,
                objective_contract_path=Path(args.objective_contract),
                risk_spec_path=Path(args.risk_spec),
                baseline_scenario_path=Path(args.baseline_scenario),
                parameter_registry_path=Path(args.parameter_registry),
                parameter_claims_path=Path(args.parameter_claims),
                evidence_sources_path=Path(args.evidence_sources),
                failure_surface_path=Path(args.failure_surface),
                determinism_status_path=Path(args.determinism_status),
                mode="realistic",
                seed=int(frontier.get("seed", 1)),
                max_points=int(frontier.get("evaluation_count", 20)),
            )
        except ValueError as exc:
            result["status"] = "FAIL"
            result["errors"].append(f"determinism precondition failed: {exc}")
            expected_search = search_space
            expected_frontier = frontier

        if contracts.canonical_json(expected_search) != contracts.canonical_json(search_space):
            result["status"] = "FAIL"
            result["errors"].append("search_space determinism mismatch: regenerated payload differs")
        if contracts.canonical_json(expected_frontier) != contracts.canonical_json(frontier):
            result["status"] = "FAIL"
            result["errors"].append("frontier determinism mismatch: regenerated payload differs")
        if int(frontier.get("evaluation_count", -1)) != int(expected_frontier.get("evaluation_count", -2)):
            result["status"] = "FAIL"
            result["errors"].append("evaluation_count not reproducible")

        result["error_count"] = len(result["errors"])

        rendered = render_output(result, output_format=args.format, text_renderer=_render_text)
        print(rendered)
        if args.output:
            write_text(Path(args.output), rendered)

        if result["status"] == "PASS":
            return EXIT_PASS
        return EXIT_VIOLATION if args.strict else EXIT_PASS
    except Exception as exc:  # noqa: BLE001
        message = f"INTERNAL ERROR: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
