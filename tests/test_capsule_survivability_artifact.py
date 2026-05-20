from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_capsule_survivability_artifact import (
    build_capsule_survivability_artifact,
    validate_capsule_survivability_artifact,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class CapsuleSurvivabilityArtifactTests(unittest.TestCase):
    def test_committed_artifact_validates_and_contains_default_black_hole_row(self) -> None:
        payload = json.loads((REPO_ROOT / "artifacts" / "capsule_survivability_lab.v1.json").read_text(encoding="utf-8"))

        self.assertEqual([], validate_capsule_survivability_artifact(payload))
        self.assertEqual("capsule_survivability_lab.v1", payload["schema_version"])
        self.assertTrue(payload["non_certification_notice"])
        self.assertGreaterEqual(len(payload["rows"]), 100)
        self.assertGreaterEqual(len(payload["source_data"]), 16)

        default_row = next(
            row
            for row in payload["rows"]
            if row["targetId"] == "reference-black-hole"
            and row["velocityId"] == "conditional-45"
            and row["timeId"] == "ballistic-arrival"
            and row["capsuleId"] == "baseline-stack"
        )
        self.assertGreaterEqual(default_row["flightYears"], 10_000_000.0)
        self.assertLessEqual(default_row["flightYears"], 11_000_000.0)
        self.assertEqual("stressed", default_row["output"]["outcomeBand"])
        self.assertGreater(default_row["output"]["survivalP95"], default_row["output"]["survivalProbability"])

    def test_builder_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first_output = Path(temp_dir) / "first.json"
            second_output = Path(temp_dir) / "second.json"
            first = build_capsule_survivability_artifact(
                repo_root=REPO_ROOT,
                output_path=first_output,
                samples=16,
                seed=77,
            )
            second = build_capsule_survivability_artifact(
                repo_root=REPO_ROOT,
                output_path=second_output,
                samples=16,
                seed=77,
            )

            self.assertEqual("PASS", first["status"])
            self.assertEqual("PASS", second["status"])
            self.assertEqual(first["artifact_sha256"], second["artifact_sha256"])


if __name__ == "__main__":
    unittest.main()
