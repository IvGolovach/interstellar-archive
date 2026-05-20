from __future__ import annotations

import copy
from importlib import import_module
import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _external_proof_module():
    try:
        return import_module("mission.external_proof")
    except ModuleNotFoundError as exc:
        raise AssertionError("mission.external_proof package must expose proof-phase builders") from exc


def _load_artifact(name: str) -> dict:
    path = REPO_ROOT / "artifacts" / name
    if not path.exists():
        raise AssertionError(f"committed proof-phase artifact missing: artifacts/{name}")
    return json.loads(path.read_text(encoding="utf-8"))


class ExternalProofPhaseTests(unittest.TestCase):
    def test_external_validation_execution_ledger_is_open_and_deterministic(self) -> None:
        proof = _external_proof_module()
        payload = proof.build_external_validation_execution_ledger(REPO_ROOT)

        self.assertEqual("external_validation_execution_ledger.v1", payload["schema_version"])
        self.assertEqual([], proof.validate_external_validation_execution_ledger(payload, repo_root=REPO_ROOT))
        self.assertEqual(payload, _load_artifact("external_validation_execution_ledger.v1.json"))
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(7, payload["review_case_count"])
        self.assertEqual(0, payload["execution_record_count"])
        self.assertEqual(0, payload["external_record_count"])
        self.assertEqual(
            "repo_native_execution_ledger_ready_external_records_not_uploaded",
            payload["execution_ledger_status"],
        )
        self.assertTrue(
            all(row["execution_status"] == "external_required" for row in payload["execution_cases"])
        )
        self.assertTrue(
            all(row["external_record_status"] == "no_external_record_uploaded" for row in payload["execution_cases"])
        )
        self.assertFalse(payload["rollup"]["external_validation_completed"])
        self.assertFalse(payload["rollup"]["third_party_records_uploaded"])
        self.assertFalse(payload["rollup"]["independent_reproduction_completed"])
        self.assertIn("external validation completed", payload["blocked_claims"])

    def test_independent_physics_backend_comparison_is_repo_crosscheck_not_external_validation(self) -> None:
        proof = _external_proof_module()
        payload = proof.build_independent_physics_backend_comparison(REPO_ROOT)

        self.assertEqual("independent_physics_backend_comparison.v1", payload["schema_version"])
        self.assertEqual([], proof.validate_independent_physics_backend_comparison(payload, repo_root=REPO_ROOT))
        self.assertEqual(payload, _load_artifact("independent_physics_backend_comparison.v1.json"))
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(
            "repo_analytic_crosscheck_ready_external_backend_open",
            payload["comparison_status"],
        )
        self.assertGreaterEqual(payload["analytic_check_count"], 4)
        self.assertLessEqual(payload["rollup"]["max_relative_error"], 1e-9)
        self.assertFalse(payload["rollup"]["independent_external_backend_complete"])
        self.assertFalse(payload["rollup"]["cross_backend_comparison_completed"])
        self.assertFalse(payload["rollup"]["high_fidelity_state_trace_complete"])
        self.assertIn("independent physics backend validated", payload["blocked_claims"])

    def test_capsule_qualification_pack_tracks_material_stack_without_claiming_lab_completion(self) -> None:
        proof = _external_proof_module()
        payload = proof.build_capsule_qualification_evidence_pack(REPO_ROOT)

        self.assertEqual("capsule_qualification_evidence_pack.v1", payload["schema_version"])
        self.assertEqual([], proof.validate_capsule_qualification_evidence_pack(payload, repo_root=REPO_ROOT))
        self.assertEqual(payload, _load_artifact("capsule_qualification_evidence_pack.v1.json"))
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual("interstellar_archive_capsule_v1", payload["capsule_design"]["design_id"])
        self.assertEqual(206.0, payload["mass_closure"]["configured_capsule_mass_kg"])
        self.assertEqual(206.0, payload["mass_closure"]["component_mass_kg"])
        self.assertTrue(payload["mass_closure"]["within_declared_margin"])
        self.assertGreaterEqual(payload["material_count"], 6)
        self.assertGreaterEqual(payload["layer_count"], 6)
        self.assertGreaterEqual(payload["qualification_test_count"], 6)
        self.assertEqual(0, payload["lab_record_count"])
        self.assertFalse(payload["rollup"]["qualification_complete"])
        self.assertFalse(payload["rollup"]["flight_ready_claimed"])
        self.assertIn("qualified", payload["blocked_claims"])

    def test_evidence_upgrade_closure_closes_no_trust_grades_without_new_external_sources(self) -> None:
        proof = _external_proof_module()
        payload = proof.build_evidence_upgrade_closure(REPO_ROOT)

        self.assertEqual("evidence_upgrade_closure.v1", payload["schema_version"])
        self.assertEqual([], proof.validate_evidence_upgrade_closure(payload, repo_root=REPO_ROOT))
        self.assertEqual(payload, _load_artifact("evidence_upgrade_closure.v1.json"))
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(15, payload["closure_cycle_count"])
        self.assertEqual(0, payload["rollup"]["external_source_upgrade_count"])
        self.assertEqual(0, payload["rollup"]["trust_grade_promotion_count"])
        self.assertFalse(payload["rollup"]["source_correctness_claimed"])
        self.assertFalse(payload["rollup"]["trust_grades_upgraded_automatically"])
        self.assertIn("trust grades upgraded automatically", payload["blocked_claims"])
        by_parameter = {row["parameter_id"]: row for row in payload["closure_rows"]}
        self.assertEqual(
            "speculative_quarantined",
            by_parameter["environment_model.non_physical_safety_multiplier"]["closure_status"],
        )
        self.assertEqual(
            "speculative_quarantined",
            by_parameter["trajectory_model.non_physical_capture_bias"]["closure_status"],
        )

    def test_release_candidate_readiness_is_publication_candidate_not_certification_gate(self) -> None:
        proof = _external_proof_module()
        payload = proof.build_release_candidate_readiness(REPO_ROOT)

        self.assertEqual("release_candidate_readiness.v1", payload["schema_version"])
        self.assertEqual([], proof.validate_release_candidate_readiness(payload, repo_root=REPO_ROOT))
        self.assertEqual(payload, _load_artifact("release_candidate_readiness.v1.json"))
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(
            "repo_publication_candidate_external_evidence_open",
            payload["release_candidate_status"],
        )
        self.assertTrue(payload["rollup"]["repo_publication_candidate_ready"])
        self.assertFalse(payload["rollup"]["certification_go"])
        self.assertFalse(payload["rollup"]["external_validation_completed"])
        self.assertFalse(payload["rollup"]["qualification_complete"])
        self.assertFalse(payload["rollup"]["independent_backend_validated"])
        self.assertIn("external_validation_execution_ledger", payload["component_rollups"])
        self.assertIn("external_reproduction_kit", payload["component_rollups"])
        self.assertIn("external_evidence_intake", payload["component_rollups"])
        self.assertIn("external_validation_campaign", payload["component_rollups"])
        self.assertIn("capsule_qualification_evidence_pack", payload["component_rollups"])
        self.assertIn("certified", payload["blocked_claims"])

    def test_validators_reject_external_proof_overclaims(self) -> None:
        proof = _external_proof_module()
        cases = [
            (
                proof.build_external_validation_execution_ledger(REPO_ROOT),
                proof.validate_external_validation_execution_ledger,
                lambda item: item["rollup"].update({"external_validation_completed": True}),
                "external_validation_completed",
            ),
            (
                proof.build_independent_physics_backend_comparison(REPO_ROOT),
                proof.validate_independent_physics_backend_comparison,
                lambda item: item["rollup"].update({"independent_external_backend_complete": True}),
                "independent_external_backend_complete",
            ),
            (
                proof.build_capsule_qualification_evidence_pack(REPO_ROOT),
                proof.validate_capsule_qualification_evidence_pack,
                lambda item: item["rollup"].update({"qualification_complete": True}),
                "qualification_complete",
            ),
            (
                proof.build_evidence_upgrade_closure(REPO_ROOT),
                proof.validate_evidence_upgrade_closure,
                lambda item: item["rollup"].update({"trust_grade_promotion_count": 1}),
                "trust_grade_promotion_count",
            ),
            (
                proof.build_release_candidate_readiness(REPO_ROOT),
                proof.validate_release_candidate_readiness,
                lambda item: item["rollup"].update({"certification_go": True}),
                "certification_go",
            ),
        ]
        for payload, validator, mutate, expected in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = validator(broken, repo_root=REPO_ROOT)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
