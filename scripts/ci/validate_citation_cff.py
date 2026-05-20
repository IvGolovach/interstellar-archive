#!/usr/bin/env python3
"""Validate CITATION.cff structure for required public metadata fields."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_INTERNAL = 3


REQUIRED_KEYS = (
    "cff-version",
    "message",
    "title",
    "authors",
    "version",
    "date-released",
    "url",
    "license",
    "repository-code",
)


def _load_yaml_like(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(text)
    except ModuleNotFoundError:
        # YAML is a superset of JSON; this fallback keeps validator deterministic in minimal envs.
        parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("CITATION.cff must parse to a top-level object.")
    return parsed


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(path: Path, version_file: Path) -> List[str]:
    errors: List[str] = []
    if not path.is_file():
        return [f"missing file: {path}"]

    data = _load_yaml_like(path)
    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    for key in ("cff-version", "message", "title", "version", "date-released", "url", "license", "repository-code"):
        if key in data and not _is_non_empty_string(data.get(key)):
            errors.append(f"{key} must be a non-empty string")

    authors = data.get("authors")
    if not isinstance(authors, list) or len(authors) == 0:
        errors.append("authors must be a non-empty list")
    else:
        for idx, author in enumerate(authors):
            if not isinstance(author, dict):
                errors.append(f"authors[{idx}] must be an object")
                continue
            has_name = _is_non_empty_string(author.get("name"))
            has_split_name = _is_non_empty_string(author.get("family-names")) or _is_non_empty_string(author.get("given-names"))
            if not (has_name or has_split_name):
                errors.append(f"authors[{idx}] must define 'name' or family/given names")

    if version_file.is_file():
        expected_version = version_file.read_text(encoding="utf-8").strip()
        if _is_non_empty_string(expected_version):
            if str(data.get("version", "")).strip() != expected_version:
                errors.append(
                    f"version mismatch: CITATION.cff={data.get('version')} VERSION={expected_version}"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CITATION.cff required fields.")
    parser.add_argument("--citation-file", default="CITATION.cff")
    parser.add_argument("--version-file", default="VERSION")
    args = parser.parse_args()

    citation_file = Path(args.citation_file)
    version_file = Path(args.version_file)
    try:
        errors = validate(citation_file, version_file)
        if errors:
            print("FAIL: citation validation")
            for error in errors:
                print(f"- {error}")
            return EXIT_FAIL
        print("PASS: citation validation")
        print(f"- file: {citation_file}")
        return EXIT_PASS
    except Exception as exc:  # pragma: no cover
        print(f"INTERNAL ERROR: citation validation failed: {exc}")
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())

