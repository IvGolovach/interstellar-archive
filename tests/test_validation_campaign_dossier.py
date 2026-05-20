from __future__ import annotations

import copy
from importlib import import_module
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


EXPECTED_TRACK_IDS = [
    "ballistic-limit",
    "hydrocode-correlation",
    "radiation-transport",
    "archive-media-aging",
    "ecc-recovery",
    "independent-review",
]


def _validation_campaign_module():
    try:
        return import_module("mission.validation_campaign")
    except ModuleNotFoundError as exc:
        raise AssertionError("mission.validation_campaign must expose dossier builders") from exc


class ValidationCampaignDossierTests(unittest.TestCase):
    def test_capsule_qualification_program_keeps_all_tracks_external(self) -> None:
        campaign = _validation_campaign_module()
        payload = campaign.build_capsule_qualification_program(REPO_ROOT)

        self.assertEqual("capsule_qualification_program.v1", payload["schema_version"])
        self.assertEqual([], campaign.validate_capsule_qualification_program(payload, repo_root=REPO_ROOT))
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual("planned_external_records_required", payload["qualification_program_status"])
        self.assertEqual(0, payload["lab_record_count"])
        self.assertEqual([], payload["lab_records"])
        self.assertEqual(EXPECTED_TRACK_IDS, [track["track_id"] for track in payload["qualification_tracks"]])
        self.assertTrue(all(track["status"] == "external_required" for track in payload["qualification_tracks"]))
        self.assertTrue(all(track["external_required"] is True for track in payload["qualification_tracks"]))
        self.assertTrue(all(track["lab_record_count"] == 0 for track in payload["qualification_tracks"]))
        self.assertTrue(payload["rollup"]["all_tracks_external_required"])
        self.assertFalse(payload["rollup"]["qualification_complete"])
        self.assertFalse(payload["rollup"]["certification_claimed"])
        self.assertFalse(payload["rollup"]["flight_ready_claimed"])
        self.assertFalse(payload["rollup"]["legal_public_approval_claimed"])
        self.assertIn("qualification complete", payload["blocked_claims"])
        self.assertIn("certified", payload["blocked_claims"])
        self.assertIn("flight-ready", payload["blocked_claims"])
        self.assertIn("legal or public approval complete", payload["blocked_claims"])

    def test_public_evidence_dossier_summarizes_sources_without_overclaiming(self) -> None:
        campaign = _validation_campaign_module()
        payload = campaign.build_public_evidence_dossier(REPO_ROOT)

        self.assertEqual("public_evidence_dossier.v1", payload["schema_version"])
        self.assertEqual([], campaign.validate_public_evidence_dossier(payload, repo_root=REPO_ROOT))
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual("repo_native_dossier_ready_external_records_open", payload["dossier_status"])
        self.assertEqual("reviewer_facing_evidence_boundary", payload["public_scope"])
        self.assertEqual(0, payload["external_record_count"])
        self.assertEqual(0, payload["accepted_external_record_count"])
        self.assertEqual("capsule_qualification_program.v1", payload["qualification_program"]["schema_version"])
        self.assertEqual("planned_external_records_required", payload["qualification_program"]["qualification_program_status"])
        self.assertEqual(6, payload["dossier_sections"]["qualification_program"]["track_count"])
        self.assertEqual(0, payload["dossier_sections"]["qualification_program"]["lab_record_count"])
        self.assertGreaterEqual(payload["dossier_sections"]["design_evidence"]["material_count"], 6)
        self.assertGreaterEqual(payload["dossier_sections"]["external_review"]["review_case_count"], 7)
        self.assertGreaterEqual(payload["dossier_sections"]["claim_boundary"]["blocked_claim_count"], 10)
        self.assertFalse(payload["claim_status"]["qualification_complete"])
        self.assertFalse(payload["claim_status"]["certification_claimed"])
        self.assertFalse(payload["claim_status"]["flight_ready_claimed"])
        self.assertFalse(payload["claim_status"]["legal_public_approval_claimed"])
        self.assertFalse(payload["claim_status"]["public_claim_approval_claimed"])
        self.assertEqual([], payload["approved_public_claims"])
        self.assertIn("qualification complete", payload["blocked_claims"])
        self.assertIn("certified", payload["blocked_claims"])
        self.assertIn("flight-ready", payload["blocked_claims"])
        self.assertIn("legal or public approval complete", payload["blocked_claims"])

    def test_validators_reject_claim_promotion_and_record_fabrication(self) -> None:
        campaign = _validation_campaign_module()
        cases = [
            (
                campaign.build_capsule_qualification_program(REPO_ROOT),
                campaign.validate_capsule_qualification_program,
                lambda item: item["rollup"].update({"qualification_complete": True}),
                "qualification_complete",
            ),
            (
                campaign.build_capsule_qualification_program(REPO_ROOT),
                campaign.validate_capsule_qualification_program,
                lambda item: item["qualification_tracks"][0].update({"status": "complete", "lab_record_count": 1}),
                "qualification_tracks[0].status",
            ),
            (
                campaign.build_public_evidence_dossier(REPO_ROOT),
                campaign.validate_public_evidence_dossier,
                lambda item: item["claim_status"].update({"certification_claimed": True}),
                "certification_claimed",
            ),
            (
                campaign.build_public_evidence_dossier(REPO_ROOT),
                campaign.validate_public_evidence_dossier,
                lambda item: item.update({"approved_public_claims": ["public wording approved"]}),
                "approved_public_claims",
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
