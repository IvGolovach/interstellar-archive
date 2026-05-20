from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from scripts.ci import validate_model_version


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "ci" / "validate_model_version.py"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


class ModelVersionTests(unittest.TestCase):
    def test_validator_passes_on_repo_file(self) -> None:
        proc = _run([sys.executable, str(VALIDATOR)], cwd=REPO_ROOT)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("PASS", proc.stdout)

    def test_validate_detects_missing_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "MODEL_VERSION.json"
            payload = dict(validate_model_version.EXPECTED_MODEL_VERSION)
            del payload["schema_version"]
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            errors = validate_model_version.validate(path)
            self.assertTrue(any("missing required key: schema_version" in item for item in errors))

    def test_validate_detects_wrong_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "MODEL_VERSION.json"
            payload = dict(validate_model_version.EXPECTED_MODEL_VERSION)
            payload["engine_version"] = "v9"
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            errors = validate_model_version.validate(path)
            self.assertTrue(any("engine_version must be 'v1'" in item for item in errors))


if __name__ == "__main__":
    unittest.main()

