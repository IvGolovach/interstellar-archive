from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from mission.user_runs.catalog import build_user_run_pack
from scripts.ci.user_mission_run_pack_validate import EXPECTED_SOURCE_PATHS, validate_pack


REPO_ROOT = Path(__file__).resolve().parents[1]


class UserMissionRunPackValidateTests(unittest.TestCase):
    def test_validator_accepts_temp_default_pack(self) -> None:
        run_id = "unit-pack-validator-v1"
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = build_user_run_pack(
                repo_root=REPO_ROOT,
                target_id="reference-black-hole",
                velocity_id="conditional-45",
                run_id=run_id,
                mode="dual",
                seed=1,
                output_dir=Path(tmp_dir) / run_id,
            )
            runner_payload = {
                "run_id": run_id,
                "output_dir": result["output_dir"],
                "summary_sha256": result["meta"]["summary_sha256"],
                "determinism": {"verdict": "PASS"},
                "verdict": "PASS",
            }

            errors = validate_pack(REPO_ROOT, Path(result["output_dir"]), runner_payload)

            self.assertEqual([], errors)
            manifest = json.loads((Path(result["output_dir"]) / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertTrue(EXPECTED_SOURCE_PATHS.issubset({entry["path"] for entry in manifest["source_manifest"]}))

    def test_validator_rejects_runtime_overclaims(self) -> None:
        run_id = "unit-pack-validator-negative"
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = build_user_run_pack(
                repo_root=REPO_ROOT,
                target_id="reference-black-hole",
                velocity_id="conditional-45",
                run_id=run_id,
                mode="dual",
                seed=1,
                output_dir=Path(tmp_dir) / run_id,
            )
            summary_path = Path(result["output_dir"]) / "USER_RUN_SUMMARY.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["blocked_claims"] = ["mission feasible"]
            summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            runner_payload = {
                "run_id": run_id,
                "output_dir": result["output_dir"],
                "summary_sha256": result["meta"]["summary_sha256"],
                "determinism": {"verdict": "PASS"},
                "verdict": "PASS",
            }

            errors = validate_pack(REPO_ROOT, Path(result["output_dir"]), runner_payload)

            self.assertTrue(errors)
            self.assertTrue(any("flight ready" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
