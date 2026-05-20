from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/ci/parameter_sensitivity_report.py"


class SensitivityDominantDriversTests(unittest.TestCase):
    def test_sensitivity_outputs_top_5(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "out"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--baseline",
                    "mission/BASELINE_SCENARIO_v1.json",
                    "--output-dir",
                    str(out_dir),
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            payload = json.loads((out_dir / "SENSITIVITY_RESULTS.json").read_text(encoding="utf-8"))
            self.assertEqual(5, len(payload["top_5"]))
            scores = [item["influence_score"] for item in payload["top_5"]]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_missing_binding_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            for rel in [
                "mission/BASELINE_SCENARIO_v1.json",
                "mission/MISSION_SCHEMA_v1.json",
                "parameters/registry/parameter_registry.v1.json",
                "parameters/registry/parameter_claims.v1.json",
            ]:
                src = REPO_ROOT / rel
                dst = tmp / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

            claims_path = tmp / "parameters/registry/parameter_claims.v1.json"
            claims = json.loads(claims_path.read_text(encoding="utf-8"))
            claims["claims"] = [item for item in claims["claims"] if item["parameter_id"] != "bh_parameters.mass_kg"]
            claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--baseline",
                    str(tmp / "mission/BASELINE_SCENARIO_v1.json"),
                    "--schema",
                    str(tmp / "mission/MISSION_SCHEMA_v1.json"),
                    "--parameter-registry",
                    str(tmp / "parameters/registry/parameter_registry.v1.json"),
                    "--parameter-claims",
                    str(tmp / "parameters/registry/parameter_claims.v1.json"),
                    "--output-dir",
                    str(tmp / "out"),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("missing parameter bindings", proc.stdout)


if __name__ == "__main__":
    unittest.main()
