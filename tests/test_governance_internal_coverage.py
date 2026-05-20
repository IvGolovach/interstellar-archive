from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.ci.governance.config import GovernanceConfigError, load_policy
from scripts.ci.governance.report import render_json, render_text
from scripts.ci.governance.rules import run_governance_checks


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "engineering" / "governance_policy.yaml"


class GovernanceInternalCoverageTests(unittest.TestCase):
    def test_empty_range_pass(self) -> None:
        with self._temp_repo() as repo:
            head = self._head(repo)
            result = run_governance_checks(repo, head, head)
            self.assertEqual("PASS", result.status)
            self.assertIn("No files changed in commit range.", result.notes)

    def test_core_change_violation_and_fix(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(repo / "models" / "x.py", "x=1\n")
            self._commit_all(repo, "core")
            head = self._head(repo)
            fail = run_governance_checks(repo, base, head)
            self.assertEqual("FAIL", fail.status)
            self.assertTrue(any(v.rule_id == "changelog_required" for v in fail.violations))

            self._append_changelog(repo, self._head(repo))
            self._commit_all(repo, "changelog")
            fixed = run_governance_checks(repo, base, self._head(repo))
            self.assertEqual("PASS", fixed.status)

    def test_architecture_decisions_violation_and_fix(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(repo / "engineering" / "ARCHITECTURE.md", self._architecture_doc("changed"))
            self._commit_all(repo, "arch")
            fail = run_governance_checks(repo, base, self._head(repo))
            self.assertTrue(any(v.rule_id == "decisions_required" for v in fail.violations))

            self._append_decision(repo, self._head(repo), "D-0002")
            self._commit_all(repo, "decision")
            passed = run_governance_checks(repo, base, self._head(repo))
            self.assertEqual("PASS", passed.status)

    def test_changelog_append_only_violation(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(
                repo / "engineering" / "CHANGELOG.md",
                "# Engineering Changelog\n\n## 2026-02-17 — New\n- Date (UTC): 2026-02-17T00:00:00Z\n- Commit: 1234567\n- Type: infra\n- Summary: new\n- Link: https://github.com/org/repo/commit/1234567\n- Rationale: new\n",
            )
            self._commit_all(repo, "replace changelog")
            result = run_governance_checks(repo, base, self._head(repo))
            self.assertTrue(any(v.rule_id == "changelog_append_only" for v in result.violations))

    def test_artifact_checksum_rules(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(repo / "artifacts" / "claim_values.json", "{\"x\":1}\n")
            self._commit_all(repo, "artifact without checksum update")
            result = run_governance_checks(repo, base, self._head(repo))
            self.assertTrue(
                any(v.rule_id == "artifact_checksums_update_required" for v in result.violations)
            )

    def test_engineering_sections_violation(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(repo / "engineering" / "GOVERNANCE.md", "# Governance\n\n## Mandatory Rules\nx\n")
            self._commit_all(repo, "remove section")
            result = run_governance_checks(repo, base, self._head(repo))
            self.assertTrue(any(v.rule_id == "engineering_sections" for v in result.violations))

    def test_report_renderers(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._write(repo / "models" / "x.py", "x=1\n")
            self._commit_all(repo, "core")
            result = run_governance_checks(repo, base, self._head(repo))
            text = render_text(result)
            payload = json.loads(render_json(result))
            self.assertIn("FAIL: governance violation", text)
            self.assertEqual("FAIL", payload["status"])

    def test_policy_load_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "engineering").mkdir(parents=True, exist_ok=True)
            (repo / "engineering" / "governance_policy.yaml").write_text("{bad", encoding="utf-8")
            with self.assertRaises(GovernanceConfigError):
                load_policy(repo)

    def test_policy_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(GovernanceConfigError):
                load_policy(Path(tmp))

    def test_file_exists_failure_paths(self) -> None:
        with self._temp_repo() as repo:
            base = self._head(repo)
            self._git(repo, "rm", "engineering/CHANGELOG.md")
            self._write(repo / "models" / "x.py", "x=1\n")
            self._commit_all(repo, "remove changelog and core")
            result = run_governance_checks(repo, base, self._head(repo))
            self.assertTrue(any(v.rule_id == "engineering_files_required" for v in result.violations))

    def _temp_repo(self):
        class RepoContext:
            def __init__(self, outer: "GovernanceInternalCoverageTests"):
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
        self._write(repo / "engineering" / "ARCHITECTURE.md", self._architecture_doc("x"))
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
        self._write(repo / "models" / "placeholder.py", "x=1\n")
        self._write(repo / "artifacts" / "claim_values.json", "{}\n")
        self._write(repo / "artifacts" / "claims_table.csv", "x\n")
        self._write(repo / "artifacts" / "traceability_matrix.csv", "x\n")
        self._write(repo / "artifacts" / "claims_report.md", "x\n")
        self._write(
            repo / "artifacts" / "evidence-pack-v1" / "checksums.sha256",
            (
                f"{self._sha(repo / 'artifacts' / 'claim_values.json')}  artifacts/claim_values.json\n"
                f"{self._sha(repo / 'artifacts' / 'claims_table.csv')}  artifacts/claims_table.csv\n"
                f"{self._sha(repo / 'artifacts' / 'traceability_matrix.csv')}  artifacts/traceability_matrix.csv\n"
                f"{self._sha(repo / 'artifacts' / 'claims_report.md')}  artifacts/claims_report.md\n"
            ),
        )

    def _append_changelog(self, repo: Path, commit_sha: str) -> None:
        path = repo / "engineering" / "CHANGELOG.md"
        current = path.read_text(encoding="utf-8")
        current += (
            "\n## 2026-02-17 — Update\n"
            "- Date (UTC): 2026-02-17T00:00:00Z\n"
            f"- Commit: {commit_sha}\n"
            "- Type: infra\n"
            "- Summary: update\n"
            f"- Link: https://github.com/org/repo/commit/{commit_sha}\n"
            "- Rationale: update\n"
        )
        self._write(path, current)

    def _append_decision(self, repo: Path, commit_sha: str, decision_id: str) -> None:
        path = repo / "engineering" / "DECISIONS.md"
        current = path.read_text(encoding="utf-8")
        current += (
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
        self._write(path, current)

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
    def _sha(path: Path) -> str:
        import hashlib

        return hashlib.sha256(path.read_bytes()).hexdigest()

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

