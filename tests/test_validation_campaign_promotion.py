from __future__ import annotations

import copy
from pathlib import Path
import unittest

from mission.external_reproduction import build_external_evidence_intake
from mission.validation_campaign import (
    build_external_validation_campaign,
    build_proof_promotion_review,
    validate_external_validation_campaign,
    validate_proof_promotion_review,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _accepted_intake_shape() -> dict:
    intake = build_external_evidence_intake(REPO_ROOT)
    accepted_record = {
        "path": "evidence/external_records/external-independent-reproduction-placeholder.json",
        "record_id": "external-independent-reproduction-placeholder",
        "record_type": "independent_reproduction",
        "review_case_id": "independent-backend-comparison",
    }
    intake["intake_status"] = "external_records_present_pending_claim_promotion_review"
    intake["record_count"] = 1
    intake["accepted_record_count"] = 1
    intake["accepted_records"] = [accepted_record]
    intake["rollup"]["record_count"] = 1
    intake["rollup"]["accepted_record_count"] = 1
    intake["rollup"]["first_real_external_record_present"] = True
    return intake


class ValidationCampaignPromotionTests(unittest.TestCase):
    def test_campaign_builder_covers_six_workstreams_without_external_records(self) -> None:
        payload = build_external_validation_campaign(REPO_ROOT)

        self.assertEqual("external_validation_campaign.v1", payload["schema_version"])
        self.assertEqual([], validate_external_validation_campaign(payload, repo_root=REPO_ROOT))
        self.assertTrue(payload["non_certification_notice"])
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
        self.assertEqual(0, payload["rollup"]["accepted_record_count"])
        self.assertFalse(payload["rollup"]["first_real_external_record_present"])
        self.assertTrue(payload["campaign_policy"]["records_do_not_directly_unlock_claims"])
        self.assertTrue(payload["campaign_policy"]["proof_promotion_requires_followup_review"])
        self.assertEqual(0, payload["proof_promotion_review"]["rollup"]["promoted_claim_count"])
        self.assertFalse(payload["proof_promotion_review"]["rollup"]["external_validation_completed"])
        self.assertEqual(payload, build_external_validation_campaign(REPO_ROOT))

    def test_proof_promotion_review_consumes_intake_shape_but_does_not_auto_promote(self) -> None:
        review = build_proof_promotion_review(REPO_ROOT, intake_payload=_accepted_intake_shape())

        self.assertEqual("proof_promotion_review.v1", review["schema_version"])
        self.assertEqual([], validate_proof_promotion_review(review))
        self.assertEqual(1, review["rollup"]["accepted_record_count"])
        self.assertTrue(review["rollup"]["first_real_external_record_present"])
        self.assertEqual(1, review["reviewed_record_count"])
        self.assertTrue(review["review_policy"]["records_do_not_directly_unlock_claims"])
        self.assertTrue(review["review_policy"]["proof_promotion_requires_followup_review"])
        self.assertTrue(review["review_policy"]["v1_auto_promotion_enabled"] is False)
        self.assertEqual(0, review["rollup"]["promoted_claim_count"])
        self.assertTrue(all(not row["promotion_allowed"] for row in review["claim_reviews"]))
        self.assertTrue(all(row["decision"] == "followup_review_required" for row in review["claim_reviews"]))

    def test_campaign_validator_enforces_default_zero_record_boundary(self) -> None:
        payload = build_external_validation_campaign(REPO_ROOT)
        broken = copy.deepcopy(payload)
        broken["rollup"]["accepted_record_count"] = 1
        broken["rollup"]["first_real_external_record_present"] = True
        broken["campaign_policy"]["records_do_not_directly_unlock_claims"] = False
        broken["campaign_policy"]["proof_promotion_requires_followup_review"] = False

        errors = validate_external_validation_campaign(broken, repo_root=REPO_ROOT)

        self.assertTrue(errors)
        self.assertTrue(any("accepted_record_count" in error for error in errors), errors)
        self.assertTrue(any("first_real_external_record_present" in error for error in errors), errors)
        self.assertTrue(any("records_do_not_directly_unlock_claims" in error for error in errors), errors)
        self.assertTrue(any("proof_promotion_requires_followup_review" in error for error in errors), errors)

    def test_proof_promotion_validator_rejects_any_manual_promotion(self) -> None:
        review = build_proof_promotion_review(REPO_ROOT, intake_payload=_accepted_intake_shape())
        broken = copy.deepcopy(review)
        broken["claim_reviews"][0]["promotion_allowed"] = True
        broken["claim_reviews"][0]["promoted"] = True
        broken["rollup"]["promoted_claim_count"] = 1
        broken["rollup"]["external_validation_completed"] = True

        errors = validate_proof_promotion_review(broken)

        self.assertTrue(errors)
        self.assertTrue(any("promotion_allowed" in error for error in errors), errors)
        self.assertTrue(any("promoted_claim_count" in error for error in errors), errors)
        self.assertTrue(any("external_validation_completed" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
