#!/usr/bin/env python3
"""Validate research signals payload and enforce no-drift contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
from typing import Any, Dict, List


REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from scripts.build_research_signals import (  # noqa: E402
    GOLDEN_CHECKSUM_PATTERN,
    build_research_signals_payload,
)


EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_INTERNAL = 3

REQUIRED_KEYS = {
    "engine_version",
    "schema_version",
    "golden_checksum",
    "golden_checksum_short",
    "determinism_verified",
    "evidence_completeness",
    "ci_status",
    "realistic_mode_verified",
    "speculative_mode_enabled",
    "last_verified_commit",
    "version",
    "license",
    "determinism_badge",
    "golden_badge",
    "evidence_badge",
    "ci_badge",
    "realistic_mode_badge",
    "speculative_mode_badge",
    "version_badge",
    "license_badge",
}


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level object")
    return payload


def _validate_shape(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    keys = set(payload.keys())
    missing = sorted(REQUIRED_KEYS - keys)
    for key in missing:
        errors.append(f"missing key: {key}")

    if "golden_checksum" in payload:
        checksum = str(payload["golden_checksum"])
        if not GOLDEN_CHECKSUM_PATTERN.match(checksum):
            errors.append("golden_checksum must be a 64-hex string")
    if "golden_checksum_short" in payload and "golden_checksum" in payload:
        expected_short = f"{str(payload['golden_checksum'])[:7]}..."
        if payload["golden_checksum_short"] != expected_short:
            errors.append("golden_checksum_short does not match golden_checksum")

    if not isinstance(payload.get("determinism_verified"), bool):
        errors.append("determinism_verified must be boolean")
    if not isinstance(payload.get("realistic_mode_verified"), bool):
        errors.append("realistic_mode_verified must be boolean")
    if not isinstance(payload.get("speculative_mode_enabled"), bool):
        errors.append("speculative_mode_enabled must be boolean")

    evidence = payload.get("evidence_completeness")
    if not isinstance(evidence, (float, int)):
        errors.append("evidence_completeness must be numeric")
    elif not (0 <= float(evidence) <= 1):
        errors.append("evidence_completeness must be in [0, 1]")

    ci_status = payload.get("ci_status")
    if ci_status not in {"passing", "failing"}:
        errors.append("ci_status must be 'passing' or 'failing'")

    for key in (
        "determinism_badge",
        "golden_badge",
        "evidence_badge",
        "ci_badge",
        "realistic_mode_badge",
        "speculative_mode_badge",
        "version_badge",
        "license_badge",
    ):
        badge = payload.get(key)
        if not isinstance(badge, dict):
            errors.append(f"{key} must be an object")
            continue
        for field in ("label", "message", "color"):
            value = badge.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{key}.{field} must be a non-empty string")

    return errors


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--signals-file", default="artifacts/research_signals.json", help="Path to research signals file")
    parser.add_argument("--strict", action="store_true", help="Fail if file does not exactly match computed payload")
    parser.add_argument(
        "--no-require-tag",
        action="store_true",
        help="Do not require matching vX.Y.Z tag when computing expected payload",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root).resolve()
    signals_file = (repo_root / args.signals_file).resolve()
    try:
        payload = _read_json(signals_file)
        errors = _validate_shape(payload)

        if args.strict:
            expected = build_research_signals_payload(repo_root=repo_root, require_tag=not args.no_require_tag)
            if payload != expected:
                errors.append("signals payload drift: file content does not match computed contract")

        if errors:
            print("FAIL: research signals validation")
            print(f"- file: {signals_file}")
            for error in errors:
                print(f"- {error}")
            return EXIT_FAIL

        print("PASS: research signals validation")
        print(f"- file: {signals_file}")
        print(f"- ci_status: {payload['ci_status']}")
        print(f"- golden_checksum_short: {payload['golden_checksum_short']}")
        return EXIT_PASS
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return EXIT_FAIL
    except Exception as exc:  # pragma: no cover
        print(f"INTERNAL ERROR: {exc}")
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
