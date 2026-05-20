from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from mission.review.validation_pack import (
    SCHEMA_VERSION,
    build_external_validation_review_pack,
    validate_external_validation_review_pack,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class ExternalValidationReviewPackTests(unittest.TestCase):
    def test_committed_artifact_validates_and_keeps_external_review_open(self) -> None:
        payload = json.loads((REPO_ROOT / "artifacts/external_validation_review_pack.v1.json").read_text())

        self.assertEqual([], validate_external_validation_review_pack(payload, repo_root=REPO_ROOT))
        self.assertEqual(SCHEMA_VERSION, payload["schema_version"])
        self.assertTrue(payload["non_certification_notice"])
        self.assertGreaterEqual(payload["review_case_count"], 6)
        self.assertFalse(payload["rollup"]["third_party_review_completed"])
        self.assertFalse(payload["rollup"]["independent_reproduction_completed"])
        self.assertFalse(payload["rollup"]["independent_benchmark_completed"])
        self.assertFalse(payload["rollup"]["high_fidelity_state_trace_complete"])
        self.assertFalse(payload["rollup"]["external_red_team_completed"])
        self.assertFalse(payload["rollup"]["external_validation_claimed"])
        self.assertTrue(payload["rollup"]["all_cases_require_external_review"])
        self.assertEqual(6, payload["rollup"]["external_deliverable_count"])
        self.assertEqual(6, len(payload["required_external_deliverables"]))
        self.assertIn("independent reproduction completed", payload["blocked_claims"])
        self.assertIn("third-party validated", payload["blocked_claims"])

    def test_builder_is_deterministic(self) -> None:
        committed = json.loads((REPO_ROOT / "artifacts/external_validation_review_pack.v1.json").read_text())
        built = build_external_validation_review_pack(REPO_ROOT)

        self.assertEqual(committed, built)
        self.assertEqual([], validate_external_validation_review_pack(built, repo_root=REPO_ROOT))

    def test_validator_rejects_external_validation_overclaims(self) -> None:
        payload = build_external_validation_review_pack(REPO_ROOT)
        cases = [
            ("non_certification_notice", lambda item: item.update({"non_certification_notice": False})),
            (
                "third_party_review_completed",
                lambda item: item["rollup"].update({"third_party_review_completed": True}),
            ),
            (
                "independent_reproduction_completed",
                lambda item: item["rollup"].update({"independent_reproduction_completed": True}),
            ),
            (
                "external_validation_claimed",
                lambda item: item["rollup"].update({"external_validation_claimed": True}),
            ),
            (
                "external_red_team_completed",
                lambda item: item["rollup"].update({"external_red_team_completed": True}),
            ),
            (
                "independent_result_available",
                lambda item: item["review_cases"][0].update({"independent_result_available": True}),
            ),
            ("blocked_claims", lambda item: item.update({"blocked_claims": ["flight ready"]})),
        ]
        for expected, mutate in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = validate_external_validation_review_pack(broken, repo_root=REPO_ROOT)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
