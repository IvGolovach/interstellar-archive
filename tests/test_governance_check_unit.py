from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ci.governance.config import GovernanceConfigError, load_policy
from scripts.ci.governance.config import (
    ArtifactsPolicy,
    ChangelogPolicy,
    DecisionsPolicy,
    GovernancePolicy,
    PathsPolicy,
)
from scripts.ci.governance.git_utils import (
    ChangedFile,
    FileDecodeError,
    GitCommandError,
    commit_range,
    parse_name_status_z,
    run_git,
)
from scripts.ci.governance.parsers import (
    parse_changelog,
    parse_checksums_file,
    parse_decisions,
    extract_headings,
)
from scripts.ci.governance.report import render_text
from scripts.ci.governance.rules import (
    GovernanceResult,
    RuleContext,
    rule_architecture_requires_decisions,
    rule_artifact_checksums,
    rule_changelog_append_only,
    rule_changelog_structure_and_sha,
    rule_core_requires_changelog,
    rule_decisions_structure,
    rule_engineering_files_exist,
    rule_engineering_sections,
)


def _policy() -> GovernancePolicy:
    return GovernancePolicy(
        version="2",
        paths=PathsPolicy(
            core_prefixes=["src/", "core/", "models/", "scripts/"],
            architecture_files=[
                "engineering/ARCHITECTURE.md",
                "engineering/GOVERNANCE.md",
                "engineering/REPRODUCIBILITY.md",
            ],
            changelog="engineering/CHANGELOG.md",
            decisions="engineering/DECISIONS.md",
            engineering_prefix="engineering/",
            required_engineering_files=[
                "engineering/CHANGELOG.md",
                "engineering/DECISIONS.md",
                "engineering/ARCHITECTURE.md",
                "engineering/REPRODUCIBILITY.md",
                "engineering/GOVERNANCE.md",
            ],
        ),
        changelog=ChangelogPolicy(
            required_fields=["Date (UTC)", "Commit", "Type", "Summary", "Link", "Rationale"],
            allowed_types=["feature", "fix", "research", "infra", "doc"],
            link_regex=r"^https://github\.com/.+/commit/[0-9a-f]{7,40}$",
            heading_regex=r"^##\s+\d{4}-\d{2}-\d{2}\s+—\s+.+$",
        ),
        decisions=DecisionsPolicy(
            entry_heading_regex=r"^##\s+D-\d{4}\s+—\s+.+$",
            required_meta_fields=["Status", "Date", "Author", "Related commits"],
            allowed_statuses=["accepted", "rejected", "superseded"],
            required_sections=[
                "Context",
                "Options considered",
                "Decision",
                "Rationale",
                "Trade-offs",
                "Future reconsideration trigger",
            ],
        ),
        engineering_sections={
            "engineering/ARCHITECTURE.md": ["System Overview"],
            "engineering/REPRODUCIBILITY.md": ["How to clone and build"],
            "engineering/GOVERNANCE.md": ["Mandatory Rules", "Future Contributors Policy"],
        },
        artifacts=ArtifactsPolicy(
            prefix="artifacts/",
            checksums_file="artifacts/evidence-pack-v1/checksums.sha256",
            tracked_outputs=["artifacts/claim_values.json"],
        ),
    )


def _context(
    touched_paths: set[str],
    changed: list[ChangedFile] | None = None,
    commit_shas: list[str] | None = None,
) -> RuleContext:
    if changed is None:
        changed = [ChangedFile(status="M", raw_status="M", path=path) for path in sorted(touched_paths)]
    if commit_shas is None:
        commit_shas = ["1111111111111111111111111111111111111111"]
    return RuleContext(
        repo_root=Path("."),
        base="base",
        head="head",
        policy=_policy(),
        changed=changed,
        commit_shas=commit_shas,
        touched_paths=touched_paths,
    )


class GovernanceUnitTests(unittest.TestCase):
    def test_parse_name_status_z_with_rename_and_delete(self) -> None:
        payload = b"R100\x00old/name.py\x00new/name.py\x00D\x00gone.txt\x00M\x00stay.txt\x00"
        parsed = parse_name_status_z(payload)
        self.assertEqual(3, len(parsed))
        self.assertEqual("R", parsed[0].status)
        self.assertEqual("old/name.py", parsed[0].old_path)
        self.assertEqual("new/name.py", parsed[0].new_path)
        self.assertEqual("D", parsed[1].status)
        self.assertEqual("gone.txt", parsed[1].path)
        self.assertIn("old/name.py", parsed[0].touched_paths())
        self.assertIn("new/name.py", parsed[0].touched_paths())

    def test_parse_name_status_malformed(self) -> None:
        with self.assertRaises(GitCommandError):
            parse_name_status_z(b"R100\x00only-old\x00")
        with self.assertRaises(GitCommandError):
            parse_name_status_z(b"M\x00")

    def test_commit_range_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._git_init(repo)
            self._write(repo / "a.txt", "a\n")
            self._git_commit(repo, "a")
            base = self._git(repo, "rev-parse", "HEAD").strip()
            self._write(repo / "b.txt", "b\n")
            self._git_commit(repo, "b")
            head = self._git(repo, "rev-parse", "HEAD").strip()
            shas = commit_range(repo, base, head)
            self.assertEqual(1, len(shas))
            self.assertEqual(head, shas[0])

    def test_run_git_error_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with self.assertRaises(GitCommandError):
                run_git(repo, ["status"])

    def test_changelog_parser_valid_and_invalid(self) -> None:
        valid = """# Engineering Changelog
## 2026-02-17 — Title
- Date (UTC): 2026-02-17T00:00:00Z
- Commit: 1234567
- Type: infra
- Summary: Good
- Link: https://github.com/org/repo/commit/1234567
- Rationale: Good
"""
        parsed = parse_changelog(
            valid,
            heading_regex=r"^##\s+\d{4}-\d{2}-\d{2}\s+—\s+.+$",
            required_fields=["Date (UTC)", "Commit", "Type", "Summary", "Link", "Rationale"],
            allowed_types=["infra"],
            link_regex=r"^https://github\.com/.+/commit/[0-9a-f]{7,40}$",
        )
        self.assertFalse(parsed.errors)
        self.assertEqual(["1234567"], parsed.commit_shas)

        invalid = valid.replace("- Type: infra", "- Type: wrong")
        invalid_parsed = parse_changelog(
            invalid,
            heading_regex=r"^##\s+\d{4}-\d{2}-\d{2}\s+—\s+.+$",
            required_fields=["Date (UTC)", "Commit", "Type", "Summary", "Link", "Rationale"],
            allowed_types=["infra"],
            link_regex=r"^https://github\.com/.+/commit/[0-9a-f]{7,40}$",
        )
        self.assertTrue(invalid_parsed.errors)

    def test_changelog_parser_edge_errors(self) -> None:
        malformed = (
            "# Engineering Changelog\n"
            "## broken\n"
            "stray\n"
            "- Commit: ZZZ\n"
            "- Type: infra\n"
            "- Summary: \n"
            "- Link: bad\n"
            "- Rationale: \n"
        )
        parsed = parse_changelog(
            malformed,
            heading_regex=r"^##\s+\d{4}-\d{2}-\d{2}\s+—\s+.+$",
            required_fields=["Date (UTC)", "Commit", "Type", "Summary", "Link", "Rationale"],
            allowed_types=["infra"],
            link_regex=r"^https://github\.com/.+/commit/[0-9a-f]{7,40}$",
        )
        self.assertTrue(parsed.errors)

        no_entries = parse_changelog(
            "plain text",
            heading_regex=r"^##\s+\d{4}-\d{2}-\d{2}\s+—\s+.+$",
            required_fields=["Date (UTC)", "Commit", "Type", "Summary", "Link", "Rationale"],
            allowed_types=["infra"],
            link_regex=r"^https://github\.com/.+/commit/[0-9a-f]{7,40}$",
        )
        self.assertIn("no changelog entries found", no_entries.errors)

    def test_decision_parser(self) -> None:
        text = """# Decisions
## D-0001 — Test
Status: accepted
Date: 2026-02-17T00:00:00Z
Author: A
Related commits: abcdef1

### Context
X
### Options considered
1
### Decision
2
### Rationale
3
### Trade-offs
4
### Future reconsideration trigger
5
"""
        parsed = parse_decisions(
            text,
            heading_regex=r"^##\s+D-\d{4}\s+—\s+.+$",
            required_meta_fields=["Status", "Date", "Author", "Related commits"],
            allowed_statuses=["accepted"],
            required_sections=[
                "Context",
                "Options considered",
                "Decision",
                "Rationale",
                "Trade-offs",
                "Future reconsideration trigger",
            ],
        )
        self.assertFalse(parsed.errors)

    def test_decision_parser_edge_errors(self) -> None:
        empty = parse_decisions(
            "no entries",
            heading_regex=r"^##\s+D-\d{4}\s+—\s+.+$",
            required_meta_fields=["Status"],
            allowed_statuses=["accepted"],
            required_sections=["Context"],
        )
        self.assertTrue(empty.errors)

        broken = parse_decisions(
            "# Decisions\n## wrong heading\nStatus: maybe\n### Context\n",
            heading_regex=r"^##\s+D-\d{4}\s+—\s+.+$",
            required_meta_fields=["Status", "Date", "Author", "Related commits"],
            allowed_statuses=["accepted"],
            required_sections=["Context", "Decision"],
        )
        self.assertTrue(broken.errors)

    def test_parse_checksums_invalid(self) -> None:
        checksums, errors = parse_checksums_file("not-valid\n")
        self.assertTrue(errors)
        self.assertFalse(checksums)
        dup, dup_errors = parse_checksums_file(
            "a" * 64 + "  artifacts/claim_values.json\n" + "b" * 64 + "  artifacts/claim_values.json\n"
        )
        self.assertTrue(dup_errors)
        self.assertIn("artifacts/claim_values.json", dup)

    def test_extract_headings(self) -> None:
        headings = extract_headings("# T\n\n## A\n### B\n")
        self.assertIn("A", headings)

    def test_rule_core_requires_changelog(self) -> None:
        ctx = _context({"models/x.py"}, changed=[ChangedFile(status="M", raw_status="M", path="models/x.py")])
        violations = rule_core_requires_changelog(ctx)
        self.assertEqual("changelog_required", violations[0].rule_id)

    def test_rule_architecture_requires_decisions(self) -> None:
        ctx = _context({"engineering/ARCHITECTURE.md"})
        violations = rule_architecture_requires_decisions(ctx)
        self.assertEqual("decisions_required", violations[0].rule_id)

    @patch("scripts.ci.governance.rules.diff_deleted_lines", return_value=["- old line"])
    def test_rule_changelog_append_only(self, _: object) -> None:
        changed = [ChangedFile(status="M", raw_status="M", path="engineering/CHANGELOG.md")]
        ctx = _context({"engineering/CHANGELOG.md"}, changed=changed)
        violations = rule_changelog_append_only(ctx)
        self.assertEqual("changelog_append_only", violations[0].rule_id)

    @patch("scripts.ci.governance.rules.file_exists_at", return_value=True)
    @patch("scripts.ci.governance.rules._load_text_at_head")
    @patch("scripts.ci.governance.rules.parse_changelog")
    def test_rule_changelog_structure_and_sha(self, parse_mock: object, load_mock: object, exists_mock: object) -> None:
        del exists_mock, load_mock
        parse_mock.return_value = type(
            "X",
            (),
            {"errors": [], "commit_shas": ["1111111"]},
        )()
        changed = [ChangedFile(status="M", raw_status="M", path="engineering/CHANGELOG.md")]
        ctx = _context({"engineering/CHANGELOG.md"}, changed=changed, commit_shas=["111111111111"])
        violations = rule_changelog_structure_and_sha(ctx)
        self.assertFalse(violations)

    @patch("scripts.ci.governance.rules.file_exists_at", return_value=True)
    @patch("scripts.ci.governance.rules._load_text_at_head", return_value="x")
    @patch("scripts.ci.governance.rules.parse_changelog")
    def test_rule_changelog_structure_errors_and_empty_range(
        self, parse_mock: object, _: object, __: object
    ) -> None:
        parse_mock.return_value = type("X", (), {"errors": ["bad"], "commit_shas": []})()
        changed = [ChangedFile(status="M", raw_status="M", path="engineering/CHANGELOG.md")]
        ctx = _context({"engineering/CHANGELOG.md"}, changed=changed, commit_shas=[])
        violations = rule_changelog_structure_and_sha(ctx)
        self.assertEqual("changelog_structure", violations[0].rule_id)

        parse_mock.return_value = type("X", (), {"errors": [], "commit_shas": []})()
        violations = rule_changelog_structure_and_sha(ctx)
        self.assertEqual("changelog_sha_reference", violations[0].rule_id)

    @patch("scripts.ci.governance.rules.file_exists_at", return_value=True)
    @patch("scripts.ci.governance.rules._load_text_at_head", return_value="x")
    @patch("scripts.ci.governance.rules.parse_decisions")
    def test_rule_decisions_structure(self, parse_mock: object, _: object, __: object) -> None:
        parse_mock.return_value = type("D", (), {"errors": ["bad"]})()
        ctx = _context({"engineering/DECISIONS.md"})
        violations = rule_decisions_structure(ctx)
        self.assertEqual("decisions_structure", violations[0].rule_id)

    @patch("scripts.ci.governance.rules.file_exists_at", return_value=False)
    def test_rule_decisions_missing(self, _: object) -> None:
        ctx = _context({"engineering/ARCHITECTURE.md"})
        violations = rule_decisions_structure(ctx)
        self.assertEqual("decisions_missing", violations[0].rule_id)

    @patch("scripts.ci.governance.rules.file_exists_at", return_value=True)
    @patch("scripts.ci.governance.rules._load_text_at_head", return_value="# X")
    @patch("scripts.ci.governance.rules.missing_required_headings", return_value=["System Overview"])
    def test_rule_engineering_sections(self, _: object, __: object, ___: object) -> None:
        ctx = _context({"engineering/ARCHITECTURE.md"})
        violations = rule_engineering_sections(ctx)
        self.assertTrue(violations)

    @patch("scripts.ci.governance.rules.file_exists_at", return_value=False)
    def test_rule_engineering_sections_missing_file(self, _: object) -> None:
        ctx = _context({"engineering/ARCHITECTURE.md"})
        violations = rule_engineering_sections(ctx)
        self.assertTrue(violations)

    @patch("scripts.ci.governance.rules.file_exists_at", return_value=True)
    @patch("scripts.ci.governance.rules._load_text_at_head")
    @patch("scripts.ci.governance.rules.parse_checksums_file")
    @patch("scripts.ci.governance.rules.file_bytes_at", return_value=b"abc")
    def test_rule_artifact_checksums(self, _: object, parse_mock: object, load_mock: object, exists_mock: object) -> None:
        del exists_mock, load_mock
        digest = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        parse_mock.return_value = (
            {"artifacts/claim_values.json": digest},
            [],
        )
        changed = [ChangedFile(status="M", raw_status="M", path="artifacts/claim_values.json")]
        ctx = _context({"artifacts/claim_values.json"}, changed=changed)
        violations = rule_artifact_checksums(ctx)
        self.assertEqual("artifact_checksums_update_required", violations[0].rule_id)

    @patch("scripts.ci.governance.rules.file_exists_at", return_value=True)
    @patch("scripts.ci.governance.rules._load_text_at_head", return_value="bad-line")
    @patch("scripts.ci.governance.rules.parse_checksums_file", return_value=({}, ["bad"]))
    def test_rule_artifact_checksums_parse_error(self, _: object, __: object, ___: object) -> None:
        changed = [ChangedFile(status="M", raw_status="M", path="artifacts/evidence-pack-v1/checksums.sha256")]
        ctx = _context(
            {"artifacts/evidence-pack-v1/checksums.sha256"},
            changed=changed,
        )
        violations = rule_artifact_checksums(ctx)
        self.assertTrue(any(v.rule_id == "artifact_checksums_parse" for v in violations))

    @patch("scripts.ci.governance.rules.file_exists_at")
    @patch("scripts.ci.governance.rules._load_text_at_head", return_value="x")
    @patch(
        "scripts.ci.governance.rules.parse_checksums_file",
        return_value=({"artifacts/claim_values.json": "0" * 64}, []),
    )
    @patch("scripts.ci.governance.rules.file_bytes_at", return_value=b"abc")
    def test_rule_artifact_checksums_mismatch_and_missing_paths(
        self, _: object, __: object, ___: object, exists_mock: object
    ) -> None:
        def _exists(repo_root: Path, head: str, path: str) -> bool:  # noqa: ARG001
            return path != "artifacts/claim_values.json"

        exists_mock.side_effect = _exists
        changed = [ChangedFile(status="M", raw_status="M", path="artifacts/evidence-pack-v1/checksums.sha256")]
        ctx = _context(
            {"artifacts/evidence-pack-v1/checksums.sha256"},
            changed=changed,
        )
        violations = rule_artifact_checksums(ctx)
        ids = {item.rule_id for item in violations}
        self.assertIn("artifact_checksums_paths_missing", ids)

    @patch("scripts.ci.governance.rules.file_exists_at", return_value=True)
    @patch("scripts.ci.governance.rules._load_text_at_head", return_value="x")
    @patch(
        "scripts.ci.governance.rules.parse_checksums_file",
        return_value=({"artifacts/claim_values.json": "0" * 64}, []),
    )
    @patch("scripts.ci.governance.rules.file_bytes_at", return_value=b"abc")
    def test_rule_artifact_checksums_mismatch(
        self, _: object, __: object, ___: object, ____: object
    ) -> None:
        changed = [ChangedFile(status="M", raw_status="M", path="artifacts/evidence-pack-v1/checksums.sha256")]
        ctx = _context(
            {"artifacts/evidence-pack-v1/checksums.sha256"},
            changed=changed,
        )
        violations = rule_artifact_checksums(ctx)
        self.assertTrue(any(v.rule_id == "artifact_checksums_mismatch" for v in violations))

    @patch("scripts.ci.governance.rules.file_exists_at", return_value=False)
    def test_rule_artifact_checksums_missing_file(self, _: object) -> None:
        changed = [ChangedFile(status="M", raw_status="M", path="artifacts/claim_values.json")]
        ctx = _context({"artifacts/claim_values.json"}, changed=changed)
        violations = rule_artifact_checksums(ctx)
        self.assertTrue(any(v.rule_id == "artifact_checksums_missing" for v in violations))

    @patch("scripts.ci.governance.git_utils.run_git", return_value=b"\xff")
    def test_file_decode_error(self, _: object) -> None:
        from scripts.ci.governance.git_utils import file_contents_at

        with self.assertRaises(FileDecodeError):
            file_contents_at(Path("."), "HEAD", "x")

    @patch("scripts.ci.governance.rules.file_exists_at", return_value=False)
    def test_rule_engineering_files_exist(self, _: object) -> None:
        ctx = _context({"engineering/GOVERNANCE.md"})
        violations = rule_engineering_files_exist(ctx)
        self.assertEqual("engineering_files_required", violations[0].rule_id)

    def test_report_pass_text_branch(self) -> None:
        text = render_text(
            GovernanceResult(
                status="PASS",
                base="a",
                head="b",
                violations=[],
                notes=["no changes"],
            )
        )
        self.assertIn("PASS: governance checks passed", text)
        self.assertIn("no changes", text)

    def test_load_policy_validation_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "engineering").mkdir(parents=True, exist_ok=True)
            (repo / "engineering" / "governance_policy.yaml").write_text(
                json.dumps(
                    {
                        "version": "2",
                        "paths": "bad",
                        "changelog": {},
                        "decisions": {},
                        "engineering_sections": {},
                        "artifacts": {},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(GovernanceConfigError):
                load_policy(repo)

    def test_load_policy_utf8_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "engineering").mkdir(parents=True, exist_ok=True)
            (repo / "engineering" / "governance_policy.yaml").write_bytes(b"\xff\xfe")
            with self.assertRaises(GovernanceConfigError):
                load_policy(repo)

    def test_load_policy_engineering_section_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "engineering").mkdir(parents=True, exist_ok=True)
            payload = {
                "version": "2",
                "paths": {
                    "core_prefixes": ["src/"],
                    "architecture_files": ["engineering/ARCHITECTURE.md"],
                    "changelog": "engineering/CHANGELOG.md",
                    "decisions": "engineering/DECISIONS.md",
                    "engineering_prefix": "engineering/",
                    "required_engineering_files": ["engineering/CHANGELOG.md"],
                },
                "changelog": {
                    "required_fields": ["Date (UTC)"],
                    "allowed_types": ["infra"],
                    "link_regex": "^x$",
                    "heading_regex": "^x$",
                },
                "decisions": {
                    "entry_heading_regex": "^x$",
                    "required_meta_fields": ["Status"],
                    "allowed_statuses": ["accepted"],
                    "required_sections": ["Context"],
                },
                "engineering_sections": {"": ["ok"]},
                "artifacts": {
                    "prefix": "artifacts/",
                    "checksums_file": "artifacts/evidence-pack-v1/checksums.sha256",
                    "tracked_outputs": ["artifacts/claim_values.json"],
                },
            }
            (repo / "engineering" / "governance_policy.yaml").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            with self.assertRaises(GovernanceConfigError):
                load_policy(repo)

    def test_load_policy_field_type_errors(self) -> None:
        base_payload = {
            "version": "2",
            "paths": {
                "core_prefixes": ["src/"],
                "architecture_files": ["engineering/ARCHITECTURE.md"],
                "changelog": "engineering/CHANGELOG.md",
                "decisions": "engineering/DECISIONS.md",
                "engineering_prefix": "engineering/",
                "required_engineering_files": ["engineering/CHANGELOG.md"],
            },
            "changelog": {
                "required_fields": ["Date (UTC)"],
                "allowed_types": ["infra"],
                "link_regex": "^x$",
                "heading_regex": "^x$",
            },
            "decisions": {
                "entry_heading_regex": "^x$",
                "required_meta_fields": ["Status"],
                "allowed_statuses": ["accepted"],
                "required_sections": ["Context"],
            },
            "engineering_sections": {"engineering/ARCHITECTURE.md": ["System Overview"]},
            "artifacts": {
                "prefix": "artifacts/",
                "checksums_file": "artifacts/evidence-pack-v1/checksums.sha256",
                "tracked_outputs": ["artifacts/claim_values.json"],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "engineering").mkdir(parents=True, exist_ok=True)

            payload = dict(base_payload)
            payload["version"] = "   "
            (repo / "engineering" / "governance_policy.yaml").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            with self.assertRaises(GovernanceConfigError):
                load_policy(repo)

            payload = dict(base_payload)
            payload["paths"] = dict(base_payload["paths"])
            payload["paths"]["core_prefixes"] = [""]
            (repo / "engineering" / "governance_policy.yaml").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            with self.assertRaises(GovernanceConfigError):
                load_policy(repo)

            payload = dict(base_payload)
            payload["engineering_sections"] = {"engineering/ARCHITECTURE.md": ["", "x"]}
            (repo / "engineering" / "governance_policy.yaml").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            with self.assertRaises(GovernanceConfigError):
                load_policy(repo)

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _git(repo: Path, *args: str) -> str:
        import subprocess

        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout

    def _git_init(self, repo: Path) -> None:
        self._git(repo, "init")
        self._git(repo, "config", "user.email", "t@example.com")
        self._git(repo, "config", "user.name", "t")

    def _git_commit(self, repo: Path, message: str) -> None:
        self._git(repo, "add", ".")
        self._git(repo, "commit", "-m", message)


if __name__ == "__main__":
    unittest.main()
