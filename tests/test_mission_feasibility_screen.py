from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from mission.feasibility.screen import SCHEMA_VERSION, validate_feasibility_screen
from mission.feasibility import build_feasibility_screen


REPO_ROOT = Path(__file__).resolve().parents[1]


class MissionFeasibilityScreenTests(unittest.TestCase):
    def test_committed_artifact_validates_and_has_default_ten_myr_row(self) -> None:
        payload = json.loads((REPO_ROOT / "artifacts" / "mission_feasibility_screen.v1.json").read_text(encoding="utf-8"))

        self.assertEqual([], validate_feasibility_screen(payload))
        self.assertEqual(SCHEMA_VERSION, payload["schema_version"])
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(3, payload["target_count"])
        self.assertEqual(5, payload["velocity_count"])
        self.assertEqual(15, payload["scenario_count"])
        self.assertEqual(15, payload["capsule_risk_budget_match_count"])
        self.assertGreater(payload["default_black_hole_flight_years"], 10_000_000)
        self.assertLess(payload["default_black_hole_flight_years"], 10_700_000)

        default_row = next(row for row in payload["scenario_rows"] if row["id"] == payload["default_scenario_id"])
        self.assertEqual("reference-black-hole", default_row["target_id"])
        self.assertEqual("conditional-45", default_row["velocity_id"])
        self.assertTrue(default_row["black_hole_screen"]["crossing_condition_met"])
        self.assertTrue(default_row["capsule_risk_budget_link"]["matched"])
        self.assertTrue(default_row["external_evidence_gaps"])
        self.assertIn("flight ready", default_row["blocked_claims"])

    def test_builder_is_deterministic(self) -> None:
        first = build_feasibility_screen(REPO_ROOT)
        second = build_feasibility_screen(REPO_ROOT)

        self.assertEqual(first, second)
        self.assertEqual([], validate_feasibility_screen(first))

    def test_validator_rejects_contract_breaks(self) -> None:
        payload = build_feasibility_screen(REPO_ROOT)

        def break_default_year(item: dict) -> None:
            for row in item["scenario_rows"]:
                if row["id"] == item["default_scenario_id"]:
                    row["flight_years"] = 9_000_000
                    return

        cases = [
            ("non_certification_notice", lambda item: item.update({"non_certification_notice": False})),
            ("scenario_rows", lambda item: item.update({"scenario_rows": item["scenario_rows"][:-1]})),
            ("capsule_risk_budget_match_count", lambda item: item.update({"capsule_risk_budget_match_count": 0})),
            ("default reference black-hole", break_default_year),
            ("external_evidence_gaps", lambda item: item["scenario_rows"][0].update({"external_evidence_gaps": []})),
            ("blocked_claims", lambda item: item["scenario_rows"][0].update({"blocked_claims": []})),
        ]
        for expected, mutate in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = validate_feasibility_screen(broken)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
