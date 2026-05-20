from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from mission.user_runs.runtime_generation import (
    OUTPUT_FILES,
    SCHEMA_VERSION,
    build_runtime_scenario_generation,
    validate_runtime_scenario_generation,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class RuntimeScenarioGenerationTests(unittest.TestCase):
    def test_committed_artifact_validates_and_exposes_runtime_contract(self) -> None:
        payload = json.loads((REPO_ROOT / "artifacts/runtime_scenario_generation.v1.json").read_text(encoding="utf-8"))

        self.assertEqual([], validate_runtime_scenario_generation(payload))
        self.assertEqual(SCHEMA_VERSION, payload["schema_version"])
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(15, payload["generation_row_count"])
        self.assertFalse(payload["run_pack_contract"]["writes_tracked_files"])
        self.assertEqual(OUTPUT_FILES, payload["run_pack_contract"]["output_files"])
        self.assertFalse(payload["rollup"]["remote_execution_claimed"])
        self.assertFalse(payload["rollup"]["persistent_reviewed_archive_claimed"])

        default_row = next(
            row for row in payload["generation_rows"] if row["run_id"] == payload["selection_axes"]["default_run_id"]
        )
        self.assertEqual("reference-black-hole", default_row["target_id"])
        self.assertEqual("conditional-45", default_row["velocity_id"])
        self.assertIn("scripts/run_user_mission_scenario.py", default_row["command_preview"])
        self.assertIn("--verify-deterministic", default_row["command_preview"])
        self.assertIn("persistent reviewed run archive", default_row["blocked_claims"])

    def test_builder_is_deterministic(self) -> None:
        first = build_runtime_scenario_generation(REPO_ROOT)
        second = build_runtime_scenario_generation(REPO_ROOT)

        self.assertEqual(first, second)
        self.assertEqual([], validate_runtime_scenario_generation(first))

    def test_validator_rejects_runtime_overclaims(self) -> None:
        payload = build_runtime_scenario_generation(REPO_ROOT)
        cases = [
            ("non_certification_notice", lambda item: item.update({"non_certification_notice": False})),
            ("generation_rows", lambda item: item.update({"generation_rows": item["generation_rows"][:-1]})),
            ("command_preview", lambda item: item["generation_rows"][0].update({"command_preview": "python3 bad.py"})),
            (
                "writes_tracked_files",
                lambda item: item["generation_rows"][0]["run_pack_contract"].update({"writes_tracked_files": True}),
            ),
            (
                "remote_execution",
                lambda item: item["generation_rows"][0]["ownership_boundary"].update({"remote_execution": True}),
            ),
            ("blocked_claims", lambda item: item.update({"blocked_claims": ["flight ready"]})),
        ]
        for expected, mutate in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = validate_runtime_scenario_generation(broken)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
