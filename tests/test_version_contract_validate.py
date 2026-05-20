from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from scripts.ci import version_contract_validate


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "ci" / "version_contract_validate.py"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _git(repo: Path, *args: str) -> None:
    proc = _run(["git", *args], cwd=repo)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stdout}\n{proc.stderr}")


def _write_contract_files(repo: Path, version: str, citation_version: str, signals_version: str) -> None:
    (repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    (repo / "CITATION.cff").write_text(
        json.dumps(
            {
                "cff-version": "1.2.0",
                "message": "x",
                "title": "T",
                "authors": [{"name": "Author"}],
                "version": citation_version,
                "date-released": "2026-02-19",
                "url": "https://example.com",
                "license": "CC-BY-4.0",
                "repository-code": "https://example.com/repo",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    artifacts = repo / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "research_signals.json").write_text(
        json.dumps({"version": signals_version}, indent=2) + "\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("# T\nCurrent release: see Releases tab.\n", encoding="utf-8")


def _init_temp_repo(version: str = "0.2.1", citation_version: str = "0.2.1", signals_version: str = "v0.2.1") -> Path:
    tmp_dir = Path(tempfile.mkdtemp())
    _git(tmp_dir, "init")
    _git(tmp_dir, "config", "user.name", "Test User")
    _git(tmp_dir, "config", "user.email", "test@example.com")
    _git(tmp_dir, "config", "tag.gpgSign", "false")
    _write_contract_files(tmp_dir, version, citation_version, signals_version)
    _git(tmp_dir, "add", ".")
    _git(tmp_dir, "commit", "-m", "init")
    return tmp_dir


class VersionContractValidateTests(unittest.TestCase):
    def test_validator_passes_on_repo_file(self) -> None:
        proc = _run([sys.executable, str(VALIDATOR), "--strict"], cwd=REPO_ROOT)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("PASS", proc.stdout)

    def test_fails_when_version_changes_without_citation_sync(self) -> None:
        repo = _init_temp_repo(version="0.2.1", citation_version="0.2.0", signals_version="v0.2.1")
        errors = version_contract_validate.validate(repo)
        self.assertTrue(any("CITATION.cff version mismatch" in item for item in errors))

    def test_fails_when_citation_changes_without_version_sync(self) -> None:
        repo = _init_temp_repo(version="0.2.1", citation_version="0.2.2", signals_version="v0.2.1")
        errors = version_contract_validate.validate(repo)
        self.assertTrue(any("CITATION.cff version mismatch" in item for item in errors))

    def test_fails_when_head_semver_tag_does_not_match_version(self) -> None:
        repo = _init_temp_repo()
        _git(repo, "tag", "v0.2.0")
        errors = version_contract_validate.validate(repo)
        self.assertTrue(any("HEAD semver tag mismatch" in item for item in errors))

    def test_fails_for_narrative_tag_in_version_namespace(self) -> None:
        repo = _init_temp_repo()
        _git(repo, "tag", "v1.2")
        errors = version_contract_validate.validate(repo)
        self.assertTrue(any("invalid version-namespace tags" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
