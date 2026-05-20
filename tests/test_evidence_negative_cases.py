from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "ci" / "evidence_validate.py"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _copy_contract_files(target_root: Path) -> None:
    (target_root / "mission").mkdir(parents=True, exist_ok=True)
    (target_root / "engineering").mkdir(parents=True, exist_ok=True)
    for name in [
        "EVIDENCE_SCHEMA_v1.json",
        "EVIDENCE_REGISTRY_v1.json",
        "MISSION_SCHEMA_v1.json",
        "UNCERTAINTY_MODEL_v1.json",
    ]:
        shutil.copyfile(REPO_ROOT / "mission" / name, target_root / "mission" / name)
    (target_root / "engineering" / "CHANGELOG.md").write_text("## baseline\n", encoding="utf-8")


def _init_git_repo(repo_root: Path) -> str:
    _run(["git", "init"], cwd=repo_root)
    _run(["git", "config", "user.email", "tests@example.com"], cwd=repo_root)
    _run(["git", "config", "user.name", "Evidence Tests"], cwd=repo_root)
    _run(["git", "add", "."], cwd=repo_root)
    commit = _run(["git", "commit", "-m", "fixture"], cwd=repo_root)
    if commit.returncode != 0:
        raise AssertionError(commit.stdout + commit.stderr)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()


class EvidenceNegativeCasesTests(unittest.TestCase):
    def _with_fixture(self) -> tuple[Path, str]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        repo = Path(temp.name)
        _copy_contract_files(repo)
        head = _init_git_repo(repo)
        return repo, head

    def test_realistic_parameter_with_trust_d_fails(self) -> None:
        repo, head = self._with_fixture()
        registry_path = repo / "mission" / "EVIDENCE_REGISTRY_v1.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for claim in registry["parameter_claims"]:
            if claim["mode"] == "realistic":
                claim["trust_grade"] = "D"
                break
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        proc = _run(
            [
                sys.executable,
                str(VALIDATOR),
                "--repo-root",
                str(repo),
                "--strict",
                "--base",
                head,
                "--head",
                head,
            ],
            cwd=repo,
        )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("realistic mode cannot use trust_grade D", proc.stdout)

    def test_missing_evidence_source_id_fails(self) -> None:
        repo, head = self._with_fixture()
        registry_path = repo / "mission" / "EVIDENCE_REGISTRY_v1.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["parameter_claims"][0]["evidence_source_ids"] = []
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        proc = _run(
            [
                sys.executable,
                str(VALIDATOR),
                "--repo-root",
                str(repo),
                "--strict",
                "--base",
                head,
                "--head",
                head,
            ],
            cwd=repo,
        )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("evidence_source_ids must be non-empty array", proc.stdout)

    def test_dangling_evidence_source_id_fails(self) -> None:
        repo, head = self._with_fixture()
        registry_path = repo / "mission" / "EVIDENCE_REGISTRY_v1.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["parameter_claims"][0]["evidence_source_ids"] = ["SRC-DOES-NOT-EXIST"]
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

        proc = _run(
            [
                sys.executable,
                str(VALIDATOR),
                "--repo-root",
                str(repo),
                "--strict",
                "--base",
                head,
                "--head",
                head,
            ],
            cwd=repo,
        )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("unknown source", proc.stdout)


if __name__ == "__main__":
    unittest.main()
