#!/usr/bin/env python3
"""Build deterministic public research signals payload."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

try:
    from .script_io import load_json, write_json
except ImportError:
    from script_io import load_json, write_json


EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_INTERNAL = 3


GOLDEN_CHECKSUM_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_LICENSE = "CC-BY-4.0"


def _read_object_json(path: Path) -> Dict[str, Any]:
    try:
        payload = load_json(path)
    except FileNotFoundError as exc:
        raise ValueError(f"missing required file: {path}") from exc
    except ValueError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level JSON object")
    return payload


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ValueError(f"missing required file: {path}") from exc


def _git_tag_exists(repo_root: Path, tag: str) -> bool:
    proc = subprocess.run(
        ["git", "tag", "-l", tag],
        cwd=repo_root,
        env={**os.environ, "LANG": "C", "LC_ALL": "C"},
        capture_output=True,
        check=False,
        text=True,
    )
    if proc.returncode != 0:
        raise ValueError(f"unable to resolve git tags: {proc.stderr.strip()}")
    return bool(proc.stdout.strip())


def _status_color(status: str) -> str:
    return "0b7d3b" if status == "passing" else "b02a37"


def _evidence_message(value: float) -> str:
    if value == 1.0:
        return "complete"
    return f"{value:.2f}"


def _resolve_domain_status(repo_root: Path) -> Dict[str, Any]:
    status_path = repo_root / "artifacts" / "domain_mode_status.json"
    if status_path.exists():
        return _read_object_json(status_path)

    proc = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "parameter_domain_guard.py"),
            "--strict",
            "--format",
            "json",
        ],
        cwd=repo_root,
        env={**os.environ, "LANG": "C", "LC_ALL": "C"},
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stdout.strip() or proc.stderr.strip() or f"exit={proc.returncode}"
        raise ValueError(f"cannot resolve domain mode status: {detail}")

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("parameter_domain_guard returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("parameter_domain_guard output must be JSON object")
    return payload


def _determinism_from_payload(payload: Dict[str, Any]) -> bool:
    return str(payload.get("message", "")).upper() == "PASS" and str(payload.get("golden_integrity_status", "")).upper() == "PASS"


def _evidence_from_payload(payload: Dict[str, Any]) -> Tuple[float, bool]:
    ratio_raw = payload.get("evidence_completeness_ratio")
    if not isinstance(ratio_raw, (float, int)):
        raise ValueError("artifacts/evidence_status_v1.json missing numeric evidence_completeness_ratio")
    ratio = float(ratio_raw)
    if ratio < 0 or ratio > 1:
        raise ValueError("evidence_completeness_ratio must be in range [0, 1]")
    status_ok = (
        str(payload.get("status", "")).upper() == "PASS"
        and int(payload.get("missing_evidence_count", 1)) == 0
        and int(payload.get("realistic_D_violations", 1)) == 0
    )
    return ratio, status_ok


def build_research_signals_payload(repo_root: Path, require_tag: bool = True) -> Dict[str, Any]:
    determinism_status = _read_object_json(repo_root / "artifacts" / "determinism_status.json")
    evidence_status = _read_object_json(repo_root / "artifacts" / "evidence_status_v1.json")
    domain_status = _resolve_domain_status(repo_root)
    model_version = _read_object_json(repo_root / "MODEL_VERSION.json")
    citation = _read_object_json(repo_root / "CITATION.cff")
    version = _read_text(repo_root / "VERSION")
    version_tag = f"v{version}"
    if require_tag and not _git_tag_exists(repo_root, version_tag):
        raise ValueError(f"required version tag not found: {version_tag}")

    golden_checksum = _read_text(repo_root / "sim" / "golden" / "golden_checksum.txt")
    if not GOLDEN_CHECKSUM_PATTERN.match(golden_checksum):
        raise ValueError("sim/golden/golden_checksum.txt must contain a 64-hex digest")

    determinism_verified = _determinism_from_payload(determinism_status)
    evidence_ratio, evidence_ok = _evidence_from_payload(evidence_status)
    realistic_mode_verified = bool(domain_status.get("realistic_mode_verified"))
    speculative_mode_enabled = bool(domain_status.get("speculative_mode_enabled"))
    domain_ok = str(domain_status.get("status", "")).upper() == "PASS" and realistic_mode_verified and speculative_mode_enabled
    ci_status = "passing" if (determinism_verified and evidence_ok and domain_ok) else "failing"
    golden_short = f"{golden_checksum[:7]}..."

    license_value = str(citation.get("license", "")).strip()
    if not license_value:
        raise ValueError("CITATION.cff missing license")
    if license_value != EXPECTED_LICENSE:
        raise ValueError(f"unexpected license in CITATION.cff: {license_value} (expected {EXPECTED_LICENSE})")

    payload: Dict[str, Any] = {
        "engine_version": str(model_version.get("engine_version", "")),
        "schema_version": str(model_version.get("schema_version", "")),
        "golden_checksum": golden_checksum,
        "golden_checksum_short": golden_short,
        "determinism_verified": determinism_verified,
        "evidence_completeness": evidence_ratio,
        "ci_status": ci_status,
        "realistic_mode_verified": realistic_mode_verified,
        "speculative_mode_enabled": speculative_mode_enabled,
        "last_verified_commit": str(determinism_status.get("last_verified_commit_sha", "unknown")),
        "version": version_tag,
        "license": license_value,
        "determinism_badge": {
            "label": "Determinism",
            "message": "Verified" if determinism_verified else "Failed",
            "color": _status_color(ci_status if determinism_verified else "failing"),
        },
        "golden_badge": {
            "label": "Golden",
            "message": golden_short,
            "color": "1b6ac9",
        },
        "evidence_badge": {
            "label": "Traceability",
            "message": _evidence_message(evidence_ratio),
            "color": "0b7d3b" if evidence_ok else "b02a37",
        },
        "ci_badge": {
            "label": "CI",
            "message": ci_status,
            "color": _status_color(ci_status),
        },
        "realistic_mode_badge": {
            "label": "Realistic Mode",
            "message": "Verified" if realistic_mode_verified else "Failed",
            "color": "0b7d3b" if realistic_mode_verified else "b02a37",
        },
        "speculative_mode_badge": {
            "label": "Speculative Mode",
            "message": "Enabled (Labeled)" if speculative_mode_enabled else "Disabled",
            "color": "1b6ac9" if speculative_mode_enabled else "b02a37",
        },
        "version_badge": {
            "label": "Version",
            "message": version_tag,
            "color": "465d84",
        },
        "license_badge": {
            "label": "License",
            "message": license_value,
            "color": "6a6a6a",
        },
    }
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or validate artifacts/research_signals.json")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--output", default="artifacts/research_signals.json", help="Output path relative to repo root")
    parser.add_argument("--check", action="store_true", help="Validate output file matches computed payload")
    parser.add_argument("--no-require-tag", action="store_true", help="Do not require matching vX.Y.Z git tag")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_path = (repo_root / args.output).resolve()
    try:
        payload = build_research_signals_payload(repo_root=repo_root, require_tag=not args.no_require_tag)
        if args.check:
            current = _read_object_json(output_path)
            if current != payload:
                print("FAIL: research_signals drift detected")
                print(f"- file: {output_path}")
                return EXIT_FAIL
            print("PASS: research_signals check")
            print(f"- file: {output_path}")
            return EXIT_PASS

        write_json(output_path, payload)
        print("PASS: research_signals built")
        print(f"- file: {output_path}")
        print(f"- determinism_verified: {payload['determinism_verified']}")
        print(f"- evidence_completeness: {payload['evidence_completeness']:.2f}")
        print(f"- ci_status: {payload['ci_status']}")
        return EXIT_PASS
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return EXIT_FAIL
    except Exception as exc:  # pragma: no cover
        print(f"INTERNAL ERROR: {exc}")
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
