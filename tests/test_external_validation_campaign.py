from __future__ import annotations

import copy
from importlib import import_module
import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _validation_campaign_module():
    try:
        return import_module("mission.validation_campaign")
    except ModuleNotFoundError as exc:
        raise AssertionError("mission.validation_campaign must expose campaign builders") from exc


def _load_artifact(name: str) -> dict:
    path = REPO_ROOT / "artifacts" / name
    if not path.exists():
        raise AssertionError(f"committed validation-campaign artifact missing: artifacts/{name}")
    return json.loads(path.read_text(encoding="utf-8"))


class ExternalValidationCampaignTests(unittest.TestCase):
    def test_campaign_covers_all_six_workstreams_without_claiming_external_completion(self) -> None:
        campaign = _validation_campaign_module()
        payload = campaign.build_external_validation_campaign(REPO_ROOT)

        self.assertEqual("external_validation_campaign.v1", payload["schema_version"])
        self.assertEqual([], campaign.validate_external_validation_campaign(payload, repo_root=REPO_ROOT))
        self.assertEqual(payload, _load_artifact("external_validation_campaign.v1.json"))
        self.assertEqual("repo_campaign_ready_external_execution_required", payload["campaign_status"])
        self.assertEqual(6, payload["workstream_count"])
        self.assertEqual(
            [
                "first-real-external-record",
                "independent-physics-backend",
                "capsule-qualification-program",
                "line-of-sight-environment-model",
                "proof-promotion-review",
                "public-evidence-dossier",
            ],
            [row["workstream_id"] for row in payload["workstreams"]],
        )
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(0, payload["rollup"]["accepted_external_record_count"])
        self.assertFalse(payload["rollup"]["first_real_external_record_present"])
        self.assertFalse(payload["rollup"]["external_validation_completed"])
        self.assertFalse(payload["rollup"]["independent_backend_validated"])
        self.assertFalse(payload["rollup"]["qualification_complete"])
        self.assertFalse(payload["rollup"]["certification_go"])

    def test_campaign_tracks_backend_environment_qualification_promotion_and_dossier_boundaries(self) -> None:
        campaign = _validation_campaign_module()
        payload = campaign.build_external_validation_campaign(REPO_ROOT)

        backend = payload["independent_backend_execution_plan"]
        self.assertEqual("external_required", backend["status"])
        self.assertEqual(5, backend["repo_analytic_check_count"])
        self.assertFalse(backend["independent_external_backend_complete"])
        self.assertFalse(backend["high_fidelity_state_trace_complete"])

        environment = payload["line_of_sight_environment_model"]
        self.assertEqual("direction_dependent_model_required", environment["status"])
        self.assertGreaterEqual(len(environment["source_backed_anchors"]), 4)
        self.assertIn("exact mm/cm interstellar dust flux over Myr horizons", environment["assumption_bound_families"])
        self.assertFalse(environment["rollup"]["line_of_sight_model_complete"])

        qualification = payload["capsule_qualification_program"]
        self.assertEqual("external_required", qualification["status"])
        self.assertEqual(0, qualification["lab_record_count"])
        self.assertGreaterEqual(qualification["test_count"], 6)
        self.assertFalse(qualification["qualification_complete"])

        promotion = payload["proof_promotion_review"]
        self.assertEqual("blocked_until_valid_external_records", promotion["status"])
        self.assertTrue(promotion["requires_followup_review"])
        self.assertFalse(promotion["automatic_claim_promotion_allowed"])
        self.assertEqual([], promotion["promoted_claims"])

        dossier = payload["public_evidence_dossier"]
        self.assertEqual("repo_dossier_ready_external_records_absent", dossier["status"])
        self.assertTrue(dossier["shows_blocked_claims"])
        self.assertFalse(dossier["marketing_claim_surface"])
        self.assertFalse(dossier["certification_language_allowed"])

    def test_campaign_validator_rejects_overclaims_and_manual_external_records(self) -> None:
        campaign = _validation_campaign_module()
        payload = campaign.build_external_validation_campaign(REPO_ROOT)
        cases = [
            ("rollup", "external_validation_completed", True),
            ("rollup", "first_real_external_record_present", True),
            ("rollup", "certification_go", True),
            ("independent_backend_execution_plan", "independent_external_backend_complete", True),
            ("line_of_sight_environment_model", "line_of_sight_model_complete", True),
            ("capsule_qualification_program", "qualification_complete", True),
            ("proof_promotion_review", "automatic_claim_promotion_allowed", True),
            ("public_evidence_dossier", "certification_language_allowed", True),
        ]
        for section, field, value in cases:
            with self.subTest(section=section, field=field):
                broken = copy.deepcopy(payload)
                broken[section][field] = value
                if section == "rollup":
                    broken[section][field] = value

                errors = campaign.validate_external_validation_campaign(broken, repo_root=REPO_ROOT)

                self.assertTrue(errors)
                self.assertTrue(any(field in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
