#!/usr/bin/env python3
"""Validate browser-facing deterministic artifacts without ops/ dependency."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Sequence

try:
    from .script_io import render_json, render_output, write_text
except ImportError:
    from script_io import render_json, render_output, write_text

DEFAULT_ARTIFACTS = (
    Path("artifacts/parameter_drilldown_manifest.json"),
    Path("artifacts/parameter_static_usage_graph.json"),
    Path("artifacts/parameter_evidence_index.json"),
    Path("artifacts/p_success_defensibility.json"),
    Path("artifacts/failure_surface_baseline.v1.json"),
    Path("artifacts/objective_score_baseline.v1.json"),
    Path("artifacts/optimization_search_space.v1.json"),
    Path("artifacts/optimization_frontier_realistic.v1.json"),
    Path("artifacts/capsule_survivability_lab.v1.json"),
    Path("artifacts/capsule_risk_budget.v1.json"),
    Path("artifacts/mission_feasibility_screen.v1.json"),
    Path("artifacts/user_mission_run_catalog.v1.json"),
    Path("artifacts/runtime_scenario_generation.v1.json"),
    Path("artifacts/cost_procurement_architecture_feasibility.v1.json"),
    Path("artifacts/external_validation_review_pack.v1.json"),
    Path("artifacts/public_narrative_hardening.v1.json"),
    Path("artifacts/external_validation_execution_ledger.v1.json"),
    Path("artifacts/independent_physics_backend_comparison.v1.json"),
    Path("artifacts/capsule_qualification_evidence_pack.v1.json"),
    Path("artifacts/evidence_upgrade_closure.v1.json"),
    Path("artifacts/external_reproduction_kit.v1.json"),
    Path("artifacts/external_evidence_intake.v1.json"),
    Path("artifacts/external_validation_campaign.v1.json"),
    Path("artifacts/release_candidate_readiness.v1.json"),
    Path("artifacts/mission_probability_coupling.v1.json"),
    Path("artifacts/uncertainty_interactions.v1.json"),
    Path("artifacts/evidence_upgrade_campaign.v1.json"),
    Path("artifacts/optimization_v2_frontier.v1.json"),
    Path("artifacts/mission_dag_v2_boundary.v1.json"),
    Path("artifacts/roadmap_closure.v1.json"),
    Path("artifacts/browser_dataset.v1.json"),
)
DEFAULT_BUILDERS = (
    Path("scripts/build_parameter_drilldown_artifacts.py"),
    Path("scripts/build_failure_surface_artifacts.py"),
    Path("scripts/build_objective_artifacts.py"),
    Path("scripts/build_optimization_frontier.py"),
    Path("scripts/build_capsule_survivability_artifact.py"),
    Path("scripts/build_capsule_risk_budget_artifact.py"),
    Path("scripts/build_mission_feasibility_screen_artifact.py"),
    Path("scripts/build_user_mission_run_catalog_artifact.py"),
    Path("scripts/build_runtime_scenario_generation_artifact.py"),
    Path("scripts/build_cost_procurement_architecture_feasibility_artifact.py"),
    Path("scripts/build_external_validation_review_pack_artifact.py"),
    Path("scripts/build_public_narrative_hardening_artifact.py"),
    Path("scripts/build_external_validation_execution_ledger_artifact.py"),
    Path("scripts/build_independent_physics_backend_comparison_artifact.py"),
    Path("scripts/build_capsule_qualification_evidence_pack_artifact.py"),
    Path("scripts/build_evidence_upgrade_closure_artifact.py"),
    Path("scripts/build_external_reproduction_kit_artifact.py"),
    Path("scripts/build_external_evidence_intake_artifact.py"),
    Path("scripts/build_external_validation_campaign_artifact.py"),
    Path("scripts/build_mission_probability_coupling_artifact.py"),
    Path("scripts/build_uncertainty_interactions_artifact.py"),
    Path("scripts/build_evidence_upgrade_campaign_artifact.py"),
    Path("scripts/build_optimization_v2_artifact.py"),
    Path("scripts/build_mission_dag_v2_boundary_artifact.py"),
    Path("scripts/build_roadmap_closure_artifact.py"),
    Path("scripts/build_release_candidate_readiness_artifact.py"),
    Path("scripts/build_browser_dataset_artifact.py"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_builder(repo_root: Path, builder: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["LANG"] = "C"
    env["LC_ALL"] = "C"
    return subprocess.run(
        [sys.executable, str(builder), "--repo-root", str(repo_root)],
        cwd=repo_root,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def _run_builders(repo_root: Path, builders: Sequence[Path]) -> List[subprocess.CompletedProcess[str]]:
    return [_run_builder(repo_root, builder) for builder in builders]


def _compute_hashes(repo_root: Path, artifacts: Sequence[Path]) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for path in artifacts:
        full = repo_root / path
        if not full.exists():
            raise FileNotFoundError(f"missing artifact: {path}")
        hashes[str(path)] = _sha256(full)
    return hashes


def validate(*, repo_root: Path, artifacts: Sequence[Path], builders: Sequence[Path]) -> Dict[str, Any]:
    before = _compute_hashes(repo_root, artifacts)

    ops_path = repo_root / "ops"
    hidden_ops_path: Path | None = None
    temp_root = Path(tempfile.mkdtemp(prefix="artifact-determinism-"))

    try:
        if ops_path.exists():
            hidden_ops_path = temp_root / "ops.hidden"
            shutil.move(str(ops_path), str(hidden_ops_path))

        build_results = _run_builders(repo_root, builders)
        failed = next((result for result in build_results if result.returncode != 0), None)

        if failed is not None:
            return {
                "status": "FAIL",
                "reason": "builder_failed_without_ops",
                "builder_exit_code": failed.returncode,
                "builder_stdout": failed.stdout,
                "builder_stderr": failed.stderr,
                "before": before,
                "after": {},
                "changed": [],
            }

        after = _compute_hashes(repo_root, artifacts)
        changed = [path for path in sorted(before) if before[path] != after[path]]
        status = "PASS" if not changed else "FAIL"
        return {
            "status": status,
            "reason": "ok" if status == "PASS" else "artifact_hash_drift",
            "builder_exit_code": 0,
            "builder_stdout": "\n".join(result.stdout for result in build_results if result.stdout),
            "builder_stderr": "\n".join(result.stderr for result in build_results if result.stderr),
            "before": before,
            "after": after,
            "changed": changed,
        }
    finally:
        if hidden_ops_path and hidden_ops_path.exists():
            shutil.move(str(hidden_ops_path), str(ops_path))
        shutil.rmtree(temp_root, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--builder",
        action="append",
        default=[],
        help="Builder path relative to repo root; may be specified multiple times.",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Artifact path relative to repo root; may be specified multiple times.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    parser.add_argument("--strict", action="store_true", default=True)
    parser.add_argument("--no-strict", dest="strict", action="store_false")
    return parser.parse_args()


def _render_text(result: Dict[str, Any]) -> str:
    lines = [
        f"{result['status']}: browser-facing artifact determinism without ops",
        f"- reason: {result['reason']}",
        f"- builder_exit_code: {result['builder_exit_code']}",
    ]
    if result.get("changed"):
        lines.append(f"- changed_artifacts: {len(result['changed'])}")
        for path in result["changed"]:
            lines.append(f"  - {path}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    builders = [Path(item) for item in args.builder] if args.builder else list(DEFAULT_BUILDERS)
    resolved_builders: List[Path] = []
    for builder in builders:
        resolved_builders.append(builder if builder.is_absolute() else (repo_root / builder).resolve())

    artifacts = [Path(item) for item in args.artifact] if args.artifact else list(DEFAULT_ARTIFACTS)

    try:
        result = validate(repo_root=repo_root, artifacts=artifacts, builders=resolved_builders)
    except Exception as exc:  # pragma: no cover - defensive exit path
        payload = {
            "status": "ERROR",
            "reason": "internal_error",
            "error": str(exc),
        }
        rendered = render_json(payload)
        if args.format == "json":
            print(rendered)
            if args.output:
                write_text(Path(args.output), rendered)
        else:
            message = f"ERROR: internal error: {exc}"
            print(message)
            if args.output:
                write_text(Path(args.output), message)
        return 3

    rendered = render_output(result, output_format=args.format, text_renderer=_render_text)
    print(rendered)
    if args.output:
        write_text(Path(args.output), rendered)

    if result["status"] == "PASS":
        return 0
    return 2 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
