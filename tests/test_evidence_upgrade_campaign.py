from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from mission.evidence_upgrade import (
    build_evidence_upgrade_campaign,
    validate_evidence_upgrade_campaign,
)
from mission.evidence_upgrade.campaign import SCHEMA_VERSION


REPO_ROOT = Path(__file__).resolve().parents[1]


class EvidenceUpgradeCampaignTests(unittest.TestCase):
    def test_committed_artifact_validates_and_keeps_upgrades_as_work_items(self) -> None:
        payload = json.loads((REPO_ROOT / "artifacts" / "evidence_upgrade_campaign.v1.json").read_text(encoding="utf-8"))

        self.assertEqual([], validate_evidence_upgrade_campaign(payload))
        self.assertEqual(SCHEMA_VERSION, payload["schema_version"])
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(66, payload["claim_count"])
        self.assertEqual({"B": 8, "C": 56, "D": 2}, payload["trust_distribution"])
        self.assertEqual({"B": 8, "C": 21, "D": 2}, payload["public_trust_distribution"])
        self.assertEqual(31, payload["public_campaign_count"])
        self.assertEqual(35, payload["internal_audit_count"])
        self.assertEqual(15, payload["top_priority_count"])
        self.assertIn("trust grades upgraded automatically", payload["blocked_claims"])
        self.assertIn("source correctness proven", payload["blocked_claims"])

        top = payload["top_priorities"][0]
        self.assertIn(top["visibility"], {"public", "internal"})
        self.assertGreaterEqual(top["priority_score"], payload["top_priorities"][-1]["priority_score"])
        self.assertIn("automatic trust promotion", top["blocked_claims"])

    def test_builder_is_deterministic(self) -> None:
        first = build_evidence_upgrade_campaign(REPO_ROOT)
        second = build_evidence_upgrade_campaign(REPO_ROOT)

        self.assertEqual(first, second)
        self.assertEqual([], validate_evidence_upgrade_campaign(first))

    def test_validator_rejects_overclaim_and_scope_breaks(self) -> None:
        payload = build_evidence_upgrade_campaign(REPO_ROOT)
        cases = [
            ("non_certification_notice", lambda item: item.update({"non_certification_notice": False})),
            ("trust_distribution", lambda item: item.update({"trust_distribution": {"A": 66}})),
            ("public_campaign_rows", lambda item: item.update({"public_campaign_rows": []})),
            ("automatic trust promotion", lambda item: item["campaign_rows"][0].update({"blocked_claims": []})),
            (
                "D-grade rows",
                lambda item: next(
                    row for row in item["campaign_rows"] if row["current_trust_grade"] == "D"
                ).update({"target_trust_grade": "B"}),
            ),
            ("top_priorities", lambda item: item.update({"top_priorities": list(reversed(item["top_priorities"]))})),
            ("source correctness proof", lambda item: item.update({"blocked_claims": ["trust grades upgraded automatically"]})),
        ]
        for expected, mutate in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = validate_evidence_upgrade_campaign(broken)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
