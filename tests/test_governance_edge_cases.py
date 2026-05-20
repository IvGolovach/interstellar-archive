from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.ci.governance.parsers import parse_changelog, parse_checksums_file


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = REPO_ROOT / "scripts" / "ci" / "governance_check.py"
POLICY_PATH = REPO_ROOT / "engineering" / "governance_policy.yaml"


class GovernanceEdgeCaseTests(unittest.TestCase):
    def test_multiline_changelog_entry(self) -> None:
        text = (
            "# Engineering Changelog\n\n"
            "## 2026-02-17 — Title\n"
            "- Date (UTC): 2026-02-17T00:00:00Z\n"
            "- Commit: 1234567\n"
            "- Type: infra\n"
            "- Summary: line1\n"
            "  line2\n"
            "- Link: https://github.com/org/repo/commit/1234567\n"
            "- Rationale: part1\n"
            "  part2\n"
        )
        parsed = parse_changelog(
            text,
            heading_regex=r"^##\s+\d{4}-\d{2}-\d{2}\s+—\s+.+$",
            required_fields=["Date (UTC)", "Commit", "Type", "Summary", "Link", "Rationale"],
            allowed_types=["infra"],
            link_regex=r"^https://github\.com/.+/commit/[0-9a-f]{7,40}$",
        )
        self.assertFalse(parsed.errors)
        self.assertIn("line2", parsed.entries[0].fields["Summary"])

    def test_extra_whitespace_and_crlf(self) -> None:
        text = (
            "# Engineering Changelog\r\n\r\n"
            "## 2026-02-17 — Title\r\n"
            "- Date (UTC):   2026-02-17T00:00:00Z\r\n"
            "- Commit: 1234567\r\n"
            "- Type: infra\r\n"
            "- Summary: ok\r\n"
            "- Link: https://github.com/org/repo/commit/1234567\r\n"
            "- Rationale: ok\r\n"
        )
        parsed = parse_changelog(
            text,
            heading_regex=r"^##\s+\d{4}-\d{2}-\d{2}\s+—\s+.+$",
            required_fields=["Date (UTC)", "Commit", "Type", "Summary", "Link", "Rationale"],
            allowed_types=["infra"],
            link_regex=r"^https://github\.com/.+/commit/[0-9a-f]{7,40}$",
        )
        self.assertFalse(parsed.errors)

        checksums, errors = parse_checksums_file(
            "a" * 64 + "  artifacts/claim_values.json\r\n" + "b" * 64 + "  artifacts/claims_table.csv\r\n"
        )
        self.assertFalse(errors)
        self.assertEqual(2, len(checksums))

    def test_large_changelog(self) -> None:
        entries = ["# Engineering Changelog\n"]
        for i in range(200):
            sha = f"{i:07x}"
            entries.append(
                "\n".join(
                    [
                        f"## 2026-02-17 — Entry {i}",
                        "- Date (UTC): 2026-02-17T00:00:00Z",
                        f"- Commit: {sha}",
                        "- Type: infra",
                        "- Summary: ok",
                        f"- Link: https://github.com/org/repo/commit/{sha}",
                        "- Rationale: ok",
                        "",
                    ]
                )
            )
        parsed = parse_changelog(
            "\n".join(entries),
            heading_regex=r"^##\s+\d{4}-\d{2}-\d{2}\s+—\s+.+$",
            required_fields=["Date (UTC)", "Commit", "Type", "Summary", "Link", "Rationale"],
            allowed_types=["infra"],
            link_regex=r"^https://github\.com/.+/commit/[0-9a-f]{7,40}$",
        )
        self.assertFalse(parsed.errors)
        self.assertEqual(200, len(parsed.entries))

    def test_encoding_issue_returns_internal_error(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            changelog = repo / "engineering" / "CHANGELOG.md"
            changelog.write_bytes(b"\xff\xfe\xfd")
            self._commit_all(repo, "break encoding")
            head = self._head(repo)
            result = self._run(repo, base, head)
            self.assertEqual(3, result.returncode)
            self.assertIn("INTERNAL ERROR", result.stdout)

    def test_missing_file_violation(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._git(repo, "rm", "engineering/DECISIONS.md")
            self._write(repo / "engineering" / "ARCHITECTURE.md", self._architecture_doc("x"))
            self._commit_all(repo, "remove decisions and touch arch")
            head = self._head(repo)
            result = self._run(repo, base, head)
            self.assertEqual(2, result.returncode)
            self.assertIn("decisions_missing", result.stdout)

    def _run(self, repo: Path, base: str, head: str) -> subprocess.CompletedProcess[str]:
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
            ],
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "LANG": "C", "LC_ALL": "C"},
        )

    def _temp_repo(self):
        class RepoContext:
            def __init__(self, outer: "GovernanceEdgeCaseTests"):
                self.outer = outer
                self.tmp = tempfile.TemporaryDirectory()

            def __enter__(self) -> Path:
                repo = Path(self.tmp.name)
                self.outer._git(repo, "init")
                self.outer._git(repo, "config", "user.email", "test@example.com")
                self.outer._git(repo, "config", "user.name", "test")
                self.outer._seed(repo)
                self.outer._commit_all(repo, "init")
                return repo

            def __exit__(self, exc_type, exc, tb):
                self.tmp.cleanup()
                return False

        return RepoContext(self)

    def _seed(self, repo: Path) -> None:
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
                "- Summary: ok\n"
                "- Link: https://github.com/org/repo/commit/1234567\n"
                "- Rationale: ok\n"
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
                "### Options considered\nx\n\n"
                "### Decision\nx\n\n"
                "### Rationale\nx\n\n"
                "### Trade-offs\nx\n\n"
                "### Future reconsideration trigger\nx\n"
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
            "# Governance\n\n## Mandatory Rules\nx\n\n## Future Contributors Policy\nx\n",
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


if __name__ == "__main__":
    unittest.main()
