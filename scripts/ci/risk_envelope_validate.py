#!/usr/bin/env python3
"""Validate risk-envelope contract and 2D optimization frontier integrity."""

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
from typing import Any, Dict, List, Mapping

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from mission.dag import contracts
from scripts import build_optimization_frontier
from scripts.ci import optimization_frontier_validate

EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_OBJECTIVE_CONTRACT = Path("mission/objectives/objective_contract.v1.json")
DEFAULT_RISK_SPEC = Path("mission/objectives/risk_envelope.v1.json")
DEFAULT_UNCERTAINTY_MODEL = Path("mission/UNCERTAINTY_MODEL_v1.json")
DEFAULT_PARAMETER_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_PARAMETER_CLAIMS = Path("parameters/registry/parameter_claims.v1.json")
DEFAULT_BASELINE_SCENARIO = Path("mission/BASELINE_SCENARIO_v1.json")
DEFAULT_EVIDENCE_SOURCES = Path("parameters/registry/evidence_sources.v1.json")
DEFAULT_FAILURE_SURFACE = Path("artifacts/failure_surface_baseline.v1.json")
DEFAULT_DETERMINISM_STATUS = Path("artifacts/determinism_status.json")
DEFAULT_SEARCH_SPACE = Path("artifacts/optimization_search_space.v1.json")
DEFAULT_FRONTIER = Path("artifacts/optimization_frontier_realistic.v1.json")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def validate(
    *,
    repo_root: Path,
    objective_contract_path: Path,
    risk_spec_path: Path,
    uncertainty_model_path: Path,
    parameter_registry_path: Path,
    parameter_claims_path: Path,
    baseline_scenario_path: Path,
    evidence_sources_path: Path,
    failure_surface_path: Path,
    determinism_status_path: Path,
    search_space_path: Path,
    frontier_path: Path,
) -> Dict[str, Any]:
    errors: List[str] = []

    contract = load_json(repo_root / objective_contract_path)
    risk_spec = load_json(repo_root / risk_spec_path)
    uncertainty_model = load_json(repo_root / uncertainty_model_path)
    parameter_registry = load_json(repo_root / parameter_registry_path)
    parameter_claims = load_json(repo_root / parameter_claims_path)
    search_space = load_json(repo_root / search_space_path)
    frontier = load_json(repo_root / frontier_path)

    if risk_spec.get("schema_version") != "risk_envelope.v1":
        errors.append("risk spec schema_version must be risk_envelope.v1")
    if risk_spec.get("method") != "lower_quantile":
        errors.append("risk spec method must be lower_quantile")
    quantile = risk_spec.get("quantile")
    if not _is_number(quantile) or not (0.0 < float(quantile) < 1.0):
        errors.append("risk spec quantile must be numeric in (0,1)")
    if risk_spec.get("mode") != "realistic_only":
        errors.append("risk spec mode must be realistic_only")
    if risk_spec.get("source") != "uncertainty_model":
        errors.append("risk spec source must be uncertainty_model")
    if risk_spec.get("uncertainty_model_ref") != str(uncertainty_model_path):
        errors.append(
            f"risk spec uncertainty_model_ref must equal '{uncertainty_model_path}'"
        )

    if uncertainty_model.get("schema_version") != "uncertainty_model.v1":
        errors.append("mission/UNCERTAINTY_MODEL_v1.json schema_version must be uncertainty_model.v1")

    if frontier.get("mode") != "realistic":
        errors.append("frontier mode must be realistic")
    seed = frontier.get("seed")
    spec_seed = risk_spec.get("deterministic_seed")
    if not isinstance(seed, int):
        errors.append("frontier.seed must be int")
    if not isinstance(spec_seed, int):
        errors.append("risk spec deterministic_seed must be int")
    elif isinstance(seed, int) and seed != spec_seed:
        errors.append("frontier.seed must match risk spec deterministic_seed")

    dimensions = frontier.get("dimensions")
    if dimensions != ["p_success", "risk_envelope"]:
        errors.append("frontier.dimensions must equal ['p_success','risk_envelope']")

    for index, point in enumerate(frontier.get("points", [])):
        if not isinstance(point, Mapping):
            errors.append(f"frontier.points[{index}] must be object")
            continue
        scores = point.get("scores")
        if not isinstance(scores, Mapping):
            errors.append(f"frontier.points[{index}].scores must be object")
            continue
        risk_value = scores.get("risk_envelope")
        if not _is_number(risk_value):
            errors.append(f"frontier.points[{index}].scores.risk_envelope must be numeric")
        elif not (0.0 <= float(risk_value) <= 1.0):
            errors.append(f"frontier.points[{index}].scores.risk_envelope must be in [0,1]")

        meta = scores.get("risk_meta")
        if not isinstance(meta, Mapping):
            errors.append(f"frontier.points[{index}].scores.risk_meta must be object")
            continue
        if meta.get("method") != risk_spec.get("method"):
            errors.append(f"frontier.points[{index}] risk_meta.method must match risk spec method")
        if not _is_number(meta.get("quantile")):
            errors.append(f"frontier.points[{index}] risk_meta.quantile must be numeric")
        elif _is_number(quantile) and abs(float(meta.get("quantile")) - float(quantile)) > 1e-12:
            errors.append(f"frontier.points[{index}] risk_meta.quantile must match risk spec quantile")
        samples = risk_spec.get("monte_carlo_samples")
        if isinstance(samples, int):
            if meta.get("distribution_size") != samples:
                errors.append(
                    f"frontier.points[{index}] risk_meta.distribution_size must equal {samples}"
                )

    frontier_core_result = optimization_frontier_validate.validate(
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
    errors.extend(list(frontier_core_result.get("errors", [])))

    try:
        expected_search, expected_frontier = build_optimization_frontier.build_payloads(
            repo_root=repo_root,
            objective_contract_path=objective_contract_path,
            risk_spec_path=risk_spec_path,
            baseline_scenario_path=baseline_scenario_path,
            parameter_registry_path=parameter_registry_path,
            parameter_claims_path=parameter_claims_path,
            evidence_sources_path=evidence_sources_path,
            failure_surface_path=failure_surface_path,
            determinism_status_path=determinism_status_path,
            mode="realistic",
            seed=int(frontier.get("seed", 1)),
            max_points=int(frontier.get("evaluation_count", 20)),
        )
        if contracts.canonical_json(expected_search) != contracts.canonical_json(search_space):
            errors.append("search_space determinism mismatch: regenerated payload differs")
        if contracts.canonical_json(expected_frontier) != contracts.canonical_json(frontier):
            errors.append("frontier determinism mismatch: regenerated payload differs")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"determinism precondition failed: {exc}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "evaluation_count": int(frontier.get("evaluation_count", 0)),
        "pareto_size": len(frontier.get("pareto_frontier_indices", []))
        if isinstance(frontier.get("pareto_frontier_indices"), list)
        else 0,
    }


def _render_text(result: Mapping[str, Any]) -> str:
    lines = [
        f"{result['status']}: risk envelope validation",
        f"- error_count: {result['error_count']}",
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
    parser.add_argument("--uncertainty-model", default=str(DEFAULT_UNCERTAINTY_MODEL))
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
        result = validate(
            repo_root=repo_root,
            objective_contract_path=Path(args.objective_contract),
            risk_spec_path=Path(args.risk_spec),
            uncertainty_model_path=Path(args.uncertainty_model),
            parameter_registry_path=Path(args.parameter_registry),
            parameter_claims_path=Path(args.parameter_claims),
            baseline_scenario_path=Path(args.baseline_scenario),
            evidence_sources_path=Path(args.evidence_sources),
            failure_surface_path=Path(args.failure_surface),
            determinism_status_path=Path(args.determinism_status),
            search_space_path=Path(args.search_space),
            frontier_path=Path(args.frontier),
        )
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
