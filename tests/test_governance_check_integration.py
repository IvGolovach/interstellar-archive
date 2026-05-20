from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = REPO_ROOT / "scripts" / "ci" / "governance_check.py"
POLICY_PATH = REPO_ROOT / "engineering" / "governance_policy.yaml"


class GovernanceIntegrationTests(unittest.TestCase):
    def test_core_change_without_changelog_fails(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(repo / "models" / "core.py", "print('v1')\n")
            self._commit_all(repo, "core change")
            head = self._head(repo)
            result = self._run_check(repo, base, head)
            self.assertEqual(2, result.returncode)
            self.assertIn("changelog_required", result.stdout)

    def test_core_change_with_changelog_passes(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(repo / "models" / "core.py", "print('v1')\n")
            self._commit_all(repo, "core change")
            core_sha = self._head(repo)
            self._append_changelog_entry(repo, commit_sha=core_sha, title="Core update")
            self._commit_all(repo, "changelog update")
            head = self._head(repo)
            result = self._run_check(repo, base, head)
            self.assertEqual(0, result.returncode)
            self.assertIn("PASS", result.stdout)

    def test_architecture_change_without_decisions_fails(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(repo / "engineering" / "ARCHITECTURE.md", self._architecture_doc("changed"))
            self._commit_all(repo, "arch change")
            head = self._head(repo)
            result = self._run_check(repo, base, head)
            self.assertEqual(2, result.returncode)
            self.assertIn("decisions_required", result.stdout)

    def test_architecture_change_with_decisions_passes(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(repo / "engineering" / "ARCHITECTURE.md", self._architecture_doc("changed"))
            self._commit_all(repo, "arch change")
            arch_sha = self._head(repo)
            self._append_decision(repo, commit_sha=arch_sha, decision_id="D-0002")
            self._commit_all(repo, "decision update")
            head = self._head(repo)
            result = self._run_check(repo, base, head)
            self.assertEqual(0, result.returncode)
            self.assertIn("PASS", result.stdout)

    def test_renamed_files_detected(self) -> None:
        with self._temp_repo() as repo:
            self._write(repo / "models" / "old.py", "x=1\n")
            self._commit_all(repo, "add old")
            base = self._head(repo)
            self._git(repo, "mv", "models/old.py", "models/new.py")
            self._commit_all(repo, "rename file")
            head = self._head(repo)
            result = self._run_check(repo, base, head)
            self.assertEqual(2, result.returncode)
            self.assertIn("changelog_required", result.stdout)

    def test_deleted_files_detected(self) -> None:
        with self._temp_repo() as repo:
            self._write(repo / "models" / "gone.py", "x=1\n")
            self._commit_all(repo, "add gone")
            base = self._head(repo)
            self._git(repo, "rm", "models/gone.py")
            self._commit_all(repo, "delete gone")
            head = self._head(repo)
            result = self._run_check(repo, base, head)
            self.assertEqual(2, result.returncode)
            self.assertIn("changelog_required", result.stdout)

    def test_non_ascii_paths_handled(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            unicode_name = "\u00e9tude.py"
            self._write(repo / "models" / unicode_name, "x=1\n")
            self._commit_all(repo, "unicode path")
            head = self._head(repo)
            result = self._run_check(repo, base, head, fmt="json")
            self.assertEqual(2, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual("FAIL", payload["status"])

    def test_empty_commit_range_passes_with_message(self) -> None:
        with self._temp_repo() as repo:
            head = self._head(repo)
            result = self._run_check(repo, head, head)
            self.assertEqual(0, result.returncode)
            self.assertIn("No files changed in commit range", result.stdout)

    def test_corrupted_changelog_format_fails(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(
                repo / "engineering" / "CHANGELOG.md",
                "# Engineering Changelog\n\n## broken heading\n- Commit: xyz\n",
            )
            self._commit_all(repo, "break changelog")
            head = self._head(repo)
            result = self._run_check(repo, base, head)
            self.assertEqual(2, result.returncode)
            self.assertIn("changelog_structure", result.stdout)

    def test_json_output_written(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(repo / "models" / "core.py", "print('v1')\n")
            self._commit_all(repo, "core change")
            head = self._head(repo)
            out_path = repo / "governance.json"
            result = subprocess.run(
                [
                    "python3",
                    str(CLI_PATH),
                    "--base",
                    base,
                    "--head",
                    head,
                    "--repo-root",
                    str(repo),
                    "--format",
                    "json",
                    "--output",
                    str(out_path),
                ],
                text=True,
                capture_output=True,
                check=False,
                env={**os.environ, "LANG": "C", "LC_ALL": "C"},
            )
            self.assertEqual(2, result.returncode)
            self.assertTrue(out_path.exists())
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual("FAIL", payload["status"])

    def _run_check(self, repo: Path, base: str, head: str, fmt: str = "text") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(CLI_PATH),
                "--base",
                base,
                "--head",
                head,
                "--repo-root",
                str(repo),
                "--format",
                fmt,
            ],
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "LANG": "C", "LC_ALL": "C"},
        )

    def _temp_repo(self):
        class RepoContext:
            def __init__(self, outer: "GovernanceIntegrationTests"):
                self.outer = outer
                self.tmp = tempfile.TemporaryDirectory()

            def __enter__(self) -> Path:
                repo = Path(self.tmp.name)
                self.outer._git(repo, "init")
                self.outer._git(repo, "config", "user.email", "test@example.com")
                self.outer._git(repo, "config", "user.name", "test")
                self.outer._seed_governance(repo)
                self.outer._commit_all(repo, "initial")
                return repo

            def __exit__(self, exc_type, exc, tb):
                self.tmp.cleanup()
                return False

        return RepoContext(self)

    def _seed_governance(self, repo: Path) -> None:
        (repo / "engineering").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(POLICY_PATH, repo / "engineering" / "governance_policy.yaml")
        self._write(
            repo / "engineering" / "CHANGELOG.md",
            (
                "# Engineering Changelog\n\n"
                "## 2026-02-17 — Initial\n"
                "- Date (UTC): 2026-02-17T00:00:00Z\n"
                "- Commit: 1234567\n"
                "- Type: infra\n"
                "- Summary: initial\n"
                "- Link: https://github.com/org/repo/commit/1234567\n"
                "- Rationale: initial\n"
            ),
        )
        self._write(
            repo / "engineering" / "DECISIONS.md",
            (
                "# Decisions\n\n"
                "## D-0001 — Initial\n\n"
                "Status: accepted\n"
                "Date: 2026-02-17T00:00:00Z\n"
                "Author: Test\n"
                "Related commits: 1234567\n\n"
                "### Context\nx\n\n"
                "### Options considered\n1\n\n"
                "### Decision\n2\n\n"
                "### Rationale\n3\n\n"
                "### Trade-offs\n4\n\n"
                "### Future reconsideration trigger\n5\n"
            ),
        )
        self._write(
            repo / "engineering" / "ARCHITECTURE.md",
            self._architecture_doc("x"),
        )
        self._write(
            repo / "engineering" / "REPRODUCIBILITY.md",
            (
                "# Reproducibility Protocol\n\n"
                "## 1. How to clone and build\nx\n"
                "## 2. Deterministic setup instructions\nx\n"
                "## 3. Exact dependency versions\nx\n"
                "## 4. How to reproduce a full run\nx\n"
                "## 5. Expected outputs\nx\n"
                "## 6. How to verify outputs integrity\nx\n"
            ),
        )
        self._write(
            repo / "engineering" / "GOVERNANCE.md",
            (
                "# Governance\n\n"
                "## Mandatory Rules\nx\n"
                "## Future Contributors Policy\nx\n"
            ),
        )
        self._write(repo / "models" / "placeholder.py", "x = 1\n")

    def _append_changelog_entry(self, repo: Path, commit_sha: str, title: str) -> None:
        path = repo / "engineering" / "CHANGELOG.md"
        content = path.read_text(encoding="utf-8")
        content += (
            f"\n## 2026-02-17 — {title}\n"
            f"- Date (UTC): 2026-02-17T00:00:00Z\n"
            f"- Commit: {commit_sha}\n"
            "- Type: infra\n"
            "- Summary: update\n"
            f"- Link: https://github.com/org/repo/commit/{commit_sha}\n"
            "- Rationale: update\n"
        )
        self._write(path, content)

    def _append_decision(self, repo: Path, commit_sha: str, decision_id: str) -> None:
        path = repo / "engineering" / "DECISIONS.md"
        content = path.read_text(encoding="utf-8")
        content += (
            f"\n## {decision_id} — Update\n\n"
            "Status: accepted\n"
            "Date: 2026-02-17T00:00:00Z\n"
            "Author: Test\n"
            f"Related commits: {commit_sha}\n\n"
            "### Context\nx\n\n"
            "### Options considered\n1\n\n"
            "### Decision\n2\n\n"
            "### Rationale\n3\n\n"
            "### Trade-offs\n4\n\n"
            "### Future reconsideration trigger\n5\n"
        )
        self._write(path, content)

    @staticmethod
    def _architecture_doc(value: str) -> str:
        return (
            "# Architecture Contract\n\n"
            f"## 1. System Overview\n{value}\n"
            "## 2. Core Invariants\nx\n"
            "## 3. Data Model (high-level)\nx\n"
            "## 4. Critical Failure Modes\nx\n"
            "## 5. Trust Assumptions\nx\n"
            "## 6. What This System Explicitly Does NOT Guarantee\nx\n"
        )

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _git(repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout

    def _commit_all(self, repo: Path, message: str) -> None:
        self._git(repo, "add", "-A")
        self._git(repo, "commit", "-m", message)

    def _head(self, repo: Path) -> str:
        return self._git(repo, "rev-parse", "HEAD").strip()


if __name__ == "__main__":
    unittest.main()
