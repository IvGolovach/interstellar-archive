from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from mission.probability import (
    SCHEMA_VERSION,
    build_mission_probability_coupling,
    validate_mission_probability_coupling,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class MissionProbabilityCouplingTests(unittest.TestCase):
    def test_committed_artifact_validates_and_keeps_full_probability_open(self) -> None:
        payload = json.loads((REPO_ROOT / "artifacts" / "mission_probability_coupling.v1.json").read_text(encoding="utf-8"))

        self.assertEqual([], validate_mission_probability_coupling(payload))
        self.assertEqual(SCHEMA_VERSION, payload["schema_version"])
        self.assertEqual(15, payload["coupling_count"])
        self.assertEqual(0, payload["rollup"]["rows_with_full_mission_probability_closed"])
        self.assertTrue(payload["default_coupling_id"].startswith("mpc-reference-black-hole-conditional-45-"))

        default = next(row for row in payload["coupling_rows"] if row["coupling_id"] == payload["default_coupling_id"])
        self.assertEqual("not_closed_external_factors_open", default["full_mission_probability"]["status"])
        self.assertIsNone(default["full_mission_probability"]["p50"])
        self.assertGreater(default["closed_capsule_data_probability"]["p50"], 0.0)
        factors = {item["factor_id"]: item["value_p50"] for item in default["factor_budget"]}
        self.assertAlmostEqual(
            default["closed_capsule_data_probability"]["p50"],
            factors["capsule_survival"] * factors["data_integrity"],
            places=12,
        )
        self.assertIn("full mission probability closed", default["blocked_claims"])
        self.assertFalse(default["dag_coupling"]["writes_tracked_files"])

    def test_builder_is_deterministic(self) -> None:
        first = build_mission_probability_coupling(REPO_ROOT)
        second = build_mission_probability_coupling(REPO_ROOT)

        self.assertEqual(first, second)
        self.assertEqual([], validate_mission_probability_coupling(first))

    def test_validator_rejects_overclaim_and_probability_breaks(self) -> None:
        payload = build_mission_probability_coupling(REPO_ROOT)
        cases = [
            ("full_mission_probability.status", lambda item: item["coupling_rows"][0]["full_mission_probability"].update({"status": "closed"})),
            ("full_mission_probability.p50", lambda item: item["coupling_rows"][0]["full_mission_probability"].update({"p50": 0.5})),
            ("blocked_claims", lambda item: item["coupling_rows"][0].update({"blocked_claims": []})),
            ("open_external_factor_count", lambda item: item["coupling_rows"][0].update({"open_external_factor_count": 0})),
            ("closed_capsule_data_probability.p50", lambda item: item["coupling_rows"][0]["closed_capsule_data_probability"].update({"p50": 2.0})),
            ("capsule_survival * data_integrity", lambda item: item["coupling_rows"][0]["closed_capsule_data_probability"].update({"p50": 0.123})),
        ]
        for expected, mutate in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = validate_mission_probability_coupling(broken)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
