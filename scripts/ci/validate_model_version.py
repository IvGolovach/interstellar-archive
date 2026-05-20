#!/usr/bin/env python3
"""Validate MODEL_VERSION.json required keys and contract values."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_INTERNAL = 3


EXPECTED_MODEL_VERSION: Dict[str, str] = {
    "engine_version": "v1",
    "schema_version": "sim_schema.v2",
    "physics_engine_version": "v1",
    "mission_spec_version": "v1",
    "evidence_layer_version": "v1",
}


def validate(path: Path) -> List[str]:
    errors: List[str] = []
    if not path.is_file():
        return [f"missing file: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]
    if not isinstance(payload, dict):
        return ["MODEL_VERSION.json must be a JSON object"]

    keys = set(payload.keys())
    expected_keys = set(EXPECTED_MODEL_VERSION.keys())
    missing = sorted(expected_keys - keys)
    extra = sorted(keys - expected_keys)
    for key in missing:
        errors.append(f"missing required key: {key}")
    for key in extra:
        errors.append(f"unexpected key: {key}")

    for key, expected_value in EXPECTED_MODEL_VERSION.items():
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key} must be a non-empty string")
            continue
        if value != expected_value:
            errors.append(f"{key} must be '{expected_value}' (got '{value}')")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate MODEL_VERSION.json contract.")
    parser.add_argument("--model-version-file", default="MODEL_VERSION.json")
    args = parser.parse_args()
    path = Path(args.model_version_file)
    try:
        errors = validate(path)
        if errors:
            print("FAIL: model version validation")
            for error in errors:
                print(f"- {error}")
            return EXIT_FAIL
        print("PASS: model version validation")
        print(f"- file: {path}")
        return EXIT_PASS
    except Exception as exc:  # pragma: no cover
        print(f"INTERNAL ERROR: model version validation failed: {exc}")
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())

