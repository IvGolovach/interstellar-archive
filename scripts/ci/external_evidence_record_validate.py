#!/usr/bin/env python3
"""Validate one external evidence record JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mission.external_reproduction import validate_external_evidence_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    record_path = Path(args.record)
    if not record_path.is_absolute():
        record_path = repo_root / record_path
    record = json.loads(record_path.read_text(encoding="utf-8"))
    errors = validate_external_evidence_record(record, repo_root=repo_root)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "record": str(record_path.relative_to(repo_root)) if record_path.is_relative_to(repo_root) else str(record_path),
        "record_id": record.get("record_id"),
        "error_count": len(errors),
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: external evidence record validation")
        print(f"- record: {result['record']}")
        print(f"- record_id: {result['record_id']}")
        print(f"- error_count: {result['error_count']}")
        for error in errors:
            print(f"- error: {error}")
    return 0 if not errors or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
