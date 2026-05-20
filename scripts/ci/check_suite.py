#!/usr/bin/env python3
"""Run the canonical repository validation suite used by local and CI checks."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
MISSION_DAG_RUN_ID = "check-suite-mission-dag-v1"
OPTIMIZATION_RUN_ID = "check-suite-optimization-v1"
OPTIMIZATION_VERIFY_RUN_ID = "check-suite-optimization-v1-verify"


@dataclass(frozen=True)
class Step:
    name: str
    command: Tuple[str, ...]


def _env() -> dict[str, str]:
    return {**os.environ, "LANG": "C", "LC_ALL": "C"}


def _git(repo_root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or proc.stdout.strip() or f"exit={proc.returncode}"
        raise ValueError(f"git {' '.join(args)} failed: {stderr}")
    return proc.stdout.strip()


def resolve_base_head(repo_root: Path, base_sha: str | None, head_sha: str | None) -> tuple[str, str]:
    if bool(base_sha) != bool(head_sha):
        raise ValueError("BASE_SHA and HEAD_SHA must be provided together")
    if base_sha and head_sha:
        return base_sha, head_sha

    head = _git(repo_root, "rev-parse", "HEAD")
    try:
        _git(repo_root, "rev-parse", "--verify", "origin/main")
        base = _git(repo_root, "merge-base", "origin/main", "HEAD")
    except ValueError:
        roots = _git(repo_root, "rev-list", "--max-parents=0", "HEAD").splitlines()
        base = roots[-1] if roots else head

    return base, head


def build_steps(base_sha: str, head_sha: str, remote_proof_dir: str | None) -> List[Step]:
    python = sys.executable
    scratch_evidence_status = str(
        (Path(tempfile.gettempdir()) / f"check-suite-evidence-status-{os.getpid()}.json").resolve()
    )
    scratch_external_pack = str(
        (Path(tempfile.gettempdir()) / f"check-suite-external-reproduction-pack-{os.getpid()}").resolve()
    )
    steps: List[Step] = [
        Step(
            "Validate required repository files",
            (python, "scripts/ci/required_paths_validate.py", "--strict"),
        ),
        Step("Repo root guard", (python, "scripts/ci/repo_root_guard.py", "--strict")),
        Step("Validate CITATION.cff", (python, "scripts/ci/validate_citation_cff.py")),
        Step("Validate MODEL_VERSION.json", (python, "scripts/ci/validate_model_version.py")),
        Step("Version contract validate", (python, "scripts/ci/version_contract_validate.py", "--strict")),
        Step(
            "Validate mission schema and baseline scenario",
            (python, "scripts/mission_baseline_check.py", "--validate-only"),
        ),
        Step(
            "Mission baseline deterministic check",
            (python, "scripts/mission_baseline_check.py", "--mode", "dual", "--verify-deterministic"),
        ),
        Step(
            "Golden run deterministic check",
            (python, "scripts/run_golden.py", "--verify-deterministic"),
        ),
        Step("Benchmark compare", (python, "scripts/benchmark_compare.py")),
        Step("Benchmark drift guard", (python, "scripts/benchmark_drift_guard.py")),
        Step(
            "Validate evidence contract",
            (python, "scripts/ci/evidence_validate.py", "--strict", "--base", base_sha, "--head", head_sha),
        ),
        Step(
            "Parameter literal scan",
            (python, "scripts/ci/parameter_literal_scan.py", "--strict", "--format", "text"),
        ),
        Step(
            "Parameter registry validate",
            (python, "scripts/ci/parameter_registry_validate.py", "--strict"),
        ),
        Step(
            "Parameter evidence validate",
            (python, "scripts/ci/parameter_evidence_validate.py", "--strict"),
        ),
        Step("Evidence sync validate", (python, "scripts/ci/evidence_sync_validate.py", "--strict")),
        Step(
            "Build parameter drilldown artifacts",
            (python, "scripts/build_parameter_drilldown_artifacts.py"),
        ),
        Step("Build failure surface artifacts", (python, "scripts/build_failure_surface_artifacts.py")),
        Step(
            "Validate failure surface artifact",
            (python, "scripts/ci/failure_surface_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed failure surface artifact",
            ("git", "diff", "--exit-code", "artifacts/failure_surface_baseline.v1.json"),
        ),
        Step("Build objective artifacts", (python, "scripts/build_objective_artifacts.py")),
        Step(
            "Validate objective contract artifact",
            (python, "scripts/ci/objective_contract_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed objective score artifact",
            ("git", "diff", "--exit-code", "artifacts/objective_score_baseline.v1.json"),
        ),
        Step(
            "Build optimization frontier artifacts",
            (python, "scripts/build_optimization_frontier.py"),
        ),
        Step(
            "Validate optimization frontier artifacts",
            (python, "scripts/ci/optimization_frontier_validate.py", "--strict"),
        ),
        Step(
            "Validate risk envelope artifacts",
            (python, "scripts/ci/risk_envelope_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed optimization frontier artifacts",
            (
                "git",
                "diff",
                "--exit-code",
                "artifacts/optimization_search_space.v1.json",
                "artifacts/optimization_frontier_realistic.v1.json",
            ),
        ),
        Step("Build capsule survivability artifact", (python, "scripts/build_capsule_survivability_artifact.py")),
        Step(
            "Validate capsule survivability artifact",
            (python, "scripts/ci/capsule_survivability_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed capsule survivability artifact",
            ("git", "diff", "--exit-code", "artifacts/capsule_survivability_lab.v1.json"),
        ),
        Step("Build capsule risk budget artifact", (python, "scripts/build_capsule_risk_budget_artifact.py")),
        Step(
            "Validate capsule risk budget artifact",
            (python, "scripts/ci/capsule_risk_budget_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed capsule risk budget artifact",
            ("git", "diff", "--exit-code", "artifacts/capsule_risk_budget.v1.json"),
        ),
        Step("Build mission feasibility screen artifact", (python, "scripts/build_mission_feasibility_screen_artifact.py")),
        Step(
            "Validate mission feasibility screen artifact",
            (python, "scripts/ci/mission_feasibility_screen_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed mission feasibility screen artifact",
            ("git", "diff", "--exit-code", "artifacts/mission_feasibility_screen.v1.json"),
        ),
        Step("Build user mission run catalog artifact", (python, "scripts/build_user_mission_run_catalog_artifact.py")),
        Step(
            "Validate user mission run catalog artifact",
            (python, "scripts/ci/user_mission_run_catalog_validate.py", "--strict"),
        ),
        Step(
            "Build runtime scenario generation artifact",
            (python, "scripts/build_runtime_scenario_generation_artifact.py"),
        ),
        Step(
            "Validate runtime scenario generation artifact",
            (python, "scripts/ci/runtime_scenario_generation_validate.py", "--strict"),
        ),
        Step(
            "Validate default user mission run pack",
            (
                python,
                "scripts/ci/user_mission_run_pack_validate.py",
                "--strict",
            ),
        ),
        Step(
            "Enforce committed user mission run catalog artifact",
            ("git", "diff", "--exit-code", "artifacts/user_mission_run_catalog.v1.json"),
        ),
        Step(
            "Enforce committed runtime scenario generation artifact",
            ("git", "diff", "--exit-code", "artifacts/runtime_scenario_generation.v1.json"),
        ),
        Step(
            "Build mission probability coupling artifact",
            (python, "scripts/build_mission_probability_coupling_artifact.py"),
        ),
        Step(
            "Validate mission probability coupling artifact",
            (python, "scripts/ci/mission_probability_coupling_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed mission probability coupling artifact",
            ("git", "diff", "--exit-code", "artifacts/mission_probability_coupling.v1.json"),
        ),
        Step(
            "Build uncertainty interactions artifact",
            (python, "scripts/build_uncertainty_interactions_artifact.py"),
        ),
        Step(
            "Validate uncertainty interactions artifact",
            (python, "scripts/ci/uncertainty_interactions_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed uncertainty interactions artifact",
            ("git", "diff", "--exit-code", "artifacts/uncertainty_interactions.v1.json"),
        ),
        Step(
            "Build evidence upgrade campaign artifact",
            (python, "scripts/build_evidence_upgrade_campaign_artifact.py"),
        ),
        Step(
            "Validate evidence upgrade campaign artifact",
            (python, "scripts/ci/evidence_upgrade_campaign_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed evidence upgrade campaign artifact",
            ("git", "diff", "--exit-code", "artifacts/evidence_upgrade_campaign.v1.json"),
        ),
        Step(
            "Build optimization v2 artifact",
            (python, "scripts/build_optimization_v2_artifact.py"),
        ),
        Step(
            "Validate optimization v2 artifact",
            (python, "scripts/ci/optimization_v2_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed optimization v2 artifact",
            ("git", "diff", "--exit-code", "artifacts/optimization_v2_frontier.v1.json"),
        ),
        Step(
            "Build mission DAG v2 boundary artifact",
            (python, "scripts/build_mission_dag_v2_boundary_artifact.py"),
        ),
        Step(
            "Validate mission DAG v2 boundary artifact",
            (python, "scripts/ci/mission_dag_v2_boundary_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed mission DAG v2 boundary artifact",
            ("git", "diff", "--exit-code", "artifacts/mission_dag_v2_boundary.v1.json"),
        ),
        Step(
            "Build cost/procurement/architecture feasibility artifact",
            (python, "scripts/build_cost_procurement_architecture_feasibility_artifact.py"),
        ),
        Step(
            "Validate cost/procurement/architecture feasibility artifact",
            (python, "scripts/ci/cost_procurement_architecture_feasibility_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed cost/procurement/architecture feasibility artifact",
            ("git", "diff", "--exit-code", "artifacts/cost_procurement_architecture_feasibility.v1.json"),
        ),
        Step(
            "Build external validation review pack artifact",
            (python, "scripts/build_external_validation_review_pack_artifact.py"),
        ),
        Step(
            "Validate external validation review pack artifact",
            (python, "scripts/ci/external_validation_review_pack_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed external validation review pack artifact",
            ("git", "diff", "--exit-code", "artifacts/external_validation_review_pack.v1.json"),
        ),
        Step(
            "Build public narrative hardening artifact",
            (python, "scripts/build_public_narrative_hardening_artifact.py"),
        ),
        Step(
            "Validate public narrative hardening artifact",
            (python, "scripts/ci/public_narrative_hardening_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed public narrative hardening artifact",
            ("git", "diff", "--exit-code", "artifacts/public_narrative_hardening.v1.json"),
        ),
        Step(
            "Build external validation execution ledger artifact",
            (python, "scripts/build_external_validation_execution_ledger_artifact.py"),
        ),
        Step(
            "Validate external validation execution ledger artifact",
            (python, "scripts/ci/external_validation_execution_ledger_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed external validation execution ledger artifact",
            ("git", "diff", "--exit-code", "artifacts/external_validation_execution_ledger.v1.json"),
        ),
        Step(
            "Build independent physics backend comparison artifact",
            (python, "scripts/build_independent_physics_backend_comparison_artifact.py"),
        ),
        Step(
            "Validate independent physics backend comparison artifact",
            (python, "scripts/ci/independent_physics_backend_comparison_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed independent physics backend comparison artifact",
            ("git", "diff", "--exit-code", "artifacts/independent_physics_backend_comparison.v1.json"),
        ),
        Step(
            "Build capsule qualification evidence pack artifact",
            (python, "scripts/build_capsule_qualification_evidence_pack_artifact.py"),
        ),
        Step(
            "Validate capsule qualification evidence pack artifact",
            (python, "scripts/ci/capsule_qualification_evidence_pack_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed capsule qualification evidence pack artifact",
            ("git", "diff", "--exit-code", "artifacts/capsule_qualification_evidence_pack.v1.json"),
        ),
        Step(
            "Build evidence upgrade closure artifact",
            (python, "scripts/build_evidence_upgrade_closure_artifact.py"),
        ),
        Step(
            "Validate evidence upgrade closure artifact",
            (python, "scripts/ci/evidence_upgrade_closure_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed evidence upgrade closure artifact",
            ("git", "diff", "--exit-code", "artifacts/evidence_upgrade_closure.v1.json"),
        ),
        Step(
            "Build external reproduction kit artifact",
            (python, "scripts/build_external_reproduction_kit_artifact.py"),
        ),
        Step(
            "Validate external reproduction kit artifact",
            (python, "scripts/ci/external_reproduction_kit_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed external reproduction kit artifact",
            ("git", "diff", "--exit-code", "artifacts/external_reproduction_kit.v1.json"),
        ),
        Step(
            "Build external evidence intake artifact",
            (python, "scripts/build_external_evidence_intake_artifact.py"),
        ),
        Step(
            "Validate external evidence intake artifact",
            (python, "scripts/ci/external_evidence_intake_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed external evidence intake artifact",
            ("git", "diff", "--exit-code", "artifacts/external_evidence_intake.v1.json"),
        ),
        Step(
            "Build external validation campaign artifact",
            (python, "scripts/build_external_validation_campaign_artifact.py"),
        ),
        Step(
            "Validate external validation campaign artifact",
            (python, "scripts/ci/external_validation_campaign_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed external validation campaign artifact",
            ("git", "diff", "--exit-code", "artifacts/external_validation_campaign.v1.json"),
        ),
        Step(
            "Export external reproduction pack",
            (python, "scripts/export_external_reproduction_pack.py", "--output-dir", scratch_external_pack, "--no-zip"),
        ),
        Step(
            "Validate exported external reproduction pack",
            (python, "scripts/ci/external_reproduction_pack_validate.py", scratch_external_pack, "--strict"),
        ),
        Step("Build roadmap closure artifact", (python, "scripts/build_roadmap_closure_artifact.py")),
        Step(
            "Validate roadmap closure artifact",
            (python, "scripts/ci/roadmap_closure_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed roadmap closure artifact",
            ("git", "diff", "--exit-code", "artifacts/roadmap_closure.v1.json"),
        ),
        Step(
            "Build release candidate readiness artifact",
            (python, "scripts/build_release_candidate_readiness_artifact.py"),
        ),
        Step(
            "Validate release candidate readiness artifact",
            (python, "scripts/ci/release_candidate_readiness_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed release candidate readiness artifact",
            ("git", "diff", "--exit-code", "artifacts/release_candidate_readiness.v1.json"),
        ),
        Step(
            "Build browser dataset artifact",
            (python, "scripts/build_browser_dataset_artifact.py"),
        ),
        Step(
            "Validate browser dataset artifact",
            (python, "scripts/ci/browser_dataset_validate.py", "--strict"),
        ),
        Step(
            "Validate browser-facing artifact determinism",
            (python, "scripts/ci/artifact_determinism_validate.py", "--strict"),
        ),
        Step(
            "Enforce committed browser-facing artifacts",
            (
                "git",
                "diff",
                "--exit-code",
                "artifacts/parameter_drilldown_manifest.json",
                "artifacts/parameter_static_usage_graph.json",
                "artifacts/parameter_evidence_index.json",
                "artifacts/p_success_defensibility.json",
                "artifacts/capsule_survivability_lab.v1.json",
                "artifacts/capsule_risk_budget.v1.json",
                "artifacts/mission_feasibility_screen.v1.json",
                "artifacts/user_mission_run_catalog.v1.json",
                "artifacts/runtime_scenario_generation.v1.json",
                "artifacts/mission_probability_coupling.v1.json",
                "artifacts/uncertainty_interactions.v1.json",
                "artifacts/evidence_upgrade_campaign.v1.json",
                "artifacts/optimization_v2_frontier.v1.json",
                "artifacts/mission_dag_v2_boundary.v1.json",
                "artifacts/cost_procurement_architecture_feasibility.v1.json",
                "artifacts/external_validation_review_pack.v1.json",
                "artifacts/public_narrative_hardening.v1.json",
                "artifacts/external_validation_execution_ledger.v1.json",
                "artifacts/independent_physics_backend_comparison.v1.json",
                "artifacts/capsule_qualification_evidence_pack.v1.json",
                "artifacts/evidence_upgrade_closure.v1.json",
                "artifacts/external_reproduction_kit.v1.json",
                "artifacts/external_evidence_intake.v1.json",
                "artifacts/external_validation_campaign.v1.json",
                "artifacts/roadmap_closure.v1.json",
                "artifacts/release_candidate_readiness.v1.json",
                "artifacts/browser_dataset.v1.json",
            ),
        ),
        Step(
            "Parameter domain guard",
            (
                python,
                "scripts/ci/parameter_domain_guard.py",
                "--strict",
                "--divergence-threshold",
                "20",
                "--format",
                "json",
            ),
        ),
        Step(
            "Parameter sensitivity report (realistic)",
            (
                python,
                "scripts/ci/parameter_sensitivity_report.py",
                "--mode",
                "realistic",
                "--baseline",
                "mission/BASELINE_SCENARIO_v1.json",
                "--samples",
                "64",
            ),
        ),
        Step(
            "Parameter sensitivity report (speculative)",
            (
                python,
                "scripts/ci/parameter_sensitivity_report.py",
                "--mode",
                "speculative",
                "--baseline",
                "mission/BASELINE_SCENARIO_v1.json",
                "--samples",
                "64",
            ),
        ),
        Step("Defensibility validate", (python, "scripts/ci/defensibility_validate.py", "--strict")),
        Step("Optimization guard", (python, "scripts/optimization_guard.py", "--strict")),
        Step(
            "Run optimization engine",
            (
                python,
                "scripts/run_optimization.py",
                "--mode",
                "realistic",
                "--samples",
                "96",
                "--seed",
                "42",
                "--run-id",
                OPTIMIZATION_RUN_ID,
            ),
        ),
        Step(
            "Run optimization deterministic verification",
            (
                python,
                "scripts/run_optimization.py",
                "--mode",
                "realistic",
                "--samples",
                "96",
                "--seed",
                "42",
                "--run-id",
                OPTIMIZATION_VERIFY_RUN_ID,
                "--verify-deterministic",
            ),
        ),
        Step(
            "Optimization coverage gate",
            (python, "scripts/ci/optimization_coverage.py", "--min", "90"),
        ),
        Step(
            "Validate mission DAG contracts",
            (python, "scripts/ci/mission_dag_validate.py", "--strict"),
        ),
        Step(
            "DAG dependency graph audit",
            (python, "scripts/ci/dag_dependency_graph.py", "--strict"),
        ),
        Step(
            "Run mission DAG deterministic check",
            (
                python,
                "scripts/run_mission_dag.py",
                "--scenario",
                "mission/dag/scenarios/mission_dag_baseline.v1.json",
                "--mode",
                "dual",
                "--seed",
                "1",
                "--run-id",
                MISSION_DAG_RUN_ID,
                "--verify-deterministic",
            ),
        ),
        Step(
            "Validate mission DAG artifacts",
            (
                python,
                "scripts/ci/mission_dag_validate.py",
                "--strict",
                "--artifacts-dir",
                f"ops/reports/mission-dag-v1/{MISSION_DAG_RUN_ID}",
            ),
        ),
        Step(
            "Mission DAG coverage gate",
            (python, "scripts/ci/mission_dag_coverage.py", "--min", "90"),
        ),
        Step(
            "Build evidence status artifact (scratch)",
            (python, "scripts/build_evidence_status.py", "--output", scratch_evidence_status),
        ),
        Step(
            "Build research signals artifact",
            (python, "scripts/build_research_signals.py", "--no-require-tag"),
        ),
        Step(
            "Validate research signals contract",
            (python, "scripts/ci/validate_research_signals.py", "--strict", "--no-require-tag"),
        ),
        Step(
            "Enforce committed research signals",
            ("git", "diff", "--exit-code", "artifacts/research_signals.json"),
        ),
        Step("Audit claim chain", (python, "scripts/audit_claim_chain.py")),
        Step("Run unit tests", (python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")),
        Step(
            "Evidence validator coverage gate",
            (python, "scripts/ci/evidence_coverage.py", "--min", "95"),
        ),
    ]

    if remote_proof_dir:
        steps.append(
            Step(
                "Remote proof aggregate",
                (
                    python,
                    "scripts/ci/remote_proof_aggregate.py",
                    "--repo-root",
                    ".",
                    "--proof-dir",
                    remote_proof_dir,
                ),
            )
        )
    steps.extend(
        [
            Step(
                "Governance guardrails",
                (
                    python,
                    "scripts/ci/governance_check.py",
                    "--base",
                    base_sha,
                    "--head",
                    head_sha,
                    "--repo-root",
                    ".",
                ),
            ),
            Step(
                "Governance coverage gate",
                (python, "scripts/ci/governance_coverage.py", "--min", "95"),
            ),
        ]
    )
    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--base", help="Base commit SHA for diff-aware validators")
    parser.add_argument("--head", help="Head commit SHA for diff-aware validators")
    parser.add_argument("--remote-proof-dir", help="Optional remote proof directory override")
    parser.add_argument("--list-steps", action="store_true", help="Print the step plan and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    os.chdir(repo_root)

    base_sha = args.base or os.environ.get("BASE_SHA")
    head_sha = args.head or os.environ.get("HEAD_SHA")
    remote_proof_dir = args.remote_proof_dir or os.environ.get("REMOTE_PROOF_DIR")

    try:
        base_sha, head_sha = resolve_base_head(repo_root, base_sha, head_sha)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 2

    steps = build_steps(base_sha, head_sha, remote_proof_dir)
    if args.list_steps:
        print(f"Repository check suite ({len(steps)} steps)")
        print(f"- base_sha: {base_sha}")
        print(f"- head_sha: {head_sha}")
        for index, step in enumerate(steps, start=1):
            print(f"{index:02d}. {step.name}")
        return 0

    print("Running repository check suite")
    print(f"- repo_root: {repo_root}")
    print(f"- base_sha: {base_sha}")
    print(f"- head_sha: {head_sha}")
    print(f"- steps: {len(steps)}")

    for index, step in enumerate(steps, start=1):
        print(f"\n[{index:02d}/{len(steps)}] {step.name}")
        print("+ " + " ".join(shlex.quote(part) for part in step.command))
        proc = subprocess.run(step.command, cwd=repo_root, env=_env(), check=False)
        if proc.returncode != 0:
            print(f"FAIL: step '{step.name}' exited with status {proc.returncode}")
            return proc.returncode

    print("\nPASS: repository check suite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
