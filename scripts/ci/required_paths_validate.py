#!/usr/bin/env python3
"""Validate required repository files declared in docs/required_paths.v1.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_INTERNAL = 3
MANIFEST_VERSION = "required_paths.v1"


def load_manifest(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level object")
    if payload.get("version") != MANIFEST_VERSION:
        raise ValueError(f"{path} must declare version={MANIFEST_VERSION}")

    groups = payload.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError(f"{path} must contain a non-empty 'groups' array")

    return payload


def _validate_manifest_shape(manifest: Mapping[str, Any], manifest_path: Path) -> List[str]:
    errors: List[str] = []
    seen_group_ids: set[str] = set()
    seen_paths: set[str] = set()

    groups = manifest.get("groups", [])
    if not isinstance(groups, list):
        return [f"{manifest_path} has invalid 'groups' payload"]

    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            errors.append(f"{manifest_path} group #{index + 1} must be an object")
            continue

        group_id = group.get("id")
        description = group.get("description")
        paths = group.get("paths")

        if not isinstance(group_id, str) or not group_id.strip():
            errors.append(f"{manifest_path} group #{index + 1} must define a non-empty string id")
        elif group_id in seen_group_ids:
            errors.append(f"{manifest_path} declares duplicate group id: {group_id}")
        else:
            seen_group_ids.add(group_id)

        if not isinstance(description, str) or not description.strip():
            errors.append(f"{manifest_path} group '{group_id or index + 1}' must define a non-empty description")

        if not isinstance(paths, list) or not paths:
            errors.append(f"{manifest_path} group '{group_id or index + 1}' must declare a non-empty paths list")
            continue

        for raw_path in paths:
            if not isinstance(raw_path, str) or not raw_path.strip():
                errors.append(f"{manifest_path} group '{group_id or index + 1}' contains an invalid path entry")
                continue
            if raw_path.startswith("/"):
                errors.append(f"{manifest_path} path must be repository-relative: {raw_path}")
                continue
            relative_path = Path(raw_path)
            if ".." in relative_path.parts:
                errors.append(f"{manifest_path} path must not escape repo root: {raw_path}")
                continue
            normalized = relative_path.as_posix()
            if normalized in seen_paths:
                errors.append(f"{manifest_path} declares duplicate path: {normalized}")
                continue
            seen_paths.add(normalized)

    return errors


def validate_required_paths(repo_root: Path, manifest: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    groups = manifest.get("groups", [])

    for group in groups:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id", "<unknown>"))
        for raw_path in group.get("paths", []):
            if not isinstance(raw_path, str) or not raw_path.strip():
                continue
            path = (repo_root / raw_path).resolve()
            try:
                path.relative_to(repo_root.resolve())
            except ValueError:
                errors.append(f"[{group_id}] path escapes repo root: {raw_path}")
                continue

            if not path.exists():
                errors.append(f"[{group_id}] missing file: {raw_path}")
                continue
            if not path.is_file():
                errors.append(f"[{group_id}] expected file but found non-file path: {raw_path}")
                continue
            if path.stat().st_size == 0:
                errors.append(f"[{group_id}] empty file: {raw_path}")

    return errors


def summarize_groups(manifest: Mapping[str, Any]) -> List[str]:
    lines: List[str] = []
    for group in manifest.get("groups", []):
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id", "<unknown>"))
        paths = group.get("paths", [])
        count = len(paths) if isinstance(paths, list) else 0
        lines.append(f"- {group_id}: {count} required files")
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument(
        "--manifest",
        default="docs/required_paths.v1.json",
        help="Repository-relative or absolute path to the required-paths manifest",
    )
    parser.add_argument("--strict", action="store_true", help="Accepted for CI parity; always strict")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path
    manifest_path = manifest_path.resolve()

    try:
        manifest = load_manifest(manifest_path)
        errors = _validate_manifest_shape(manifest, manifest_path)
        errors.extend(validate_required_paths(repo_root, manifest))
        if errors:
            print("FAIL: required paths validation")
            for error in errors:
                print(f"- {error}")
            return EXIT_FAIL

        print("PASS: required paths validation")
        print(f"- manifest: {manifest_path.relative_to(repo_root)}")
        for line in summarize_groups(manifest):
            print(line)
        return EXIT_PASS
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return EXIT_FAIL
    except Exception as exc:  # pragma: no cover
        print(f"INTERNAL ERROR: {exc}")
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
