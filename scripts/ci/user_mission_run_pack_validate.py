#!/usr/bin/env python3
"""Build and validate a user mission run pack in an isolated output directory."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mission.baseline.validation import validate_scenario, validate_schema_contract
from mission.user_runs.catalog import (
    DEFAULT_OUTPUT_ROOT,
    SUMMARY_SCHEMA_VERSION,
    validate_user_mission_run_catalog,
    validate_user_run_summary,
)


EXPECTED_TOP_LEVEL_FILES = {
    "COMPILED_MISSION_SCENARIO.json",
    "DAG_RUN_SUMMARY.json",
    "RUN_REPORT.md",
    "SOURCE_MANIFEST.json",
    "USER_RUN_SUMMARY.json",
    "meta.json",
}
EXPECTED_SOURCE_PATHS = {
    "artifacts/user_mission_run_catalog.v1.json",
    "artifacts/mission_feasibility_screen.v1.json",
    "artifacts/capsule_risk_budget.v1.json",
    "artifacts/capsule_survivability_lab.v1.json",
    "mission/dag/scenarios/mission_dag_baseline.v1.json",
    "mission/BASELINE_SCENARIO_v1.json",
    "mission/MISSION_SCHEMA_v1.json",
    "mission/USER_MISSION_RUN_CATALOG_SPEC_v1.md",
    "mission/user_runs/catalog.py",
    "scripts/run_user_mission_scenario.py",
    "scripts/ci/user_mission_run_pack_validate.py",
}


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_default_selection(repo_root: Path) -> tuple[str, str, str]:
    catalog = _load_json(repo_root / "artifacts/user_mission_run_catalog.v1.json")
    errors = validate_user_mission_run_catalog(catalog)
    if errors:
        raise ValueError("user mission run catalog invalid: " + "; ".join(errors))
    default_run_id = catalog.get("default_run_id")
    for row in catalog.get("run_rows", []):
        if isinstance(row, Mapping) and row.get("run_id") == default_run_id:
            selection = row.get("selection")
            if isinstance(selection, Mapping):
                return str(selection["target_id"]), str(selection["velocity_id"]), str(row["run_id"])
    raise ValueError("default run row not found in user mission run catalog")


def _run_pack(
    *,
    repo_root: Path,
    target_id: str,
    velocity_id: str,
    mode: str,
    seed: int,
    run_id: str,
    output_root: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/run_user_mission_scenario.py",
            "--target-id",
            target_id,
            "--velocity-id",
            velocity_id,
            "--mode",
            mode,
            "--seed",
            str(seed),
            "--run-id",
            run_id,
            "--output-root",
            str(output_root),
            "--verify-deterministic",
            "--format",
            "json",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def _validate_source_manifest(repo_root: Path, manifest: Mapping[str, Any], errors: List[str]) -> None:
    entries = manifest.get("source_manifest")
    if not isinstance(entries, list):
        errors.append("SOURCE_MANIFEST.json must contain source_manifest list")
        return
    by_path = {str(entry.get("path")): entry for entry in entries if isinstance(entry, Mapping)}
    missing = sorted(EXPECTED_SOURCE_PATHS - set(by_path))
    for path in missing:
        errors.append(f"source_manifest missing {path}")
    for path, entry in by_path.items():
        if path not in EXPECTED_SOURCE_PATHS:
            continue
        sha = entry.get("sha256")
        if not isinstance(sha, str) or len(sha) != 64:
            errors.append(f"source_manifest sha256 invalid for {path}")
            continue
        source_path = repo_root / path
        if not source_path.exists():
            errors.append(f"source_manifest path does not exist: {path}")


def validate_pack(repo_root: Path, output_dir: Path, runner_payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if runner_payload.get("verdict") != "PASS":
        errors.append("runner payload verdict must be PASS")
    if runner_payload.get("determinism", {}).get("verdict") != "PASS":
        errors.append("runner payload determinism verdict must be PASS")
    if str(runner_payload.get("output_dir")) != str(output_dir):
        errors.append("runner payload output_dir mismatch")

    if not output_dir.exists():
        errors.append(f"output_dir missing: {output_dir}")
        return errors
    top_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    if top_files != EXPECTED_TOP_LEVEL_FILES:
        errors.append(f"top-level files mismatch: expected {sorted(EXPECTED_TOP_LEVEL_FILES)}, got {sorted(top_files)}")
    if not (output_dir / "mission_dag" / "manifest.json").exists():
        errors.append("mission_dag/manifest.json missing")

    summary = _load_json(output_dir / "USER_RUN_SUMMARY.json")
    errors.extend(validate_user_run_summary(summary))
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        errors.append(f"USER_RUN_SUMMARY schema must be {SUMMARY_SCHEMA_VERSION}")
    if summary.get("verdict") != "review_required":
        errors.append("USER_RUN_SUMMARY verdict must remain review_required")
    if summary.get("non_certification_notice") is not True:
        errors.append("USER_RUN_SUMMARY non_certification_notice must be true")
    if "flight ready" not in (summary.get("blocked_claims") or []):
        errors.append("USER_RUN_SUMMARY must block flight ready claims")
    dag = summary.get("dag_execution")
    if not isinstance(dag, Mapping):
        errors.append("USER_RUN_SUMMARY.dag_execution must be object")
    else:
        if dag.get("status") != "PASS":
            errors.append("dag_execution.status must be PASS")
        if dag.get("hashchain_status") != "PASS":
            errors.append("dag_execution.hashchain_status must be PASS")
        if dag.get("failure_taxonomy_status") != "PASS":
            errors.append("dag_execution.failure_taxonomy_status must be PASS")
        if dag.get("determinism_verdict") != "PASS":
            errors.append("dag_execution.determinism_verdict must be PASS")

    dag_summary = _load_json(output_dir / "DAG_RUN_SUMMARY.json")
    if dag_summary != summary.get("dag_execution"):
        errors.append("DAG_RUN_SUMMARY.json must match USER_RUN_SUMMARY.dag_execution")
    source_manifest = _load_json(output_dir / "SOURCE_MANIFEST.json")
    _validate_source_manifest(repo_root, source_manifest, errors)

    schema = _load_json(repo_root / "mission/MISSION_SCHEMA_v1.json")
    scenario = _load_json(output_dir / "COMPILED_MISSION_SCENARIO.json")
    errors.extend(validate_schema_contract(schema))
    errors.extend(validate_scenario(schema, scenario))
    if not str(scenario.get("seed", "")).startswith("user-mission-run:"):
        errors.append("compiled scenario seed must be user-mission-run:*")

    meta = _load_json(output_dir / "meta.json")
    if meta.get("summary_sha256") != runner_payload.get("summary_sha256"):
        errors.append("meta.summary_sha256 must match runner payload")
    if set(meta.get("output_files", [])) != EXPECTED_TOP_LEVEL_FILES - {"meta.json"}:
        errors.append("meta.output_files must list non-meta top-level output files")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--target-id")
    parser.add_argument("--velocity-id")
    parser.add_argument("--mode", choices=("realistic", "speculative", "dual"), default="dual")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--run-id")
    parser.add_argument("--output-root")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    default_target, default_velocity, default_run_id = _load_default_selection(repo_root)
    target_id = args.target_id or default_target
    velocity_id = args.velocity_id or default_velocity
    run_id = args.run_id or default_run_id

    temp_context = None
    if args.output_root:
        output_root = Path(args.output_root)
        if not output_root.is_absolute():
            output_root = repo_root / output_root
    else:
        temp_context = tempfile.TemporaryDirectory()
        output_root = Path(temp_context.name) / DEFAULT_OUTPUT_ROOT

    try:
        proc = _run_pack(
            repo_root=repo_root,
            target_id=target_id,
            velocity_id=velocity_id,
            mode=args.mode,
            seed=int(args.seed),
            run_id=run_id,
            output_root=output_root,
        )
        errors: List[str] = []
        runner_payload: Dict[str, Any] = {}
        if proc.returncode != 0:
            errors.append(f"runner exited {proc.returncode}: {proc.stdout.strip()} {proc.stderr.strip()}".strip())
        else:
            try:
                runner_payload = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"runner JSON output invalid: {exc}")
        output_dir = output_root / run_id
        if not errors:
            errors.extend(validate_pack(repo_root, output_dir, runner_payload))
        result = {
            "status": "PASS" if not errors else "FAIL",
            "run_id": run_id,
            "target_id": target_id,
            "velocity_id": velocity_id,
            "mode": args.mode,
            "seed": int(args.seed),
            "output_dir": str(output_dir),
            "error_count": len(errors),
            "errors": errors,
        }
        if args.format == "json":
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{result['status']}: user mission run pack validation")
            print(f"- run_id: {run_id}")
            print(f"- output_dir: {output_dir}")
            print(f"- error_count: {len(errors)}")
            for error in errors:
                print(f"- error: {error}")
        return 0 if not errors or not args.strict else 2
    finally:
        if temp_context is not None:
            temp_context.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
