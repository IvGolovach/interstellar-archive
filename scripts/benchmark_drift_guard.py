#!/usr/bin/env python3
"""Detect silent golden drift against baseline registry history."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List

try:
    from .script_io import load_json, render_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_json, render_output, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "benchmarks" / "baseline_registry.json"
SCHEMA_PATH = REPO_ROOT / "sim" / "schema" / "sim_schema.v1.json"
TYPES_PATH = REPO_ROOT / "sim" / "core" / "types.ts"
GOLDEN_CHECKSUM_PATH = REPO_ROOT / "sim" / "golden" / "golden_checksum.txt"
GOLDEN_OUTPUT_PATH = REPO_ROOT / "sim" / "golden" / "golden_output.v1.json"


class DriftGuardError(RuntimeError):
    """Raised when drift constraints are violated."""


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = load_json(path)
    except FileNotFoundError as exc:
        raise DriftGuardError(f"missing required file: {path.relative_to(REPO_ROOT)}") from exc
    except ValueError as exc:
        raise DriftGuardError(f"invalid JSON in {path.relative_to(REPO_ROOT)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DriftGuardError(f"{path.relative_to(REPO_ROOT)} must contain a top-level JSON object")
    return payload


def _load_engine_version() -> str:
    text = TYPES_PATH.read_text(encoding="utf-8")
    match = re.search(r'SIM_ENGINE_VERSION\s*=\s*"(v\d+)"', text)
    if not match:
        raise DriftGuardError("SIM_ENGINE_VERSION not found in sim/core/types.ts")
    return match.group(1)


def _required_fields(entry: Dict[str, Any]) -> List[str]:
    required = [
        "baseline_id",
        "metric_name",
        "metric_value",
        "date",
        "engine_version",
        "schema_version",
        "golden_checksum",
        "timestamp_utc",
        "commit_sha",
    ]
    return [field for field in required if field not in entry]


def validate_guard() -> Dict[str, Any]:
    baseline = _read_json(BASELINE_PATH)
    schema = _read_json(SCHEMA_PATH)
    golden_output = _read_json(GOLDEN_OUTPUT_PATH)

    entries = baseline.get("entries")
    if not isinstance(entries, list) or not entries:
        raise DriftGuardError("baseline_registry.json must contain non-empty entries list")

    for entry in entries:
        if not isinstance(entry, dict):
            raise DriftGuardError("baseline entry must be an object")
        missing = _required_fields(entry)
        if missing:
            raise DriftGuardError(f"baseline entry missing required fields: {', '.join(missing)}")

    current_engine_version = _load_engine_version()
    current_schema_version = str(schema.get("schema_version", "")).strip()
    if not current_schema_version:
        raise DriftGuardError("schema_version missing in sim/schema/sim_schema.v1.json")

    current_golden_checksum = GOLDEN_CHECKSUM_PATH.read_text(encoding="utf-8").strip()
    if not current_golden_checksum:
        raise DriftGuardError("sim/golden/golden_checksum.txt is empty")

    golden_output_checksum = str(golden_output.get("golden_checksum", "")).strip()
    if golden_output_checksum != current_golden_checksum:
        raise DriftGuardError(
            "golden output checksum mismatch: "
            f"output={golden_output_checksum} file={current_golden_checksum}"
        )

    relevant_entries = [
        entry
        for entry in entries
        if str(entry.get("engine_version")) == current_engine_version
        and str(entry.get("schema_version")) == current_schema_version
    ]
    if not relevant_entries:
        raise DriftGuardError(
            "baseline registry has no entries for current engine/schema: "
            f"engine={current_engine_version}, schema={current_schema_version}"
        )

    checksums = {str(entry.get("golden_checksum")) for entry in relevant_entries}
    if len(checksums) > 1:
        raise DriftGuardError(
            "detected multiple golden checksums for identical engine/schema version; "
            "drift without version bump is not allowed"
        )

    expected_checksum = checksums.pop()
    if expected_checksum != current_golden_checksum:
        raise DriftGuardError(
            "current golden checksum differs from baseline for same engine/schema version: "
            f"baseline={expected_checksum}, current={current_golden_checksum}"
        )

    latest_entry = max(relevant_entries, key=lambda item: str(item.get("timestamp_utc", "")))
    commit_sha = str(latest_entry.get("commit_sha", "")).strip()
    if commit_sha != "HEAD" and len(commit_sha) < 7:
        raise DriftGuardError("baseline commit_sha must be 'HEAD' or a commit SHA with at least 7 chars")

    return {
        "status": "PASS",
        "engine_version": current_engine_version,
        "schema_version": current_schema_version,
        "golden_checksum": current_golden_checksum,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def _render_text(payload: Dict[str, Any]) -> str:
    return (
        "PASS: benchmark drift guard "
        f"(engine={payload['engine_version']}, schema={payload['schema_version']}, checksum={payload['golden_checksum']})"
    )


def main() -> int:
    args = parse_args()
    try:
        payload = validate_guard()
        rendered = render_output(payload, output_format=args.format, text_renderer=_render_text)
        print(rendered)
        if args.output:
            write_text(Path(args.output), rendered)
    except DriftGuardError as exc:
        message = f"FAIL: benchmark drift guard: {exc}"
        if args.format == "json":
            rendered = render_json({"status": "FAIL", "error": str(exc)})
            print(rendered)
            if args.output:
                write_text(Path(args.output), rendered)
        else:
            print(message)
            if args.output:
                write_text(Path(args.output), message)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
