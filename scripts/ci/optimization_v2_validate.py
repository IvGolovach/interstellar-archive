#!/usr/bin/env python3
"""Validate Optimization v2 four-axis decision-surface artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from mission.optimization import v2
from scripts import build_optimization_v2_artifact


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_ARTIFACT = Path("artifacts/optimization_v2_frontier.v1.json")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _source_hash_by_path(payload: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in payload.get("source_artifacts", []):
        if isinstance(item, Mapping) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str):
            out[str(item["path"])] = str(item["sha256"])
    return out


def _validate_sources(*, repo_root: Path, payload: Mapping[str, Any], errors: List[str]) -> None:
    expected = {
        "mission/objectives/objective_contract.v1.json",
        "mission/objectives/risk_envelope.v1.json",
        "parameters/registry/parameter_claims.v1.json",
        "artifacts/optimization_search_space.v1.json",
        "artifacts/optimization_frontier_realistic.v1.json",
        "artifacts/mission_feasibility_screen.v1.json",
        "artifacts/capsule_risk_budget.v1.json",
        "artifacts/evidence_upgrade_campaign.v1.json",
    }
    by_path = _source_hash_by_path(payload)
    missing = sorted(expected - set(by_path))
    if missing:
        errors.append("source_artifacts missing required paths: " + ", ".join(missing))
    for path in sorted(expected & set(by_path)):
        full = repo_root / path
        if not full.exists():
            errors.append(f"source artifact path does not exist: {path}")
            continue
        actual = v2._sha256_file(full)
        if by_path[path] != actual:
            errors.append(f"source artifact sha256 mismatch for {path}")


def _expected_pareto_ids(candidates: Sequence[Mapping[str, Any]]) -> List[str]:
    return v2.pareto_candidate_ids(candidates)


def validate(*, payload: Mapping[str, Any], repo_root: Path | None = None) -> Dict[str, Any]:
    errors: List[str] = []

    if payload.get("schema_version") != v2.SCHEMA_VERSION:
        errors.append(f"schema_version must be {v2.SCHEMA_VERSION}")
    if payload.get("generator") != v2.GENERATOR:
        errors.append(f"generator must be {v2.GENERATOR}")
    if payload.get("mode") != v2.MODE:
        errors.append("mode must be realistic")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")

    axis_contract = payload.get("axis_contract")
    if not isinstance(axis_contract, Mapping):
        errors.append("axis_contract must be object")
        axis_contract = {}
    if axis_contract.get("aggregation_policy") != "pareto_first_no_hidden_weighted_sum":
        errors.append("axis_contract.aggregation_policy must be pareto_first_no_hidden_weighted_sum")
    axes = axis_contract.get("axes")
    axis_ids = [item.get("id") for item in axes if isinstance(item, Mapping)] if isinstance(axes, list) else []
    if tuple(axis_ids) != v2.AXIS_IDS:
        errors.append(f"axis_contract axes must be exactly {','.join(v2.AXIS_IDS)}")
    if isinstance(axes, list):
        by_id = {str(item.get("id")): item for item in axes if isinstance(item, Mapping)}
        for axis_id in ("qualification_gap", "cost_proxy"):
            axis = by_id.get(axis_id, {})
            if axis.get("status") != "screening_proxy":
                errors.append(f"axis_contract.{axis_id}.status must be screening_proxy")
        for axis_id, direction in {
            "p_success": "maximize",
            "risk_envelope": "minimize",
            "qualification_gap": "minimize",
            "cost_proxy": "minimize",
        }.items():
            if by_id.get(axis_id, {}).get("direction") != direction:
                errors.append(f"axis_contract.{axis_id}.direction must be {direction}")

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append("candidates must be a non-empty list")
        candidates = []
    if payload.get("candidate_count") != len(candidates):
        errors.append(f"candidate_count mismatch: {payload.get('candidate_count')!r} != {len(candidates)}")

    candidate_ids: List[str] = []
    for index, candidate in enumerate(candidates):
        prefix = f"candidates[{index}]"
        if not isinstance(candidate, Mapping):
            errors.append(f"{prefix} must be object")
            continue
        candidate_id = candidate.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id.startswith("optv2-pt-"):
            errors.append(f"{prefix}.candidate_id must start with optv2-pt-")
        else:
            candidate_ids.append(candidate_id)
        if not isinstance(candidate.get("source_candidate_id"), str) or not str(candidate["source_candidate_id"]).startswith("pt-"):
            errors.append(f"{prefix}.source_candidate_id must start with pt-")

        scores = candidate.get("scores")
        if not isinstance(scores, Mapping):
            errors.append(f"{prefix}.scores must be object")
            continue
        vector = scores.get("objective_vector")
        if not isinstance(vector, list) or len(vector) != len(v2.AXIS_IDS) or any(not _is_number(item) for item in vector):
            errors.append(f"{prefix}.scores.objective_vector must contain four numeric axes")
        for axis_index, axis_id in enumerate(v2.AXIS_IDS):
            value = scores.get(axis_id)
            if not _is_number(value) or not 0.0 <= float(value) <= 1.0:
                errors.append(f"{prefix}.scores.{axis_id} must be numeric in [0,1]")
                continue
            if isinstance(vector, list) and axis_index < len(vector) and _is_number(vector[axis_index]):
                if abs(float(vector[axis_index]) - float(value)) > 1e-12:
                    errors.append(f"{prefix}.scores.objective_vector[{axis_index}] must equal {axis_id}")
        if scores.get("rank_key") != "pareto":
            errors.append(f"{prefix}.scores.rank_key must be pareto")

        explain = candidate.get("axis_explainability")
        if not isinstance(explain, Mapping):
            errors.append(f"{prefix}.axis_explainability must be object")
        else:
            qualification = explain.get("qualification_gap")
            cost = explain.get("cost_proxy")
            if not isinstance(qualification, Mapping) or qualification.get("method") != "trust_weighted_search_excursion":
                errors.append(f"{prefix}.axis_explainability.qualification_gap method mismatch")
            if not isinstance(cost, Mapping) or cost.get("method") != "normalized_engineering_resource_pressure":
                errors.append(f"{prefix}.axis_explainability.cost_proxy method mismatch")
        drivers = candidate.get("dominant_drivers")
        if not isinstance(drivers, Mapping):
            errors.append(f"{prefix}.dominant_drivers must be object")
        else:
            driver_ids = drivers.get("parameter_ids")
            if not isinstance(driver_ids, list):
                errors.append(f"{prefix}.dominant_drivers.parameter_ids must be list")
            else:
                for parameter_id in driver_ids:
                    if not isinstance(parameter_id, str):
                        errors.append(f"{prefix}.dominant_drivers.parameter_ids must be string list")
                    elif parameter_id.startswith("code_literal."):
                        errors.append(f"{prefix}.dominant_drivers leaks internal parameter {parameter_id!r}")
            omitted = drivers.get("excluded_internal_parameter_count")
            if not isinstance(omitted, int) or omitted < 0:
                errors.append(f"{prefix}.dominant_drivers.excluded_internal_parameter_count must be int >= 0")

    if len(candidate_ids) != len(set(candidate_ids)):
        errors.append("candidate ids must be unique")

    pareto_ids = payload.get("pareto_frontier_candidate_ids")
    if not isinstance(pareto_ids, list) or any(not isinstance(item, str) for item in pareto_ids):
        errors.append("pareto_frontier_candidate_ids must be string list")
        pareto_ids = []
    expected_pareto = _expected_pareto_ids(candidates)
    if pareto_ids != expected_pareto:
        errors.append(f"pareto_frontier_candidate_ids mismatch: expected {expected_pareto}, got {pareto_ids}")
    if payload.get("frontier_candidate_count") != len(pareto_ids):
        errors.append("frontier_candidate_count must equal pareto_frontier_candidate_ids length")

    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("dimension_count") != 4:
        errors.append("rollup.dimension_count must be 4")
    if rollup.get("axis_ids") != list(v2.AXIS_IDS):
        errors.append("rollup.axis_ids mismatch")
    if rollup.get("aggregation_policy") != "pareto_first_no_hidden_weighted_sum":
        errors.append("rollup.aggregation_policy mismatch")
    for field in (
        "global_optimum_claimed",
        "hidden_weighted_sum_used",
        "calibrated_cost_model_available",
        "qualification_complete",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")

    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list):
        errors.append("blocked_claims must be list")
        blocked = []
    for claim in v2.BLOCKED_CLAIMS:
        if claim not in blocked:
            errors.append(f"blocked_claims must include {claim!r}")
    if not isinstance(payload.get("external_evidence_gaps"), list) or not payload["external_evidence_gaps"]:
        errors.append("external_evidence_gaps must be non-empty")
    if not isinstance(payload.get("interpretation_limits"), list) or not payload["interpretation_limits"]:
        errors.append("interpretation_limits must be non-empty")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")

    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, errors=errors)

    return {
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "candidate_count": len(candidates),
        "frontier_candidate_count": len(pareto_ids),
        "axis_ids": list(v2.AXIS_IDS),
    }


def _render_text(result: Mapping[str, Any]) -> str:
    lines = [
        f"{result['status']}: optimization v2 validation",
        f"- error_count: {result['error_count']}",
        f"- candidate_count: {result['candidate_count']}",
        f"- frontier_candidate_count: {result['frontier_candidate_count']}",
        f"- axes: {','.join(result['axis_ids'])}",
    ]
    if result["errors"]:
        lines.append("- errors:")
        for item in result["errors"]:
            lines.append(f"  - {item}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        repo_root = Path(args.repo_root).resolve()
        artifact_path = Path(args.artifact)
        payload = load_json(repo_root / artifact_path)
        result = validate(payload=payload, repo_root=repo_root)

        try:
            expected = build_optimization_v2_artifact.build_payload(repo_root=repo_root)
        except Exception as exc:  # noqa: BLE001
            result["status"] = "FAIL"
            result["errors"].append(f"determinism precondition failed: {exc}")
        else:
            if v2.canonical_json(expected) != v2.canonical_json(payload):
                result["status"] = "FAIL"
                result["errors"].append("optimization_v2 determinism mismatch: regenerated payload differs")
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
