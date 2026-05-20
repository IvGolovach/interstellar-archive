"""Rule engine for governance enforcement."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set

from scripts.ci.governance.config import GovernancePolicy, load_policy
from scripts.ci.governance.git_utils import (
    ChangedFile,
    commit_range,
    diff_deleted_lines,
    file_bytes_at,
    file_contents_at,
    file_exists_at,
    is_file_changed,
    changed_files,
)
from scripts.ci.governance.parsers import (
    parse_changelog,
    parse_decisions,
    missing_required_headings,
    parse_checksums_file,
)


@dataclass(frozen=True)
class Violation:
    rule_id: str
    severity: str
    evidence: Dict[str, Any]
    fix: str


@dataclass
class GovernanceResult:
    status: str
    base: str
    head: str
    violations: List[Violation] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class RuleContext:
    repo_root: Path
    base: str
    head: str
    policy: GovernancePolicy
    changed: Sequence[ChangedFile]
    commit_shas: Sequence[str]
    touched_paths: Set[str]

    @property
    def changelog_path(self) -> str:
        return self.policy.paths.changelog

    @property
    def decisions_path(self) -> str:
        return self.policy.paths.decisions

    @property
    def changelog_changed(self) -> bool:
        return is_file_changed(self.changed, self.changelog_path)

    @property
    def decisions_changed(self) -> bool:
        return is_file_changed(self.changed, self.decisions_path)

    @property
    def engineering_changed(self) -> bool:
        prefix = self.policy.paths.engineering_prefix
        return any(path.startswith(prefix) for path in self.touched_paths)

    @property
    def architecture_contract_changed(self) -> bool:
        return any(path in set(self.policy.paths.architecture_files) for path in self.touched_paths)


def _prefix_match(path: str, prefixes: Sequence[str]) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


def _sha_matches_range(logged_sha: str, range_sha: str) -> bool:
    return range_sha.startswith(logged_sha) or logged_sha.startswith(range_sha)


def _load_text_at_head(ctx: RuleContext, path: str) -> str:
    return file_contents_at(ctx.repo_root, ctx.head, path)


def rule_core_requires_changelog(ctx: RuleContext) -> List[Violation]:
    core_changed = sorted(path for path in ctx.touched_paths if _prefix_match(path, ctx.policy.paths.core_prefixes))
    if not core_changed or ctx.changelog_changed:
        return []
    return [
        Violation(
            rule_id="changelog_required",
            severity="error",
            evidence={
                "changed_core_paths": core_changed,
                "required_file": ctx.changelog_path,
            },
            fix=(
                "Update engineering/CHANGELOG.md with Date (UTC), Commit, Type, Summary, Link, and Rationale."
            ),
        )
    ]


def rule_architecture_requires_decisions(ctx: RuleContext) -> List[Violation]:
    if not ctx.architecture_contract_changed or ctx.decisions_changed:
        return []
    changed_architecture_paths = sorted(
        path for path in ctx.touched_paths if path in set(ctx.policy.paths.architecture_files)
    )
    return [
        Violation(
            rule_id="decisions_required",
            severity="error",
            evidence={
                "changed_architecture_paths": changed_architecture_paths,
                "required_file": ctx.decisions_path,
            },
            fix=(
                "Update engineering/DECISIONS.md with a new D-xxxx entry describing the architectural change."
            ),
        )
    ]


def rule_engineering_files_exist(ctx: RuleContext) -> List[Violation]:
    if not ctx.engineering_changed:
        return []
    missing = [
        path
        for path in ctx.policy.paths.required_engineering_files
        if not file_exists_at(ctx.repo_root, ctx.head, path)
    ]
    if not missing:
        return []
    return [
        Violation(
            rule_id="engineering_files_required",
            severity="error",
            evidence={"missing_files": sorted(missing)},
            fix="Restore required engineering files defined in engineering/governance_policy.yaml.",
        )
    ]


def rule_changelog_append_only(ctx: RuleContext) -> List[Violation]:
    if not ctx.changelog_changed:
        return []
    deleted = diff_deleted_lines(ctx.repo_root, ctx.base, ctx.head, ctx.changelog_path)
    if not deleted:
        return []
    return [
        Violation(
            rule_id="changelog_append_only",
            severity="error",
            evidence={
                "file": ctx.changelog_path,
                "deleted_lines": deleted,
            },
            fix="Remove deletions from engineering/CHANGELOG.md; changelog must be append-only.",
        )
    ]


def rule_changelog_structure_and_sha(ctx: RuleContext) -> List[Violation]:
    if not (ctx.changelog_changed or ctx.engineering_changed):
        return []
    if not file_exists_at(ctx.repo_root, ctx.head, ctx.changelog_path):
        return [
            Violation(
                rule_id="changelog_missing",
                severity="error",
                evidence={"file": ctx.changelog_path},
                fix="Restore engineering/CHANGELOG.md.",
            )
        ]

    parsed = parse_changelog(
        _load_text_at_head(ctx, ctx.changelog_path),
        heading_regex=ctx.policy.changelog.heading_regex,
        required_fields=ctx.policy.changelog.required_fields,
        allowed_types=ctx.policy.changelog.allowed_types,
        link_regex=ctx.policy.changelog.link_regex,
    )
    violations: List[Violation] = []
    if parsed.errors:
        violations.append(
            Violation(
                rule_id="changelog_structure",
                severity="error",
                evidence={"file": ctx.changelog_path, "errors": parsed.errors},
                fix="Fix engineering/CHANGELOG.md entries to match required schema.",
            )
        )
        return violations

    if ctx.changelog_changed:
        if not ctx.commit_shas:
            violations.append(
                Violation(
                    rule_id="changelog_sha_reference",
                    severity="error",
                    evidence={
                        "file": ctx.changelog_path,
                        "commit_range": [],
                        "logged_commits": parsed.commit_shas,
                    },
                    fix="Provide valid commit range and reference one commit in engineering/CHANGELOG.md.",
                )
            )
            return violations

        matched = False
        for logged_sha in parsed.commit_shas:
            for range_sha in ctx.commit_shas:
                if _sha_matches_range(logged_sha, range_sha):
                    matched = True
                    break
            if matched:
                break
        if not matched:
            violations.append(
                Violation(
                    rule_id="changelog_sha_reference",
                    severity="error",
                    evidence={
                        "file": ctx.changelog_path,
                        "commit_range": list(ctx.commit_shas),
                        "logged_commits": parsed.commit_shas,
                    },
                    fix=(
                        "Add a changelog entry Commit field that references at least one SHA from base..head."
                    ),
                )
            )
    return violations


def rule_decisions_structure(ctx: RuleContext) -> List[Violation]:
    should_validate = ctx.decisions_changed or ctx.architecture_contract_changed or ctx.engineering_changed
    if not should_validate:
        return []
    if not file_exists_at(ctx.repo_root, ctx.head, ctx.decisions_path):
        return [
            Violation(
                rule_id="decisions_missing",
                severity="error",
                evidence={"file": ctx.decisions_path},
                fix="Restore engineering/DECISIONS.md.",
            )
        ]

    parsed = parse_decisions(
        _load_text_at_head(ctx, ctx.decisions_path),
        heading_regex=ctx.policy.decisions.entry_heading_regex,
        required_meta_fields=ctx.policy.decisions.required_meta_fields,
        allowed_statuses=ctx.policy.decisions.allowed_statuses,
        required_sections=ctx.policy.decisions.required_sections,
    )
    if not parsed.errors:
        return []
    return [
        Violation(
            rule_id="decisions_structure",
            severity="error",
            evidence={"file": ctx.decisions_path, "errors": parsed.errors},
            fix="Fix engineering/DECISIONS.md to match the required decision template.",
        )
    ]


def rule_engineering_sections(ctx: RuleContext) -> List[Violation]:
    if not ctx.engineering_changed:
        return []
    violations: List[Violation] = []
    for file_path, required_sections in ctx.policy.engineering_sections.items():
        if not file_exists_at(ctx.repo_root, ctx.head, file_path):
            violations.append(
                Violation(
                    rule_id="engineering_sections",
                    severity="error",
                    evidence={"file": file_path, "missing_sections": required_sections},
                    fix=f"Restore {file_path} and include required sections.",
                )
            )
            continue
        text = _load_text_at_head(ctx, file_path)
        missing = missing_required_headings(text, required_sections)
        if missing:
            violations.append(
                Violation(
                    rule_id="engineering_sections",
                    severity="error",
                    evidence={"file": file_path, "missing_sections": missing},
                    fix=f"Add required sections to {file_path}.",
                )
            )
    return violations


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rule_artifact_checksums(ctx: RuleContext) -> List[Violation]:
    artifacts_prefix = ctx.policy.artifacts.prefix
    artifacts_changed = any(path.startswith(artifacts_prefix) for path in ctx.touched_paths)
    if not artifacts_changed:
        return []

    checksums_file = ctx.policy.artifacts.checksums_file
    tracked_outputs = set(ctx.policy.artifacts.tracked_outputs)
    tracked_changed = any(path in tracked_outputs for path in ctx.touched_paths)
    checksums_changed = is_file_changed(ctx.changed, checksums_file)

    violations: List[Violation] = []
    if tracked_changed and not checksums_changed:
        violations.append(
            Violation(
                rule_id="artifact_checksums_update_required",
                severity="error",
                evidence={
                    "changed_artifacts": sorted(path for path in ctx.touched_paths if path in tracked_outputs),
                    "required_file": checksums_file,
                },
                fix="Update artifacts/evidence-pack-v1/checksums.sha256 when tracked artifact outputs change.",
            )
        )

    if not file_exists_at(ctx.repo_root, ctx.head, checksums_file):
        violations.append(
            Violation(
                rule_id="artifact_checksums_missing",
                severity="error",
                evidence={"required_file": checksums_file},
                fix="Restore artifacts/evidence-pack-v1/checksums.sha256.",
            )
        )
        return violations

    checksums_text = _load_text_at_head(ctx, checksums_file)
    checksums, parse_errors = parse_checksums_file(checksums_text)
    if parse_errors:
        violations.append(
            Violation(
                rule_id="artifact_checksums_parse",
                severity="error",
                evidence={"file": checksums_file, "errors": parse_errors},
                fix="Fix checksums.sha256 format to '<64-hex><two spaces><relative path>'.",
            )
        )
        return violations

    missing_tracked = sorted(path for path in tracked_outputs if path not in checksums)
    if missing_tracked:
        violations.append(
            Violation(
                rule_id="artifact_checksums_missing_entries",
                severity="error",
                evidence={"missing_entries": missing_tracked, "file": checksums_file},
                fix="Add checksum entries for all tracked artifact outputs.",
            )
        )

    mismatches: List[Dict[str, str]] = []
    missing_paths: List[str] = []
    for rel_path, expected_digest in checksums.items():
        if not file_exists_at(ctx.repo_root, ctx.head, rel_path):
            missing_paths.append(rel_path)
            continue
        actual_digest = _sha256(file_bytes_at(ctx.repo_root, ctx.head, rel_path))
        if actual_digest != expected_digest:
            mismatches.append(
                {
                    "path": rel_path,
                    "expected": expected_digest,
                    "actual": actual_digest,
                }
            )

    if missing_paths:
        violations.append(
            Violation(
                rule_id="artifact_checksums_paths_missing",
                severity="error",
                evidence={"missing_paths": sorted(missing_paths)},
                fix="Restore missing artifact files or remove stale entries from checksums.sha256.",
            )
        )
    if mismatches:
        violations.append(
            Violation(
                rule_id="artifact_checksums_mismatch",
                severity="error",
                evidence={"mismatches": mismatches},
                fix="Regenerate artifacts and refresh checksums.sha256.",
            )
        )

    return violations


RULES = [
    rule_core_requires_changelog,
    rule_architecture_requires_decisions,
    rule_engineering_files_exist,
    rule_changelog_append_only,
    rule_changelog_structure_and_sha,
    rule_decisions_structure,
    rule_engineering_sections,
    rule_artifact_checksums,
]


def run_governance_checks(repo_root: Path, base: str, head: str) -> GovernanceResult:
    policy = load_policy(repo_root)
    changed = changed_files(repo_root, base, head)
    commit_shas = commit_range(repo_root, base, head)
    if not changed:
        return GovernanceResult(
            status="PASS",
            base=base,
            head=head,
            violations=[],
            notes=["No files changed in commit range."],
        )

    touched_paths: Set[str] = set()
    for item in changed:
        touched_paths.update(item.touched_paths())

    context = RuleContext(
        repo_root=repo_root,
        base=base,
        head=head,
        policy=policy,
        changed=changed,
        commit_shas=commit_shas,
        touched_paths=touched_paths,
    )

    violations: List[Violation] = []
    for rule in RULES:
        violations.extend(rule(context))

    return GovernanceResult(
        status="FAIL" if violations else "PASS",
        base=base,
        head=head,
        violations=violations,
        notes=[],
    )

