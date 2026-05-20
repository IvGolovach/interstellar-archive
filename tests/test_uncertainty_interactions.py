from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from mission.uncertainty.interactions import (
    SCHEMA_VERSION,
    build_uncertainty_interactions,
    validate_uncertainty_interactions,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class UncertaintyInteractionsTests(unittest.TestCase):
    def test_committed_artifact_validates_and_keeps_correlations_open(self) -> None:
        payload = json.loads((REPO_ROOT / "artifacts" / "uncertainty_interactions.v1.json").read_text(encoding="utf-8"))

        self.assertEqual([], validate_uncertainty_interactions(payload))
        self.assertEqual(SCHEMA_VERSION, payload["schema_version"])
        self.assertEqual("realistic", payload["mode"])
        self.assertEqual(4, payload["uncertainty_entry_count"])
        self.assertEqual(6, payload["interaction_pair_count"])
        self.assertEqual(0, payload["rollup"]["validated_correlation_count"])
        self.assertFalse(payload["rollup"]["full_uncertainty_interaction_closure"])
        self.assertIn("validated uncertainty independence", payload["blocked_claims"])

        default_pair = next(
            row
            for row in payload["pair_interactions"]
            if row["pair_id"] == payload["rollup"]["dominant_pair_id"]
        )
        self.assertEqual("external_correlation_evidence_required", default_pair["status"])
        self.assertIsNone(default_pair["correlation"]["rho"])
        self.assertGreaterEqual(default_pair["interaction_residual"]["max_abs"], 0.0)

    def test_builder_is_deterministic(self) -> None:
        first = build_uncertainty_interactions(REPO_ROOT)
        second = build_uncertainty_interactions(REPO_ROOT)

        self.assertEqual(first, second)
        self.assertEqual([], validate_uncertainty_interactions(first))

    def test_validator_rejects_correlation_and_residual_overclaims(self) -> None:
        payload = build_uncertainty_interactions(REPO_ROOT)
        cases = [
            ("correlation", lambda item: item["pair_interactions"][0]["correlation"].update({"rho": 0.3})),
            ("status", lambda item: item["pair_interactions"][0].update({"status": "validated"})),
            ("full_uncertainty_interaction_closure", lambda item: item["rollup"].update({"full_uncertainty_interaction_closure": True})),
            ("validated_correlation_count", lambda item: item["rollup"].update({"validated_correlation_count": 1})),
            ("blocked_claims", lambda item: item.update({"blocked_claims": []})),
            ("interaction_residual.low_low", lambda item: item["pair_interactions"][0]["interaction_residual"].update({"low_low": 0.123})),
        ]
        for expected, mutate in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = validate_uncertainty_interactions(broken)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
