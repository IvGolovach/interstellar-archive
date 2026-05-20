from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from scripts import build_browser_dataset_artifact


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class BrowserDatasetValidateTests(unittest.TestCase):
    def test_repo_browser_dataset_validates(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertEqual([], errors)
        self.assertTrue(
            all(
                not str(item.get("parameter_id", "")).startswith("code_literal.")
                for item in payload["manifest"]["parameters"]
            )
        )
        self.assertTrue(
            all(not str(parameter_id).startswith("code_literal.") for parameter_id in payload["static_usage_graph"])
        )
        self.assertTrue(
            all(not str(parameter_id).startswith("code_literal.") for parameter_id in payload["evidence_index"])
        )
        self.assertTrue(
            all(
                not str(item.get("parameter_id", "")).startswith("code_literal.")
                for item in payload["optimization_search_space"]["parameters_considered"]
            )
        )
        self.assertTrue(
            all(
                not str(item.get("parameter_id", "")).startswith("code_literal.")
                for item in payload["optimization_search_space"]["excluded_parameters"]
            )
        )
        self.assertGreater(payload["optimization_search_space"]["excluded_internal_parameter_count"], 0)
        self.assertIn(
            "code_literal.",
            payload["optimization_search_space"]["internal_parameter_prefixes_excluded"],
        )
        self.assertEqual(
            "artifacts/capsule_risk_budget.v1.json",
            payload["source_paths"]["capsuleRiskBudget"],
        )
        self.assertEqual("capsule_risk_budget.v1", payload["capsule_risk_budget"]["schema_version"])
        self.assertTrue(payload["capsule_risk_budget"]["non_certification_notice"])
        self.assertIn("source_policy", payload["capsule_risk_budget"])
        self.assertGreaterEqual(len(payload["capsule_risk_budget"]["failure_modes"]), 8)
        self.assertGreaterEqual(len(payload["capsule_risk_budget"]["qualification_roadmap"]), 5)
        self.assertEqual(
            "artifacts/mission_feasibility_screen.v1.json",
            payload["source_paths"]["missionFeasibilityScreen"],
        )
        self.assertEqual("mission_feasibility_screen.v1", payload["mission_feasibility_screen"]["schema_version"])
        self.assertEqual(15, payload["mission_feasibility_screen"]["scenario_count"])
        self.assertEqual(15, payload["mission_feasibility_screen"]["capsule_risk_budget_match_count"])
        self.assertEqual(
            "artifacts/user_mission_run_catalog.v1.json",
            payload["source_paths"]["userMissionRunCatalog"],
        )
        self.assertEqual("user_mission_run_catalog.v1", payload["user_mission_run_catalog"]["schema_version"])
        self.assertEqual(15, payload["user_mission_run_catalog"]["run_count"])
        self.assertTrue(payload["user_mission_run_catalog"]["default_run_id"].startswith("umr-reference-black-hole-conditional-45-"))
        self.assertEqual(
            "artifacts/runtime_scenario_generation.v1.json",
            payload["source_paths"]["runtimeScenarioGeneration"],
        )
        self.assertEqual("runtime_scenario_generation.v1", payload["runtime_scenario_generation"]["schema_version"])
        self.assertEqual(15, payload["runtime_scenario_generation"]["generation_row_count"])
        self.assertEqual(0, payload["runtime_scenario_generation"]["rollup"]["rows_writing_tracked_files"])
        self.assertFalse(payload["runtime_scenario_generation"]["rollup"]["remote_execution_claimed"])
        self.assertFalse(payload["runtime_scenario_generation"]["rollup"]["persistent_reviewed_archive_claimed"])
        self.assertIn("persistent reviewed run archive", payload["runtime_scenario_generation"]["blocked_claims"])
        self.assertTrue(
            all(
                "--verify-deterministic" in row["command_preview"]
                for row in payload["runtime_scenario_generation"]["generation_rows"]
            )
        )
        self.assertEqual(
            "artifacts/cost_procurement_architecture_feasibility.v1.json",
            payload["source_paths"]["costProcurementArchitectureFeasibility"],
        )
        self.assertEqual(
            "cost_procurement_architecture_feasibility.v1",
            payload["cost_procurement_architecture_feasibility"]["schema_version"],
        )
        self.assertEqual(15, payload["cost_procurement_architecture_feasibility"]["architecture_row_count"])
        self.assertFalse(
            payload["cost_procurement_architecture_feasibility"]["rollup"]["procurement_grade_estimate_available"]
        )
        self.assertEqual(0, payload["cost_procurement_architecture_feasibility"]["rollup"]["vendor_quote_count"])
        self.assertFalse(payload["cost_procurement_architecture_feasibility"]["rollup"]["launch_vehicle_selected"])
        self.assertFalse(
            payload["cost_procurement_architecture_feasibility"]["rollup"]["architecture_selected_for_flight"]
        )
        self.assertFalse(
            payload["cost_procurement_architecture_feasibility"]["rollup"]["calibrated_cost_model_available"]
        )
        self.assertIn(
            "procurement-grade cost estimate",
            payload["cost_procurement_architecture_feasibility"]["blocked_claims"],
        )
        self.assertTrue(
            all(
                row["procurement_status"] == "external_required"
                for row in payload["cost_procurement_architecture_feasibility"]["architecture_rows"]
            )
        )
        self.assertEqual(
            "artifacts/external_validation_review_pack.v1.json",
            payload["source_paths"]["externalValidationReviewPack"],
        )
        self.assertEqual(
            "external_validation_review_pack.v1",
            payload["external_validation_review_pack"]["schema_version"],
        )
        self.assertEqual(7, payload["external_validation_review_pack"]["review_case_count"])
        self.assertEqual(
            "repo_native_review_pack_ready_external_review_not_completed",
            payload["external_validation_review_pack"]["review_pack_status"],
        )
        self.assertFalse(payload["external_validation_review_pack"]["rollup"]["third_party_review_completed"])
        self.assertFalse(payload["external_validation_review_pack"]["rollup"]["independent_reproduction_completed"])
        self.assertFalse(payload["external_validation_review_pack"]["rollup"]["independent_benchmark_completed"])
        self.assertFalse(payload["external_validation_review_pack"]["rollup"]["high_fidelity_state_trace_complete"])
        self.assertFalse(payload["external_validation_review_pack"]["rollup"]["external_red_team_completed"])
        self.assertFalse(payload["external_validation_review_pack"]["rollup"]["external_validation_claimed"])
        self.assertIn("third-party validated", payload["external_validation_review_pack"]["blocked_claims"])
        self.assertEqual(
            "artifacts/public_narrative_hardening.v1.json",
            payload["source_paths"]["publicNarrativeHardening"],
        )
        self.assertEqual(
            "public_narrative_hardening.v1",
            payload["public_narrative_hardening"]["schema_version"],
        )
        self.assertEqual(10, payload["public_narrative_hardening"]["claim_rule_count"])
        self.assertGreaterEqual(payload["public_narrative_hardening"]["public_surface_count"], 8)
        self.assertEqual(0, payload["public_narrative_hardening"]["rollup"]["unsafe_public_overclaim_count"])
        self.assertFalse(payload["public_narrative_hardening"]["rollup"]["external_wording_audit_completed"])
        self.assertFalse(payload["public_narrative_hardening"]["rollup"]["audience_testing_completed"])
        self.assertIn("certified", payload["public_narrative_hardening"]["forbidden_public_claims"])
        self.assertIn(
            "external validation completed",
            payload["public_narrative_hardening"]["forbidden_public_claims"],
        )
        self.assertIn("non-certifying", payload["public_narrative_hardening"]["required_public_concepts"])
        self.assertTrue(payload["public_narrative_hardening"]["browser_boundary"]["artifact_only_rendering"])
        self.assertFalse(
            payload["public_narrative_hardening"]["browser_boundary"][
                "client_side_claim_recomputation_allowed"
            ]
        )
        self.assertEqual(
            "artifacts/mission_probability_coupling.v1.json",
            payload["source_paths"]["missionProbabilityCoupling"],
        )
        self.assertEqual("mission_probability_coupling.v1", payload["mission_probability_coupling"]["schema_version"])
        self.assertEqual(15, payload["mission_probability_coupling"]["coupling_count"])
        self.assertTrue(
            payload["mission_probability_coupling"]["default_coupling_id"].startswith(
                "mpc-reference-black-hole-conditional-45-"
            )
        )
        self.assertEqual(0, payload["mission_probability_coupling"]["rollup"]["rows_with_full_mission_probability_closed"])
        self.assertEqual(
            "artifacts/uncertainty_interactions.v1.json",
            payload["source_paths"]["uncertaintyInteractions"],
        )
        self.assertEqual("uncertainty_interactions.v1", payload["uncertainty_interactions"]["schema_version"])
        self.assertEqual(4, payload["uncertainty_interactions"]["uncertainty_entry_count"])
        self.assertEqual(6, payload["uncertainty_interactions"]["interaction_pair_count"])
        self.assertEqual(0, payload["uncertainty_interactions"]["rollup"]["validated_correlation_count"])
        self.assertEqual(
            "artifacts/optimization_v2_frontier.v1.json",
            payload["source_paths"]["optimizationV2"],
        )
        self.assertEqual("optimization_v2_frontier.v1", payload["optimization_v2"]["schema_version"])
        self.assertEqual(20, payload["optimization_v2"]["candidate_count"])
        self.assertEqual(["p_success", "risk_envelope", "qualification_gap", "cost_proxy"], payload["optimization_v2"]["rollup"]["axis_ids"])
        self.assertFalse(payload["optimization_v2"]["rollup"]["global_optimum_claimed"])
        self.assertFalse(payload["optimization_v2"]["rollup"]["calibrated_cost_model_available"])
        self.assertIn("procurement-grade cost estimate", payload["optimization_v2"]["blocked_claims"])
        self.assertIn("flight-ready design selected", payload["optimization_v2"]["blocked_claims"])
        self.assertTrue(
            all(
                not parameter_id.startswith("code_literal.")
                for candidate in payload["optimization_v2"]["candidates"]
                for parameter_id in candidate["dominant_drivers"]["parameter_ids"]
            )
        )
        self.assertEqual(
            "artifacts/evidence_upgrade_campaign.v1.json",
            payload["source_paths"]["evidenceUpgradeCampaign"],
        )
        self.assertEqual("evidence_upgrade_campaign.v1", payload["evidence_upgrade_campaign"]["schema_version"])
        self.assertEqual(66, payload["evidence_upgrade_campaign"]["claim_count"])
        self.assertEqual(31, payload["evidence_upgrade_campaign"]["public_campaign_count"])
        self.assertEqual(35, payload["evidence_upgrade_campaign"]["internal_audit_count"])
        self.assertTrue(payload["evidence_upgrade_campaign"]["public_top_priorities"])
        self.assertTrue(
            all(
                not str(item.get("parameter_id", "")).startswith("code_literal.")
                for item in payload["evidence_upgrade_campaign"]["public_top_priorities"]
            )
        )
        self.assertIn("trust grades upgraded automatically", payload["evidence_upgrade_campaign"]["blocked_claims"])
        self.assertEqual(
            "artifacts/mission_dag_v2_boundary.v1.json",
            payload["source_paths"]["missionDagV2Boundary"],
        )
        self.assertEqual("mission_dag_v2_boundary.v1", payload["mission_dag_v2_boundary"]["schema_version"])
        self.assertEqual(6, payload["mission_dag_v2_boundary"]["module_count"])
        self.assertFalse(payload["mission_dag_v2_boundary"]["rollup"]["independent_backend_complete"])
        self.assertTrue(payload["mission_dag_v2_boundary"]["rollup"]["state_trace_contract_complete"])
        self.assertIn("independent physics backend validated", payload["mission_dag_v2_boundary"]["blocked_claims"])
        self.assertEqual(
            "artifacts/roadmap_closure.v1.json",
            payload["source_paths"]["roadmapClosure"],
        )
        self.assertEqual("roadmap_closure.v1", payload["roadmap_closure"]["schema_version"])
        self.assertTrue(payload["roadmap_closure"]["non_certification_notice"])
        self.assertEqual(15, payload["roadmap_closure"]["roadmap_item_count"])
        self.assertEqual(15, payload["roadmap_closure"]["closure_metrics"]["repo_native_closure_count"])
        self.assertEqual(
            "artifacts/external_validation_execution_ledger.v1.json",
            payload["source_paths"]["externalValidationExecutionLedger"],
        )
        self.assertEqual(
            "external_validation_execution_ledger.v1",
            payload["external_validation_execution_ledger"]["schema_version"],
        )
        self.assertEqual(0, payload["external_validation_execution_ledger"]["execution_record_count"])
        self.assertFalse(
            payload["external_validation_execution_ledger"]["rollup"]["external_validation_completed"]
        )
        self.assertEqual(
            "artifacts/independent_physics_backend_comparison.v1.json",
            payload["source_paths"]["independentPhysicsBackendComparison"],
        )
        self.assertEqual(
            "independent_physics_backend_comparison.v1",
            payload["independent_physics_backend_comparison"]["schema_version"],
        )
        self.assertGreaterEqual(payload["independent_physics_backend_comparison"]["analytic_check_count"], 4)
        self.assertFalse(
            payload["independent_physics_backend_comparison"]["rollup"]["independent_external_backend_complete"]
        )
        self.assertEqual(
            "artifacts/capsule_qualification_evidence_pack.v1.json",
            payload["source_paths"]["capsuleQualificationEvidencePack"],
        )
        self.assertEqual(
            "capsule_qualification_evidence_pack.v1",
            payload["capsule_qualification_evidence_pack"]["schema_version"],
        )
        self.assertEqual(206.0, payload["capsule_qualification_evidence_pack"]["mass_closure"]["configured_capsule_mass_kg"])
        self.assertEqual(0, payload["capsule_qualification_evidence_pack"]["lab_record_count"])
        self.assertFalse(payload["capsule_qualification_evidence_pack"]["rollup"]["qualification_complete"])
        self.assertEqual(
            "artifacts/evidence_upgrade_closure.v1.json",
            payload["source_paths"]["evidenceUpgradeClosure"],
        )
        self.assertEqual("evidence_upgrade_closure.v1", payload["evidence_upgrade_closure"]["schema_version"])
        self.assertEqual(15, payload["evidence_upgrade_closure"]["closure_cycle_count"])
        self.assertEqual(0, payload["evidence_upgrade_closure"]["rollup"]["trust_grade_promotion_count"])
        self.assertEqual(
            "artifacts/external_reproduction_kit.v1.json",
            payload["source_paths"]["externalReproductionKit"],
        )
        self.assertEqual("external_reproduction_kit.v1", payload["external_reproduction_kit"]["schema_version"])
        self.assertEqual(7, payload["external_reproduction_kit"]["review_case_count"])
        self.assertTrue(payload["external_reproduction_kit"]["rollup"]["export_cli_available"])
        self.assertFalse(payload["external_reproduction_kit"]["rollup"]["external_execution_completed"])
        self.assertFalse(payload["external_reproduction_kit"]["rollup"]["first_real_external_record_present"])
        self.assertEqual(
            "artifacts/external_evidence_intake.v1.json",
            payload["source_paths"]["externalEvidenceIntake"],
        )
        self.assertEqual("external_evidence_intake.v1", payload["external_evidence_intake"]["schema_version"])
        self.assertEqual(0, payload["external_evidence_intake"]["record_count"])
        self.assertEqual(0, payload["external_evidence_intake"]["accepted_record_count"])
        self.assertFalse(payload["external_evidence_intake"]["rollup"]["first_real_external_record_present"])
        self.assertTrue(
            payload["external_evidence_intake"]["validation_policy"]["reject_repository_maintainer_as_external"]
        )
        self.assertTrue(
            payload["external_evidence_intake"]["validation_policy"]["reject_self_signed_repo_native_records"]
        )
        self.assertEqual(
            "artifacts/external_validation_campaign.v1.json",
            payload["source_paths"]["externalValidationCampaign"],
        )
        self.assertEqual("external_validation_campaign.v1", payload["external_validation_campaign"]["schema_version"])
        self.assertEqual(6, payload["external_validation_campaign"]["workstream_count"])
        self.assertEqual(0, payload["external_validation_campaign"]["rollup"]["accepted_record_count"])
        self.assertFalse(payload["external_validation_campaign"]["rollup"]["external_validation_completed"])
        self.assertFalse(
            payload["external_validation_campaign"]["proof_promotion_review"]["automatic_claim_promotion_allowed"]
        )
        self.assertEqual(
            "artifacts/release_candidate_readiness.v1.json",
            payload["source_paths"]["releaseCandidateReadiness"],
        )
        self.assertEqual("release_candidate_readiness.v1", payload["release_candidate_readiness"]["schema_version"])
        self.assertTrue(payload["release_candidate_readiness"]["rollup"]["repo_publication_candidate_ready"])
        self.assertFalse(payload["release_candidate_readiness"]["rollup"]["certification_go"])

    def test_build_browser_dataset_matches_committed_artifact(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_output = Path(tmp_dir) / "browser_dataset.v1.json"
            result = build_browser_dataset_artifact.build_browser_dataset(
                repo_root=repo_root,
                determinism_status_path=Path("artifacts/determinism_status.json"),
                failure_surface_path=Path("artifacts/failure_surface_baseline.v1.json"),
                manifest_path=Path("artifacts/parameter_drilldown_manifest.json"),
                static_graph_path=Path("artifacts/parameter_static_usage_graph.json"),
                evidence_index_path=Path("artifacts/parameter_evidence_index.json"),
                p_success_defensibility_path=Path("artifacts/p_success_defensibility.json"),
                objective_score_path=Path("artifacts/objective_score_baseline.v1.json"),
                optimization_search_space_path=Path("artifacts/optimization_search_space.v1.json"),
                optimization_frontier_path=Path("artifacts/optimization_frontier_realistic.v1.json"),
                output_path=temp_output,
            )

            self.assertEqual("PASS", result["status"])
            self.assertEqual(
                _load_json(repo_root / "artifacts" / "browser_dataset.v1.json"),
                _load_json(temp_output),
            )

    def test_validate_browser_dataset_rejects_source_path_drift(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")
        payload["source_paths"]["optimizationFrontier"] = "artifacts/not-the-frontier.json"

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertTrue(
            any("source_paths.optimizationFrontier mismatch" in error for error in errors),
        )

    def test_validate_browser_dataset_rejects_uncertainty_correlation_overclaim(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")
        payload["uncertainty_interactions"]["pair_interactions"][0]["correlation"]["rho"] = 0.2

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertTrue(
            any("correlation.rho must be null" in error for error in errors),
            msg=str(errors),
        )

    def test_validate_browser_dataset_rejects_evidence_campaign_internal_leak(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")
        payload["evidence_upgrade_campaign"]["public_top_priorities"][0]["parameter_id"] = "code_literal.synthetic"

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertTrue(
            any("evidence_upgrade_campaign public row leaks internal parameter" in error for error in errors),
            msg=str(errors),
        )

    def test_validate_browser_dataset_rejects_external_review_overclaim(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")
        payload["external_validation_review_pack"]["rollup"]["external_validation_claimed"] = True

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertTrue(
            any("external_validation_review_pack.rollup.external_validation_claimed" in error for error in errors),
            msg=str(errors),
        )

    def test_validate_browser_dataset_rejects_external_proof_overclaim(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")
        payload["release_candidate_readiness"]["rollup"]["certification_go"] = True

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertTrue(
            any("release_candidate_readiness.rollup.certification_go" in error for error in errors),
            msg=str(errors),
        )

    def test_validate_browser_dataset_rejects_fake_external_record_intake(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")
        payload["external_evidence_intake"]["accepted_record_count"] = 1
        payload["external_evidence_intake"]["rollup"]["first_real_external_record_present"] = True

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertTrue(
            any("external_evidence_intake.accepted_record_count" in error for error in errors),
            msg=str(errors),
        )

    def test_validate_browser_dataset_rejects_external_validation_campaign_overclaim(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")
        payload["external_validation_campaign"]["rollup"]["first_real_external_record_present"] = True
        payload["external_validation_campaign"]["proof_promotion_review"][
            "automatic_claim_promotion_allowed"
        ] = True

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertTrue(
            any("external_validation_campaign.rollup.first_real_external_record_present" in error for error in errors),
            msg=str(errors),
        )
        self.assertTrue(
            any("external_validation_campaign.proof_promotion_review.automatic_claim_promotion_allowed" in error for error in errors),
            msg=str(errors),
        )

    def test_validate_browser_dataset_rejects_public_narrative_overclaim(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")
        payload["public_narrative_hardening"]["rollup"]["external_wording_audit_completed"] = True

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertTrue(
            any("public_narrative_hardening.rollup.external_wording_audit_completed" in error for error in errors),
            msg=str(errors),
        )

    def test_validate_browser_dataset_rejects_optimization_v2_overclaim(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")
        payload["optimization_v2"]["rollup"]["global_optimum_claimed"] = True

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertTrue(
            any("global_optimum_claimed" in error for error in errors),
            msg=str(errors),
        )

    def test_validate_browser_dataset_rejects_internal_optimization_leak(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")
        payload["optimization_search_space"]["excluded_parameters"].append(
            {
                "parameter_id": "code_literal.synthetic.module.literal_0",
                "exclusion_reason": ["synthetic"],
                "trust_grade": "C",
                "domain": "realistic",
            }
        )

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertTrue(
            any("optimization_search_space.excluded_parameters" in error for error in errors),
            msg=str(errors),
        )

    def test_validate_browser_dataset_rejects_manifest_internal_visibility_metadata(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        payload = _load_json(repo_root / "artifacts" / "browser_dataset.v1.json")
        payload["manifest"]["parameters"][0]["visibility"] = "internal"
        payload["manifest"]["parameters"][0]["public_surfaces"] = []
        payload["manifest"]["parameters"][0]["audit_scope"] = "code_literal"

        errors = build_browser_dataset_artifact.validate_browser_dataset(
            payload=payload,
            repo_root=repo_root,
        )

        self.assertTrue(
            any("manifest.parameters" in error and "visibility" in error for error in errors),
            msg=str(errors),
        )


if __name__ == "__main__":
    unittest.main()
