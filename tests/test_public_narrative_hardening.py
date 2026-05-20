from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from mission.narrative.hardening import (
    SCHEMA_VERSION,
    build_public_narrative_hardening,
    validate_public_narrative_hardening,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicNarrativeHardeningTests(unittest.TestCase):
    def test_committed_artifact_validates_and_blocks_public_overclaims(self) -> None:
        payload = json.loads((REPO_ROOT / "artifacts/public_narrative_hardening.v1.json").read_text())

        self.assertEqual([], validate_public_narrative_hardening(payload, repo_root=REPO_ROOT))
        self.assertEqual(SCHEMA_VERSION, payload["schema_version"])
        self.assertTrue(payload["non_certification_notice"])
        self.assertGreaterEqual(payload["public_surface_count"], 8)
        self.assertEqual(0, payload["rollup"]["unsafe_public_overclaim_count"])
        self.assertFalse(payload["rollup"]["external_wording_audit_completed"])
        self.assertFalse(payload["rollup"]["audience_testing_completed"])
        self.assertTrue(payload["rollup"]["all_required_concepts_present"])
        self.assertIn("certified", payload["forbidden_public_claims"])
        self.assertIn("external validation completed", payload["forbidden_public_claims"])
        self.assertIn("deterministic artifact", payload["required_public_concepts"])

    def test_builder_is_deterministic(self) -> None:
        committed = json.loads((REPO_ROOT / "artifacts/public_narrative_hardening.v1.json").read_text())
        built = build_public_narrative_hardening(REPO_ROOT)

        self.assertEqual(committed, built)
        self.assertEqual([], validate_public_narrative_hardening(built, repo_root=REPO_ROOT))

    def test_validator_rejects_public_overclaim_drift(self) -> None:
        payload = build_public_narrative_hardening(REPO_ROOT)
        cases = [
            ("non_certification_notice", lambda item: item.update({"non_certification_notice": False})),
            (
                "unsafe_public_overclaim_count",
                lambda item: item["rollup"].update({"unsafe_public_overclaim_count": 1}),
            ),
            (
                "external_wording_audit_completed",
                lambda item: item["rollup"].update({"external_wording_audit_completed": True}),
            ),
            (
                "all_required_concepts_present",
                lambda item: item["rollup"].update({"all_required_concepts_present": False}),
            ),
            ("forbidden_public_claims", lambda item: item.update({"forbidden_public_claims": ["certified"]})),
        ]
        for expected, mutate in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = validate_public_narrative_hardening(broken, repo_root=REPO_ROOT)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
