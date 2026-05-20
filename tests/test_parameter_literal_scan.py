from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCANNER = REPO_ROOT / "scripts/ci/parameter_literal_scan.py"


def copy_scan_fixture(tmp: Path) -> None:
    for rel in [
        "scripts/benchmark_compare.py",
        "scripts/benchmark_drift_guard.py",
        "mission/baseline/constants.py",
        "mission/baseline/model.py",
        "mission/baseline/output.py",
        "mission/BASELINE_SCENARIO_v1.json",
        "mission/UNCERTAINTY_MODEL_v1.json",
        "mission/MISSION_SCHEMA_v1.json",
        "parameters/registry/parameter_registry.v1.json",
        "parameters/registry/parameter_literal_scope.v1.json",
    ]:
        src = REPO_ROOT / rel
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)


class ParameterLiteralScanTests(unittest.TestCase):
    def test_current_repo_scan_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCANNER), "--repo-root", str(REPO_ROOT), "--strict", "--format", "json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual("PASS", payload["status"])
        self.assertEqual(0, payload["totals"]["unmatched_count"])
        self.assertEqual([], payload["scope_contract"]["undeclared_paths"]["python"])
        self.assertEqual([], payload["scope_contract"]["undeclared_paths"]["json"])
        self.assertIn("mission/dag", payload["scope"]["watched_roots"]["python"])
        self.assertIn("mission/optimization", payload["scope"]["watched_roots"]["python"])
        self.assertIn("mission/dag/runner_v1.py", payload["scope"]["excluded"]["python"])
        self.assertIn("rationale", payload["scope"]["excluded"]["python"]["mission/dag/runner_v1.py"])

    def test_missing_registry_ref_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            copy_scan_fixture(tmp)

            registry_path = tmp / "parameters/registry/parameter_registry.v1.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            target = next(item for item in registry["parameters"] if item["code_refs"])
            target["code_refs"] = []
            registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(SCANNER), "--repo-root", str(tmp), "--strict", "--format", "json"],
                cwd=tmp,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual("FAIL", payload["status"])
            self.assertGreater(payload["totals"]["unmatched_count"], 0)

    def test_new_dag_or_optimization_file_must_be_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            copy_scan_fixture(tmp)

            for rel in [
                "mission/dag/new_orchestration_constant.py",
                "mission/optimization/new_scoring_weight.py",
            ]:
                new_path = tmp / rel
                new_path.parent.mkdir(parents=True, exist_ok=True)
                new_path.write_text("RETRY_WINDOW_SECONDS = 30\n", encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(SCANNER), "--repo-root", str(tmp), "--strict", "--format", "json"],
                cwd=tmp,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual("FAIL", payload["status"])
            self.assertEqual(
                [
                    "mission/dag/new_orchestration_constant.py",
                    "mission/optimization/new_scoring_weight.py",
                ],
                payload["scope_contract"]["undeclared_paths"]["python"],
            )


if __name__ == "__main__":
    unittest.main()
