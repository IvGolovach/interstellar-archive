"""Policy loading for governance checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


class GovernanceConfigError(ValueError):
    """Raised for invalid governance configuration."""


@dataclass(frozen=True)
class PathsPolicy:
    core_prefixes: List[str]
    architecture_files: List[str]
    changelog: str
    decisions: str
    engineering_prefix: str
    required_engineering_files: List[str]


@dataclass(frozen=True)
class ChangelogPolicy:
    required_fields: List[str]
    allowed_types: List[str]
    link_regex: str
    heading_regex: str


@dataclass(frozen=True)
class DecisionsPolicy:
    entry_heading_regex: str
    required_meta_fields: List[str]
    allowed_statuses: List[str]
    required_sections: List[str]


@dataclass(frozen=True)
class ArtifactsPolicy:
    prefix: str
    checksums_file: str
    tracked_outputs: List[str]


@dataclass(frozen=True)
class GovernancePolicy:
    version: str
    paths: PathsPolicy
    changelog: ChangelogPolicy
    decisions: DecisionsPolicy
    engineering_sections: Dict[str, List[str]]
    artifacts: ArtifactsPolicy


def _require_mapping(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise GovernanceConfigError(f"policy key '{key}' must be an object")
    return value


def _require_list(data: Dict[str, Any], key: str) -> List[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise GovernanceConfigError(f"policy key '{key}' must be a list")
    return value


def _require_str(data: Dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GovernanceConfigError(f"policy key '{key}' must be a non-empty string")
    return value


def _require_str_list(data: Dict[str, Any], key: str) -> List[str]:
    values = _require_list(data, key)
    if not all(isinstance(item, str) and item.strip() for item in values):
        raise GovernanceConfigError(f"policy key '{key}' must contain non-empty strings")
    return list(values)


def load_policy(repo_root: Path) -> GovernancePolicy:
    """Load governance policy from engineering/governance_policy.yaml."""
    policy_path = repo_root / "engineering" / "governance_policy.yaml"
    if not policy_path.exists():
        raise GovernanceConfigError(f"missing policy file: {policy_path}")

    try:
        raw = json.loads(policy_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise GovernanceConfigError(f"policy file is not valid UTF-8: {policy_path}") from exc
    except json.JSONDecodeError as exc:
        raise GovernanceConfigError(f"policy file is not valid JSON-compatible YAML: {exc}") from exc

    version = _require_str(raw, "version")

    paths_raw = _require_mapping(raw, "paths")
    paths = PathsPolicy(
        core_prefixes=_require_str_list(paths_raw, "core_prefixes"),
        architecture_files=_require_str_list(paths_raw, "architecture_files"),
        changelog=_require_str(paths_raw, "changelog"),
        decisions=_require_str(paths_raw, "decisions"),
        engineering_prefix=_require_str(paths_raw, "engineering_prefix"),
        required_engineering_files=_require_str_list(paths_raw, "required_engineering_files"),
    )

    changelog_raw = _require_mapping(raw, "changelog")
    changelog = ChangelogPolicy(
        required_fields=_require_str_list(changelog_raw, "required_fields"),
        allowed_types=_require_str_list(changelog_raw, "allowed_types"),
        link_regex=_require_str(changelog_raw, "link_regex"),
        heading_regex=_require_str(changelog_raw, "heading_regex"),
    )

    decisions_raw = _require_mapping(raw, "decisions")
    decisions = DecisionsPolicy(
        entry_heading_regex=_require_str(decisions_raw, "entry_heading_regex"),
        required_meta_fields=_require_str_list(decisions_raw, "required_meta_fields"),
        allowed_statuses=_require_str_list(decisions_raw, "allowed_statuses"),
        required_sections=_require_str_list(decisions_raw, "required_sections"),
    )

    engineering_sections_raw = _require_mapping(raw, "engineering_sections")
    engineering_sections: Dict[str, List[str]] = {}
    for file_path, sections in engineering_sections_raw.items():
        if not isinstance(file_path, str) or not file_path.strip():
            raise GovernanceConfigError("engineering_sections keys must be non-empty strings")
        if not isinstance(sections, list) or not all(isinstance(x, str) and x.strip() for x in sections):
            raise GovernanceConfigError(
                f"engineering_sections['{file_path}'] must be a list of non-empty strings"
            )
        engineering_sections[file_path] = list(sections)

    artifacts_raw = _require_mapping(raw, "artifacts")
    artifacts = ArtifactsPolicy(
        prefix=_require_str(artifacts_raw, "prefix"),
        checksums_file=_require_str(artifacts_raw, "checksums_file"),
        tracked_outputs=_require_str_list(artifacts_raw, "tracked_outputs"),
    )

    return GovernancePolicy(
        version=version,
        paths=paths,
        changelog=changelog,
        decisions=decisions,
        engineering_sections=engineering_sections,
        artifacts=artifacts,
    )

