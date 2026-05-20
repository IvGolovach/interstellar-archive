#!/usr/bin/env python3
"""Validate Mission DAG v2 module-boundary artifact."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Mapping

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from mission.dag import boundary_v2
from scripts import build_mission_dag_v2_boundary_artifact


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_ARTIFACT = Path("artifacts/mission_dag_v2_boundary.v1.json")


def _source_hash_by_path(payload: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in payload.get("source_artifacts", []):
        if isinstance(item, Mapping) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str):
            out[str(item["path"])] = str(item["sha256"])
    return out


def _validate_sources(*, repo_root: Path, payload: Mapping[str, Any], errors: List[str]) -> None:
    expected = {
        "mission/dag/registry/module_registry.v1.json",
        "mission/dag/scenarios/mission_dag_baseline.v1.json",
        "mission/dag/registry/failure_taxonomy.v1.json",
        "mission/dag/schema/module_io.schema.v1.json",
        "mission/dag/schema/scenario_dag.schema.v1.json",
        "mission/dag/schema/failure_taxonomy.schema.v1.json",
        "mission/dag/runner_v1.py",
        "mission/dag/contracts.py",
        "mission/dag/hashchain.py",
        "scripts/ci/mission_dag_validate.py",
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
        actual = boundary_v2._sha256_file(full)
        if by_path[path] != actual:
            errors.append(f"source artifact sha256 mismatch for {path}")


def validate(*, payload: Mapping[str, Any], repo_root: Path | None = None) -> Dict[str, Any]:
    errors: List[str] = []

    if payload.get("schema_version") != boundary_v2.SCHEMA_VERSION:
        errors.append(f"schema_version must be {boundary_v2.SCHEMA_VERSION}")
    if payload.get("generator") != boundary_v2.GENERATOR:
        errors.append(f"generator must be {boundary_v2.GENERATOR}")
    if payload.get("public_scope") != boundary_v2.PUBLIC_SCOPE:
        errors.append("public_scope mismatch")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("registry_version") != "v1":
        errors.append("registry_version must be v1")
    if payload.get("scenario_ref") != "mission/dag/scenarios/mission_dag_baseline.v1.json":
        errors.append("scenario_ref mismatch")
    if payload.get("failure_taxonomy_ref") != "mission/dag/registry/failure_taxonomy.v1.json":
        errors.append("failure_taxonomy_ref mismatch")

    rows = payload.get("module_boundaries")
    if not isinstance(rows, list) or not rows:
        errors.append("module_boundaries must be non-empty")
        rows = []
    if payload.get("module_count") != len(rows):
        errors.append("module_count must equal module_boundaries length")

    module_ids: List[str] = []
    for index, row in enumerate(rows):
        prefix = f"module_boundaries[{index}]"
        if not isinstance(row, Mapping):
            errors.append(f"{prefix} must be object")
            continue
        module_id = row.get("module_id")
        module_type = row.get("module_type")
        if not isinstance(module_id, str) or not module_id:
            errors.append(f"{prefix}.module_id must be non-empty string")
        else:
            module_ids.append(module_id)
        if not isinstance(module_type, str) or not module_type.endswith("Module"):
            errors.append(f"{prefix}.module_type must be Module type")
        if not isinstance(row.get("entrypoint"), str) or ":run_" not in str(row.get("entrypoint")):
            errors.append(f"{prefix}.entrypoint must point to runner function")
        if row.get("input_schema_ref") != "mission/dag/schema/module_io.schema.v1.json":
            errors.append(f"{prefix}.input_schema_ref mismatch")
        if row.get("output_schema_ref") != "mission/dag/schema/module_io.schema.v1.json":
            errors.append(f"{prefix}.output_schema_ref mismatch")
        if not isinstance(row.get("scenario_node_ids"), list) or not row["scenario_node_ids"]:
            errors.append(f"{prefix}.scenario_node_ids must be non-empty")
        if not isinstance(row.get("failure_taxonomy_ids"), list) or not row["failure_taxonomy_ids"]:
            errors.append(f"{prefix}.failure_taxonomy_ids must be non-empty")
        current = row.get("current_v1_support")
        if not isinstance(current, Mapping):
            errors.append(f"{prefix}.current_v1_support must be object")
            current = {}
        for field in (
            "wrapper_over_reduced_order_baseline",
            "module_io_schema_declared",
            "hashchained_module_artifacts",
            "failure_taxonomy_mapping_declared",
        ):
            if current.get(field) is not True:
                errors.append(f"{prefix}.current_v1_support.{field} must be true")
        for field in (
            "independent_backend_id_declared",
            "high_fidelity_state_trace_available",
            "cross_backend_comparison_available",
        ):
            if current.get(field) is not False:
                errors.append(f"{prefix}.current_v1_support.{field} must be false")
        if row.get("v2_boundary_requirements") != boundary_v2.REQUIRED_BOUNDARY_REQUIREMENTS:
            errors.append(f"{prefix}.v2_boundary_requirements mismatch")
        if not isinstance(row.get("open_external_evidence_gaps"), list) or not row["open_external_evidence_gaps"]:
            errors.append(f"{prefix}.open_external_evidence_gaps must be non-empty")
        blocked = row.get("blocked_claims")
        if blocked != boundary_v2.BLOCKED_CLAIMS:
            errors.append(f"{prefix}.blocked_claims mismatch")

    if len(module_ids) != len(set(module_ids)):
        errors.append("module ids must be unique")

    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("module_count") != payload.get("module_count"):
        errors.append("rollup.module_count mismatch")
    if rollup.get("failure_taxonomy_mapping_module_count") != payload.get("module_count"):
        errors.append("rollup.failure_taxonomy_mapping_module_count must equal module_count")
    for field in (
        "module_io_schema_contract_available",
        "hashchain_contract_available",
        "state_trace_contract_complete",
    ):
        if rollup.get(field) is not True:
            errors.append(f"rollup.{field} must be true")
    for field in (
        "independent_backend_complete",
        "high_fidelity_state_traces_available",
        "cross_backend_comparison_available",
        "flight_ready_module_claimed",
        "external_reproduction_completed",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    if payload.get("blocked_claims") != boundary_v2.BLOCKED_CLAIMS:
        errors.append("blocked_claims mismatch")
    if not isinstance(payload.get("interpretation_limits"), list) or not payload["interpretation_limits"]:
        errors.append("interpretation_limits must be non-empty")
    if not isinstance(payload.get("external_evidence_gaps"), list) or not payload["external_evidence_gaps"]:
        errors.append("external_evidence_gaps must be non-empty")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")

    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, errors=errors)

    return {
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "module_count": len(rows),
        "taxonomy_mapped_count": rollup.get("failure_taxonomy_mapping_module_count"),
    }


def _render_text(result: Mapping[str, Any]) -> str:
    lines = [
        f"{result['status']}: mission DAG v2 boundary validation",
        f"- error_count: {result['error_count']}",
        f"- module_count: {result['module_count']}",
        f"- taxonomy_mapped_count: {result['taxonomy_mapped_count']}",
    ]
    if result["errors"]:
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
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
        payload = load_json(repo_root / Path(args.artifact))
        result = validate(payload=payload, repo_root=repo_root)
        try:
            expected = build_mission_dag_v2_boundary_artifact.build_payload(repo_root=repo_root)
        except Exception as exc:  # noqa: BLE001
            result["status"] = "FAIL"
            result["errors"].append(f"determinism precondition failed: {exc}")
        else:
            if boundary_v2.canonical_json(expected) != boundary_v2.canonical_json(payload):
                result["status"] = "FAIL"
                result["errors"].append("mission_dag_v2_boundary determinism mismatch: regenerated payload differs")
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
