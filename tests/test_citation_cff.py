from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from scripts.ci import validate_citation_cff


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "ci" / "validate_citation_cff.py"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


class CitationCffTests(unittest.TestCase):
    def test_validator_passes_on_repo_file(self) -> None:
        proc = _run([sys.executable, str(VALIDATOR)], cwd=REPO_ROOT)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("PASS", proc.stdout)

    def test_validate_detects_missing_required_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            citation = root / "CITATION.cff"
            version = root / "VERSION"
            citation.write_text(
                json.dumps(
                    {
                        "cff-version": "1.2.0",
                        "message": "x",
                        # title missing
                        "authors": [{"name": "Author"}],
                        "version": "1.0.0",
                        "date-released": "2026-02-18",
                        "url": "https://example.com",
                        "license": "CC-BY-4.0",
                        "repository-code": "https://example.com/repo",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            version.write_text("1.0.0\n", encoding="utf-8")
            errors = validate_citation_cff.validate(citation, version)
            self.assertTrue(any("missing required key: title" in item for item in errors))

    def test_validate_detects_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            citation = root / "CITATION.cff"
            version = root / "VERSION"
            citation.write_text(
                json.dumps(
                    {
                        "cff-version": "1.2.0",
                        "message": "x",
                        "title": "T",
                        "authors": [{"name": "Author"}],
                        "version": "1.0.1",
                        "date-released": "2026-02-18",
                        "url": "https://example.com",
                        "license": "CC-BY-4.0",
                        "repository-code": "https://example.com/repo",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            version.write_text("1.0.0\n", encoding="utf-8")
            errors = validate_citation_cff.validate(citation, version)
            self.assertTrue(any("version mismatch" in item for item in errors))


if __name__ == "__main__":
    unittest.main()

