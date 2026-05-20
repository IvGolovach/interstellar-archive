from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = REPO_ROOT / "artifacts" / "evidence-pack-v1"


class PublicFoundationLayerTests(unittest.TestCase):
    def test_run_golden_emits_required_artifact_files(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/run_golden.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, msg=result.stdout + "\n" + result.stderr)

        required_json = [
            PACK_DIR / "metadata.json",
            PACK_DIR / "input_parameters.json",
            PACK_DIR / "output_metrics.json",
        ]
        for path in required_json:
            self.assertTrue(path.exists(), msg=str(path.relative_to(REPO_ROOT)))
            json.loads(path.read_text(encoding="utf-8"))

        self.assertTrue((PACK_DIR / "checksums.sha256").exists())

    def test_run_golden_deterministic_checksums(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/run_golden.py", "--verify-deterministic"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("Golden run PASS", result.stdout)

    def test_run_golden_does_not_mutate_tracked_evidence_pack(self) -> None:
        tracked_files = [
            REPO_ROOT / "artifacts/evidence-pack-v1/metadata.json",
            REPO_ROOT / "artifacts/evidence-pack-v1/input_parameters.json",
            REPO_ROOT / "artifacts/evidence-pack-v1/output_metrics.json",
            REPO_ROOT / "artifacts/evidence-pack-v1/checksums.sha256",
        ]
        before = {path: path.read_bytes() for path in tracked_files}
        subprocess.run(["python3", "scripts/run_golden.py"], cwd=REPO_ROOT, check=True)
        for path in tracked_files:
            self.assertEqual(before[path], path.read_bytes(), msg=str(path.relative_to(REPO_ROOT)))

    def test_benchmark_compare_passes_on_current_baseline(self) -> None:
        subprocess.run(["python3", "scripts/run_golden.py"], cwd=REPO_ROOT, check=True)
        result = subprocess.run(
            ["python3", "scripts/benchmark_compare.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("Summary: total=", result.stdout)

    def test_required_public_docs_exist(self) -> None:
        for path in [
            REPO_ROOT / "ARCHITECTURE.md",
            REPO_ROOT / "INVARIANTS.md",
            REPO_ROOT / "LIMITATIONS.md",
            REPO_ROOT / "REPRODUCIBILITY.md",
        ]:
            self.assertTrue(path.exists(), msg=str(path.relative_to(REPO_ROOT)))
            self.assertTrue(path.read_text(encoding="utf-8").strip(), msg=str(path.relative_to(REPO_ROOT)))


if __name__ == "__main__":
    unittest.main()
