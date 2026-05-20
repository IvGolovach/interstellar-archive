from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
import unittest

from scripts.ci import check_suite


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _git(repo: Path, *args: str) -> str:
    proc = _run(["git", *args], cwd=repo)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stdout}\n{proc.stderr}")
    return proc.stdout.strip()


def _init_repo() -> Path:
    repo = Path(tempfile.mkdtemp())
    _git(repo, "init")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "README.md").write_text("# temp\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "init")
    return repo


class CheckSuiteTests(unittest.TestCase):
    def test_resolve_base_head_uses_explicit_overrides(self) -> None:
        repo = _init_repo()
        base, head = check_suite.resolve_base_head(repo, "base-sha", "head-sha")
        self.assertEqual(("base-sha", "head-sha"), (base, head))

    def test_resolve_base_head_falls_back_to_head_for_single_commit_repo(self) -> None:
        repo = _init_repo()
        base, head = check_suite.resolve_base_head(repo, None, None)
        self.assertEqual(head, base)

    def test_build_steps_wires_remote_proof_dir_override(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", "/tmp/proofs")
        remote_proof_step = next(step for step in steps if step.name == "Remote proof aggregate")
        self.assertIn("--proof-dir", remote_proof_step.command)
        self.assertIn("/tmp/proofs", remote_proof_step.command)

    def test_build_steps_skips_remote_proof_without_explicit_bundle(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        self.assertFalse(any(step.name == "Remote proof aggregate" for step in steps))

    def test_build_steps_passes_base_and_head_to_diff_aware_validators(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        evidence_step = next(step for step in steps if step.name == "Validate evidence contract")
        governance_step = next(step for step in steps if step.name == "Governance guardrails")
        self.assertIn("base-sha", evidence_step.command)
        self.assertIn("head-sha", evidence_step.command)
        self.assertIn("base-sha", governance_step.command)
        self.assertIn("head-sha", governance_step.command)

    def test_build_steps_include_browser_dataset_contract_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        browser_build_step = next(step for step in steps if step.name == "Build browser dataset artifact")
        browser_validate_step = next(step for step in steps if step.name == "Validate browser dataset artifact")
        browser_determinism_step = next(
            step for step in steps if step.name == "Validate browser-facing artifact determinism"
        )
        browser_diff_step = next(step for step in steps if step.name == "Enforce committed browser-facing artifacts")

        self.assertIn("scripts/build_browser_dataset_artifact.py", browser_build_step.command)
        self.assertIn("scripts/ci/browser_dataset_validate.py", browser_validate_step.command)
        self.assertIn("scripts/ci/artifact_determinism_validate.py", browser_determinism_step.command)
        self.assertIn("artifacts/mission_feasibility_screen.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/user_mission_run_catalog.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/runtime_scenario_generation.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/evidence_upgrade_campaign.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/optimization_v2_frontier.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/mission_dag_v2_boundary.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/cost_procurement_architecture_feasibility.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/external_validation_review_pack.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/public_narrative_hardening.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/roadmap_closure.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/browser_dataset.v1.json", browser_diff_step.command)

    def test_build_steps_include_mission_feasibility_screen_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        feasibility_build_step = next(step for step in steps if step.name == "Build mission feasibility screen artifact")
        feasibility_validate_step = next(
            step for step in steps if step.name == "Validate mission feasibility screen artifact"
        )
        feasibility_diff_step = next(
            step for step in steps if step.name == "Enforce committed mission feasibility screen artifact"
        )

        self.assertIn("scripts/build_mission_feasibility_screen_artifact.py", feasibility_build_step.command)
        self.assertIn("scripts/ci/mission_feasibility_screen_validate.py", feasibility_validate_step.command)
        self.assertIn("artifacts/mission_feasibility_screen.v1.json", feasibility_diff_step.command)

    def test_build_steps_include_user_mission_run_catalog_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        catalog_build_step = next(step for step in steps if step.name == "Build user mission run catalog artifact")
        catalog_validate_step = next(step for step in steps if step.name == "Validate user mission run catalog artifact")
        runtime_build_step = next(step for step in steps if step.name == "Build runtime scenario generation artifact")
        runtime_validate_step = next(step for step in steps if step.name == "Validate runtime scenario generation artifact")
        pack_validate_step = next(step for step in steps if step.name == "Validate default user mission run pack")
        catalog_diff_step = next(step for step in steps if step.name == "Enforce committed user mission run catalog artifact")
        runtime_diff_step = next(step for step in steps if step.name == "Enforce committed runtime scenario generation artifact")

        self.assertIn("scripts/build_user_mission_run_catalog_artifact.py", catalog_build_step.command)
        self.assertIn("scripts/ci/user_mission_run_catalog_validate.py", catalog_validate_step.command)
        self.assertIn("scripts/build_runtime_scenario_generation_artifact.py", runtime_build_step.command)
        self.assertIn("scripts/ci/runtime_scenario_generation_validate.py", runtime_validate_step.command)
        self.assertIn("scripts/ci/user_mission_run_pack_validate.py", pack_validate_step.command)
        self.assertIn("--strict", pack_validate_step.command)
        self.assertIn("artifacts/user_mission_run_catalog.v1.json", catalog_diff_step.command)
        self.assertIn("artifacts/runtime_scenario_generation.v1.json", runtime_diff_step.command)

    def test_build_steps_include_mission_probability_coupling_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        coupling_build_step = next(step for step in steps if step.name == "Build mission probability coupling artifact")
        coupling_validate_step = next(
            step for step in steps if step.name == "Validate mission probability coupling artifact"
        )
        coupling_diff_step = next(
            step for step in steps if step.name == "Enforce committed mission probability coupling artifact"
        )
        browser_diff_step = next(step for step in steps if step.name == "Enforce committed browser-facing artifacts")

        self.assertIn("scripts/build_mission_probability_coupling_artifact.py", coupling_build_step.command)
        self.assertIn("scripts/ci/mission_probability_coupling_validate.py", coupling_validate_step.command)
        self.assertIn("artifacts/mission_probability_coupling.v1.json", coupling_diff_step.command)
        self.assertIn("artifacts/mission_probability_coupling.v1.json", browser_diff_step.command)

    def test_build_steps_include_uncertainty_interactions_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        build_step = next(step for step in steps if step.name == "Build uncertainty interactions artifact")
        validate_step = next(step for step in steps if step.name == "Validate uncertainty interactions artifact")
        diff_step = next(step for step in steps if step.name == "Enforce committed uncertainty interactions artifact")
        browser_diff_step = next(step for step in steps if step.name == "Enforce committed browser-facing artifacts")

        self.assertIn("scripts/build_uncertainty_interactions_artifact.py", build_step.command)
        self.assertIn("scripts/ci/uncertainty_interactions_validate.py", validate_step.command)
        self.assertIn("artifacts/uncertainty_interactions.v1.json", diff_step.command)
        self.assertIn("artifacts/uncertainty_interactions.v1.json", browser_diff_step.command)

    def test_build_steps_include_evidence_upgrade_campaign_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        build_step = next(step for step in steps if step.name == "Build evidence upgrade campaign artifact")
        validate_step = next(step for step in steps if step.name == "Validate evidence upgrade campaign artifact")
        diff_step = next(step for step in steps if step.name == "Enforce committed evidence upgrade campaign artifact")
        browser_diff_step = next(step for step in steps if step.name == "Enforce committed browser-facing artifacts")

        self.assertIn("scripts/build_evidence_upgrade_campaign_artifact.py", build_step.command)
        self.assertIn("scripts/ci/evidence_upgrade_campaign_validate.py", validate_step.command)
        self.assertIn("artifacts/evidence_upgrade_campaign.v1.json", diff_step.command)
        self.assertIn("artifacts/evidence_upgrade_campaign.v1.json", browser_diff_step.command)

    def test_build_steps_include_optimization_v2_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        build_step = next(step for step in steps if step.name == "Build optimization v2 artifact")
        validate_step = next(step for step in steps if step.name == "Validate optimization v2 artifact")
        diff_step = next(step for step in steps if step.name == "Enforce committed optimization v2 artifact")
        browser_diff_step = next(step for step in steps if step.name == "Enforce committed browser-facing artifacts")

        self.assertIn("scripts/build_optimization_v2_artifact.py", build_step.command)
        self.assertIn("scripts/ci/optimization_v2_validate.py", validate_step.command)
        self.assertIn("artifacts/optimization_v2_frontier.v1.json", diff_step.command)
        self.assertIn("artifacts/optimization_v2_frontier.v1.json", browser_diff_step.command)

    def test_build_steps_include_mission_dag_v2_boundary_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        build_step = next(step for step in steps if step.name == "Build mission DAG v2 boundary artifact")
        validate_step = next(step for step in steps if step.name == "Validate mission DAG v2 boundary artifact")
        diff_step = next(step for step in steps if step.name == "Enforce committed mission DAG v2 boundary artifact")
        browser_diff_step = next(step for step in steps if step.name == "Enforce committed browser-facing artifacts")

        self.assertIn("scripts/build_mission_dag_v2_boundary_artifact.py", build_step.command)
        self.assertIn("scripts/ci/mission_dag_v2_boundary_validate.py", validate_step.command)
        self.assertIn("artifacts/mission_dag_v2_boundary.v1.json", diff_step.command)
        self.assertIn("artifacts/mission_dag_v2_boundary.v1.json", browser_diff_step.command)

    def test_build_steps_include_cost_procurement_architecture_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        build_step = next(step for step in steps if step.name == "Build cost/procurement/architecture feasibility artifact")
        validate_step = next(
            step for step in steps if step.name == "Validate cost/procurement/architecture feasibility artifact"
        )
        diff_step = next(
            step for step in steps if step.name == "Enforce committed cost/procurement/architecture feasibility artifact"
        )
        browser_diff_step = next(step for step in steps if step.name == "Enforce committed browser-facing artifacts")

        self.assertIn("scripts/build_cost_procurement_architecture_feasibility_artifact.py", build_step.command)
        self.assertIn("scripts/ci/cost_procurement_architecture_feasibility_validate.py", validate_step.command)
        self.assertIn("artifacts/cost_procurement_architecture_feasibility.v1.json", diff_step.command)
        self.assertIn("artifacts/cost_procurement_architecture_feasibility.v1.json", browser_diff_step.command)

    def test_build_steps_include_external_validation_review_pack_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        build_step = next(step for step in steps if step.name == "Build external validation review pack artifact")
        validate_step = next(step for step in steps if step.name == "Validate external validation review pack artifact")
        diff_step = next(
            step for step in steps if step.name == "Enforce committed external validation review pack artifact"
        )
        browser_diff_step = next(step for step in steps if step.name == "Enforce committed browser-facing artifacts")

        self.assertIn("scripts/build_external_validation_review_pack_artifact.py", build_step.command)
        self.assertIn("scripts/ci/external_validation_review_pack_validate.py", validate_step.command)
        self.assertIn("artifacts/external_validation_review_pack.v1.json", diff_step.command)
        self.assertIn("artifacts/external_validation_review_pack.v1.json", browser_diff_step.command)

    def test_build_steps_include_public_narrative_hardening_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        build_step = next(step for step in steps if step.name == "Build public narrative hardening artifact")
        validate_step = next(step for step in steps if step.name == "Validate public narrative hardening artifact")
        diff_step = next(step for step in steps if step.name == "Enforce committed public narrative hardening artifact")
        browser_diff_step = next(step for step in steps if step.name == "Enforce committed browser-facing artifacts")

        self.assertIn("scripts/build_public_narrative_hardening_artifact.py", build_step.command)
        self.assertIn("scripts/ci/public_narrative_hardening_validate.py", validate_step.command)
        self.assertIn("artifacts/public_narrative_hardening.v1.json", diff_step.command)
        self.assertIn("artifacts/public_narrative_hardening.v1.json", browser_diff_step.command)

    def test_build_steps_include_external_proof_phase_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        expected = {
            "Build external validation execution ledger artifact": "scripts/build_external_validation_execution_ledger_artifact.py",
            "Validate external validation execution ledger artifact": "scripts/ci/external_validation_execution_ledger_validate.py",
            "Enforce committed external validation execution ledger artifact": "artifacts/external_validation_execution_ledger.v1.json",
            "Build independent physics backend comparison artifact": "scripts/build_independent_physics_backend_comparison_artifact.py",
            "Validate independent physics backend comparison artifact": "scripts/ci/independent_physics_backend_comparison_validate.py",
            "Enforce committed independent physics backend comparison artifact": "artifacts/independent_physics_backend_comparison.v1.json",
            "Build capsule qualification evidence pack artifact": "scripts/build_capsule_qualification_evidence_pack_artifact.py",
            "Validate capsule qualification evidence pack artifact": "scripts/ci/capsule_qualification_evidence_pack_validate.py",
            "Enforce committed capsule qualification evidence pack artifact": "artifacts/capsule_qualification_evidence_pack.v1.json",
            "Build evidence upgrade closure artifact": "scripts/build_evidence_upgrade_closure_artifact.py",
            "Validate evidence upgrade closure artifact": "scripts/ci/evidence_upgrade_closure_validate.py",
            "Enforce committed evidence upgrade closure artifact": "artifacts/evidence_upgrade_closure.v1.json",
            "Build external reproduction kit artifact": "scripts/build_external_reproduction_kit_artifact.py",
            "Validate external reproduction kit artifact": "scripts/ci/external_reproduction_kit_validate.py",
            "Enforce committed external reproduction kit artifact": "artifacts/external_reproduction_kit.v1.json",
            "Build external evidence intake artifact": "scripts/build_external_evidence_intake_artifact.py",
            "Validate external evidence intake artifact": "scripts/ci/external_evidence_intake_validate.py",
            "Enforce committed external evidence intake artifact": "artifacts/external_evidence_intake.v1.json",
            "Build external validation campaign artifact": "scripts/build_external_validation_campaign_artifact.py",
            "Validate external validation campaign artifact": "scripts/ci/external_validation_campaign_validate.py",
            "Enforce committed external validation campaign artifact": "artifacts/external_validation_campaign.v1.json",
            "Export external reproduction pack": "scripts/export_external_reproduction_pack.py",
            "Validate exported external reproduction pack": "scripts/ci/external_reproduction_pack_validate.py",
            "Build release candidate readiness artifact": "scripts/build_release_candidate_readiness_artifact.py",
            "Validate release candidate readiness artifact": "scripts/ci/release_candidate_readiness_validate.py",
            "Enforce committed release candidate readiness artifact": "artifacts/release_candidate_readiness.v1.json",
        }
        for step_name, expected_command_part in expected.items():
            with self.subTest(step_name=step_name):
                step = next(item for item in steps if item.name == step_name)
                self.assertIn(expected_command_part, step.command)

        browser_diff_step = next(step for step in steps if step.name == "Enforce committed browser-facing artifacts")
        self.assertIn("artifacts/external_validation_execution_ledger.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/independent_physics_backend_comparison.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/capsule_qualification_evidence_pack.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/evidence_upgrade_closure.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/external_reproduction_kit.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/external_evidence_intake.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/external_validation_campaign.v1.json", browser_diff_step.command)
        self.assertIn("artifacts/release_candidate_readiness.v1.json", browser_diff_step.command)

    def test_build_steps_include_roadmap_closure_artifact_checks(self) -> None:
        steps = check_suite.build_steps("base-sha", "head-sha", None)
        roadmap_build_step = next(step for step in steps if step.name == "Build roadmap closure artifact")
        roadmap_validate_step = next(step for step in steps if step.name == "Validate roadmap closure artifact")
        roadmap_diff_step = next(step for step in steps if step.name == "Enforce committed roadmap closure artifact")

        self.assertIn("scripts/build_roadmap_closure_artifact.py", roadmap_build_step.command)
        self.assertIn("scripts/ci/roadmap_closure_validate.py", roadmap_validate_step.command)
        self.assertIn("artifacts/roadmap_closure.v1.json", roadmap_diff_step.command)


if __name__ == "__main__":
    unittest.main()
