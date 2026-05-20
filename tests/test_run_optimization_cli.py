from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import run_optimization


REPO_ROOT = Path(__file__).resolve().parents[1]


class RunOptimizationCliTests(unittest.TestCase):
    def test_cli_rejects_speculative_mode(self) -> None:
        argv = [
            "run_optimization.py",
            "--mode",
            "speculative",
        ]
        with patch("sys.argv", argv):
            code = run_optimization.main()
        self.assertEqual(run_optimization.EXIT_VIOLATION, code)

    def test_cli_runs_and_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = Path(tmp_dir) / "summary.txt"
            argv = [
                "run_optimization.py",
                "--mode",
                "realistic",
                "--samples",
                "16",
                "--seed",
                "42",
                "--run-id",
                "cli-test",
                "--output-root",
                tmp_dir,
                "--verify-deterministic",
                "--output",
                str(output_file),
            ]
            with patch("sys.argv", argv):
                code = run_optimization.main()

            self.assertEqual(run_optimization.EXIT_PASS, code)
            self.assertTrue(output_file.exists())
            run_dir = Path(tmp_dir) / "cli-test"
            self.assertTrue((run_dir / "meta.json").exists())
            self.assertTrue((run_dir / "DETERMINISM_CHECK.json").exists())


if __name__ == "__main__":
    unittest.main()
