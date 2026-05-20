from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "mission_baseline_check.py"
MISSION_DIR = REPO_ROOT / "mission"


class MissionDefinitionLayerTests(unittest.TestCase):
    def test_required_mission_files_exist(self) -> None:
        required = [
            "MISSION_SPEC_v1.md",
            "MISSION_SCHEMA_v1.json",
            "MISSION_LAYER_SUMMARY.md",
            "PARAMETER_CATALOG_v1.md",
            "UNCERTAINTY_MODEL_v1.md",
            "SUCCESS_METRIC_v1.md",
            "CORRECTION_WINDOW_MODEL_v1.md",
            "BLACK_HOLE_ENV_FILTER_v1.md",
            "BASELINE_SCENARIO_v1.json",
            "SENSITIVITY_PLAN_v1.md",
            "LIMITATIONS_AND_NON_GOALS_APPENDIX.md",
        ]
        for name in required:
            path = MISSION_DIR / name
            self.assertTrue(path.exists(), f"missing {name}")
            self.assertGreater(path.stat().st_size, 0, f"empty {name}")

    def test_schema_and_baseline_validate(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--validate-only"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS", proc.stdout)

    def test_baseline_check_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "mission_output.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--mode",
                    "realistic",
                    "--verify-deterministic",
                    "--output",
                    str(out_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            for field in [
                "schwarzschild_radius_m",
                "crossing_condition_met",
                "environment_acceptable",
                "p_hit",
                "p_survive",
                "p_data_intact",
                "p_success",
                "success_threshold",
                "success",
                "mode",
                "speculative_parameters_used",
                "trust_weighted_score",
                "core_probability",
                "deterministic_signature",
            ]:
                self.assertIn(field, payload)

    def test_dual_mode_report_contains_both_sections(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--mode",
                "dual",
                "--verify-deterministic",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("=== REALISTIC RESULT ===", proc.stdout)
        self.assertIn("=== SPECULATIVE RESULT ===", proc.stdout)

    def test_realistic_mode_rejects_speculative_override(self) -> None:
        scenario_path = MISSION_DIR / "BASELINE_SCENARIO_v1.json"
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        scenario["mission_mode"] = "realistic"
        scenario["speculative_overrides"] = [
            {
                "parameter_path": "trajectory_model.non_physical_capture_bias",
                "value": 0.2,
                "warning_text": "speculative",
            }
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_scenario = Path(tmp_dir) / "bad_scenario.json"
            bad_scenario.write_text(json.dumps(scenario), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--validate-only",
                    "--scenario",
                    str(bad_scenario),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("realistic mode forbids speculative_overrides", proc.stdout)


if __name__ == "__main__":
    unittest.main()
