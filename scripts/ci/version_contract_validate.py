#!/usr/bin/env python3
"""Validate SemVer version contract across repository release metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text


EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_INTERNAL = 3

STRICT_SEMVER_RE = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
VERSION_NAMESPACE_RE = re.compile(r"^v\d+(?:\.\d+){0,2}$")
README_SEMVER_RE = re.compile(r"\bv\d+\.\d+\.\d+\b")


def _git(repo_root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        env={**os.environ, "LANG": "C", "LC_ALL": "C"},
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or proc.stdout.strip() or f"exit={proc.returncode}"
        raise ValueError(f"git {' '.join(args)} failed: {stderr}")
    return proc.stdout.strip()


def _read_object_json(path: Path) -> Dict[str, Any]:
    try:
        payload = load_json(path)
    except FileNotFoundError as exc:
        raise ValueError(f"missing file: {path}") from exc
    except ValueError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level object")
    return payload


def _load_yaml_like(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(text)
    except ModuleNotFoundError:
        payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must parse to a top-level object")
    return payload


def _parse_semver(tag: str) -> Tuple[int, int, int]:
    match = STRICT_SEMVER_RE.match(tag)
    if not match:
        raise ValueError(f"not a strict semver tag: {tag}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def validate(repo_root: Path) -> List[str]:
    errors: List[str] = []

    version = (repo_root / "VERSION").read_text(encoding="utf-8").strip()
    if not VERSION_RE.match(version):
        errors.append("VERSION must match ^\\d+\\.\\d+\\.\\d+$ without leading zeros")
        return errors

    expected_tag = f"v{version}"
    version_tuple = _parse_semver(expected_tag)

    citation = _load_yaml_like(repo_root / "CITATION.cff")
    citation_version = str(citation.get("version", "")).strip()
    if citation_version != version:
        errors.append(f"CITATION.cff version mismatch: expected {version}, got {citation_version or '<empty>'}")

    signals = _read_object_json(repo_root / "artifacts" / "research_signals.json")
    signals_version = str(signals.get("version", "")).strip()
    if signals_version != expected_tag:
        errors.append(
            f"artifacts/research_signals.json version mismatch: expected {expected_tag}, got {signals_version or '<empty>'}"
        )

    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    readme_versions = sorted(set(README_SEMVER_RE.findall(readme)))
    mismatched_readme_versions = [item for item in readme_versions if item != expected_tag]
    if mismatched_readme_versions:
        errors.append(
            "README contains hardcoded semver strings that diverge from VERSION: "
            + ", ".join(mismatched_readme_versions)
        )

    raw_tags = _git(repo_root, "tag", "-l").splitlines()
    tags = [item.strip() for item in raw_tags if item.strip()]

    invalid_version_namespace_tags = [
        tag for tag in tags if VERSION_NAMESPACE_RE.match(tag) and not STRICT_SEMVER_RE.match(tag)
    ]
    if invalid_version_namespace_tags:
        errors.append(
            "invalid version-namespace tags (must be vMAJOR.MINOR.PATCH): "
            + ", ".join(sorted(invalid_version_namespace_tags))
        )

    semver_tags = [tag for tag in tags if STRICT_SEMVER_RE.match(tag)]
    if semver_tags:
        latest_semver = max(semver_tags, key=_parse_semver)
        if _parse_semver(latest_semver) > version_tuple:
            errors.append(
                f"latest semver tag {latest_semver} is greater than VERSION {version}; "
                "VERSION must not lag the latest release tag"
            )

    head_tags = _git(repo_root, "tag", "--points-at", "HEAD").splitlines()
    head_semver_tags = [tag.strip() for tag in head_tags if STRICT_SEMVER_RE.match(tag.strip())]
    for tag in head_semver_tags:
        if tag != expected_tag:
            errors.append(f"HEAD semver tag mismatch: expected {expected_tag}, got {tag}")

    return errors


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--strict", action="store_true", help="Accepted for CI parity; always strict")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def _render_text(payload: Dict[str, Any]) -> str:
    if payload["status"] == "PASS":
        return "\n".join(
            [
                "PASS: version contract validation",
                f"- version: {payload['version']}",
            ]
        )
    lines = ["FAIL: version contract validation"]
    for error in payload.get("errors", []):
        lines.append(f"- {error}")
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root).resolve()
    try:
        errors = validate(repo_root)
        payload = {
            "status": "PASS" if not errors else "FAIL",
            "version": (repo_root / "VERSION").read_text(encoding="utf-8").strip(),
            "errors": errors,
        }
        rendered = render_output(payload, output_format=args.format, text_renderer=_render_text)
        print(rendered)
        if args.output:
            write_text(Path(args.output), rendered)
        return EXIT_PASS if not errors else EXIT_FAIL
    except ValueError as exc:
        message = f"FAIL: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_FAIL
    except Exception as exc:  # pragma: no cover
        message = f"INTERNAL ERROR: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
