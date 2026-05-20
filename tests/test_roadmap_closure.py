from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from mission.roadmap import build_roadmap_closure, validate_roadmap_closure


class RoadmapClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]

    def test_builds_all_15_repo_native_closure_items(self) -> None:
        payload = build_roadmap_closure(self.repo_root)
        errors = validate_roadmap_closure(payload)

        self.assertEqual([], errors)
        self.assertEqual(15, payload["roadmap_item_count"])
        self.assertEqual(
            [f"roadmap-{index:02d}" for index in range(1, 16)],
            [item["id"] for item in payload["roadmap_items"]],
        )
        self.assertEqual(15, payload["closure_metrics"]["repo_native_closure_count"])
        self.assertTrue(
            all(
                item["status"] == "repo_native_closure_implemented_external_evidence_open"
                for item in payload["roadmap_items"]
            )
        )
        self.assertTrue(all(item["acceptance_criteria"] for item in payload["roadmap_items"]))
        self.assertTrue(all("certified" in item["false_claims_blocked"] for item in payload["roadmap_items"]))
        self.assertGreaterEqual(payload["closure_metrics"]["external_evidence_gap_count"], 15)
        self.assertTrue(all(item["non_certification_notice"] for item in payload["roadmap_items"]))
        roadmap_09 = next(item for item in payload["roadmap_items"] if item["id"] == "roadmap-09")
        self.assertEqual("tracked_evidence_upgrade_campaign", roadmap_09["implementation_mode"])
        self.assertIn("artifacts/evidence_upgrade_campaign.v1.json", roadmap_09["artifacts"])
        self.assertEqual("evidence_upgrade", roadmap_09["model_summary_ref"])
        roadmap_10 = next(item for item in payload["roadmap_items"] if item["id"] == "roadmap-10")
        self.assertEqual("tracked_four_axis_decision_surface", roadmap_10["implementation_mode"])
        self.assertIn("artifacts/optimization_v2_frontier.v1.json", roadmap_10["artifacts"])
        self.assertIn("scripts/ci/optimization_v2_validate.py", roadmap_10["validators"])
        roadmap_12 = next(item for item in payload["roadmap_items"] if item["id"] == "roadmap-12")
        self.assertEqual("tracked_runtime_generation_contract", roadmap_12["implementation_mode"])
        self.assertIn("artifacts/runtime_scenario_generation.v1.json", roadmap_12["artifacts"])
        self.assertIn("scripts/ci/runtime_scenario_generation_validate.py", roadmap_12["validators"])
        self.assertIn("scripts/ci/user_mission_run_pack_validate.py", roadmap_12["validators"])
        roadmap_14 = next(item for item in payload["roadmap_items"] if item["id"] == "roadmap-14")
        self.assertEqual("tracked_external_validation_review_pack", roadmap_14["implementation_mode"])
        self.assertIn("artifacts/external_validation_review_pack.v1.json", roadmap_14["artifacts"])
        self.assertIn("scripts/ci/external_validation_review_pack_validate.py", roadmap_14["validators"])
        roadmap_15 = next(item for item in payload["roadmap_items"] if item["id"] == "roadmap-15")
        self.assertEqual("tracked_public_narrative_hardening", roadmap_15["implementation_mode"])
        self.assertIn("artifacts/public_narrative_hardening.v1.json", roadmap_15["artifacts"])
        self.assertIn("scripts/ci/public_narrative_hardening_validate.py", roadmap_15["validators"])

    def test_evidence_upgrade_summary_is_artifact_backed(self) -> None:
        payload = build_roadmap_closure(self.repo_root)
        evidence_upgrade = payload["evidence_upgrade"]

        self.assertEqual("artifacts/evidence_upgrade_campaign.v1.json", evidence_upgrade["artifact_ref"])
        self.assertEqual("evidence_upgrade_campaign.v1", evidence_upgrade["schema_version"])
        self.assertEqual("implemented_as_tracked_campaign_ledger", evidence_upgrade["status"])
        self.assertEqual(66, evidence_upgrade["claim_count"])
        self.assertEqual(31, evidence_upgrade["public_campaign_count"])
        self.assertEqual(35, evidence_upgrade["internal_audit_count"])
        self.assertEqual({"B": 8, "C": 56, "D": 2}, evidence_upgrade["trust_grade_distribution"])
        self.assertEqual({"B": 8, "C": 21, "D": 2}, evidence_upgrade["public_trust_distribution"])
        self.assertEqual(15, evidence_upgrade["top_priority_count"])
        self.assertIn("trust grades upgraded automatically", evidence_upgrade["blocked_claims"])

    def test_optimization_v2_summary_is_artifact_backed(self) -> None:
        payload = build_roadmap_closure(self.repo_root)
        optimization = payload["model_summaries"]["optimization_v2"]

        self.assertEqual("artifacts/optimization_v2_frontier.v1.json", optimization["artifact_ref"])
        self.assertEqual("optimization_v2_frontier.v1", optimization["schema_version"])
        self.assertEqual("implemented_as_four_axis_decision_surface", optimization["status"])
        self.assertEqual(20, optimization["candidate_count"])
        self.assertGreaterEqual(optimization["frontier_candidate_count"], 1)
        self.assertEqual(["p_success", "risk_envelope", "qualification_gap", "cost_proxy"], optimization["active_axes"])
        self.assertFalse(optimization["global_optimum_claimed"])
        self.assertFalse(optimization["calibrated_cost_model_available"])
        self.assertFalse(optimization["qualification_complete"])
        self.assertIn("procurement-grade cost estimate", optimization["blocked_claims"])
        self.assertIn("flight-ready design selected", optimization["blocked_claims"])

    def test_dag_v2_summary_is_artifact_backed(self) -> None:
        payload = build_roadmap_closure(self.repo_root)
        dag_v2 = payload["dag_v2"]

        self.assertEqual("artifacts/mission_dag_v2_boundary.v1.json", dag_v2["artifact_ref"])
        self.assertEqual("mission_dag_v2_boundary.v1", dag_v2["schema_version"])
        self.assertEqual("implemented_as_tracked_module_boundary_artifact", dag_v2["status"])
        self.assertEqual(6, dag_v2["module_count"])
        self.assertEqual(6, dag_v2["failure_taxonomy_mapping_module_count"])
        self.assertTrue(dag_v2["state_trace_contract_complete"])
        self.assertFalse(dag_v2["independent_backend_complete"])
        self.assertFalse(dag_v2["high_fidelity_state_traces_available"])
        self.assertIn("independent physics backend validated", dag_v2["blocked_claims"])

    def test_runtime_runs_summary_is_artifact_backed(self) -> None:
        payload = build_roadmap_closure(self.repo_root)
        runtime = payload["runtime_runs"]

        self.assertEqual("artifacts/runtime_scenario_generation.v1.json", runtime["artifact_ref"])
        self.assertEqual("runtime_scenario_generation.v1", runtime["schema_version"])
        self.assertEqual("implemented_as_tracked_runtime_generation_contract_and_strict_local_pack_validator", runtime["status"])
        self.assertEqual(15, runtime["run_count"])
        self.assertEqual(15, runtime["generation_row_count"])
        self.assertEqual("scripts/ci/user_mission_run_pack_validate.py", runtime["pack_validator"])
        self.assertFalse(runtime["run_store_tracked_by_default"])
        self.assertFalse(runtime["writes_tracked_files"])
        self.assertFalse(runtime["remote_execution_claimed"])
        self.assertFalse(runtime["persistent_reviewed_archive_claimed"])
        self.assertIn("USER_RUN_SUMMARY.json", runtime["pack_output_files"])
        self.assertIn("persistent reviewed run archive", runtime["blocked_runtime_claims"])

    def test_review_pack_summary_is_artifact_backed(self) -> None:
        payload = build_roadmap_closure(self.repo_root)
        review_pack = payload["review_pack"]

        self.assertEqual("artifacts/external_validation_review_pack.v1.json", review_pack["artifact_ref"])
        self.assertEqual("external_validation_review_pack.v1", review_pack["schema_version"])
        self.assertEqual("implemented_as_tracked_external_validation_review_pack", review_pack["status"])
        self.assertEqual("repo_native_review_pack_ready_external_review_not_completed", review_pack["review_pack_status"])
        self.assertEqual(7, review_pack["review_case_count"])
        self.assertEqual(6, review_pack["external_deliverable_count"])
        self.assertFalse(review_pack["third_party_review_completed"])
        self.assertFalse(review_pack["independent_reproduction_completed"])
        self.assertFalse(review_pack["independent_benchmark_completed"])
        self.assertFalse(review_pack["high_fidelity_state_trace_complete"])
        self.assertFalse(review_pack["external_red_team_completed"])
        self.assertFalse(review_pack["external_validation_claimed"])
        self.assertTrue(review_pack["all_cases_require_external_review"])
        self.assertIn("optimistic-prior-collapse", review_pack["review_case_ids"])
        self.assertIn("external_red_team_report", review_pack["required_deliverable_ids"])
        self.assertIn("third-party validated", review_pack["blocked_claims"])

    def test_public_narrative_summary_is_artifact_backed(self) -> None:
        payload = build_roadmap_closure(self.repo_root)
        narrative = payload["public_narrative"]

        self.assertEqual("artifacts/public_narrative_hardening.v1.json", narrative["artifact_ref"])
        self.assertEqual("public_narrative_hardening.v1", narrative["schema_version"])
        self.assertEqual("implemented_as_tracked_public_narrative_hardening", narrative["status"])
        self.assertEqual(10, narrative["claim_rule_count"])
        self.assertGreaterEqual(narrative["public_surface_count"], 8)
        self.assertEqual(0, narrative["unsafe_public_overclaim_count"])
        self.assertFalse(narrative["external_wording_audit_completed"])
        self.assertFalse(narrative["audience_testing_completed"])
        self.assertFalse(narrative["legal_review_completed"])
        self.assertFalse(narrative["public_claim_approval_completed"])
        self.assertTrue(narrative["all_required_concepts_present"])
        self.assertIn("certified", narrative["forbidden_claims"])
        self.assertIn("external validation completed", narrative["forbidden_claims"])
        self.assertIn("procurement-grade cost estimate", narrative["forbidden_claims"])
        self.assertIn("non-certifying", narrative["required_claims"])
        self.assertTrue(narrative["browser_boundary"]["artifact_only_rendering"])
        self.assertFalse(narrative["browser_boundary"]["client_side_claim_recomputation_allowed"])

    def test_committed_artifact_matches_builder_output(self) -> None:
        committed = json.loads((self.repo_root / "artifacts/roadmap_closure.v1.json").read_text(encoding="utf-8"))
        built = build_roadmap_closure(self.repo_root)

        self.assertEqual(committed, built)

    def test_validator_rejects_missing_item(self) -> None:
        payload = build_roadmap_closure(self.repo_root)
        payload["roadmap_items"] = payload["roadmap_items"][:-1]

        errors = validate_roadmap_closure(payload)

        self.assertTrue(any("roadmap_item_count" in error or "roadmap item ids" in error for error in errors))

    def test_validator_rejects_certification_notice_drift(self) -> None:
        payload = build_roadmap_closure(self.repo_root)
        payload["roadmap_items"][0]["non_certification_notice"] = False

        errors = validate_roadmap_closure(payload)

        self.assertTrue(any("non_certification_notice" in error for error in errors))

    def test_cli_builder_writes_valid_json(self) -> None:
        from scripts import build_roadmap_closure_artifact

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "roadmap_closure.v1.json"
            payload = build_roadmap_closure(self.repo_root)
            build_roadmap_closure_artifact._write_json(output, payload)
            written = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual([], validate_roadmap_closure(written))


if __name__ == "__main__":
    unittest.main()
