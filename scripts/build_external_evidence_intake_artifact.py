#!/usr/bin/env python3
"""Build the External Evidence Intake artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mission.external_reproduction import build_external_evidence_intake, validate_external_evidence_intake


DEFAULT_OUTPUT = Path("artifacts/external_evidence_intake.v1.json")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--records-dir")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = repo_root / output
    records_dir = Path(args.records_dir).resolve() if args.records_dir else None

    payload = build_external_evidence_intake(repo_root, records_dir=records_dir)
    errors = validate_external_evidence_intake(payload, repo_root=repo_root, records_dir=records_dir)
    if not errors:
        _write_json(output, payload)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "output": str(output.relative_to(repo_root)),
        "record_count": payload.get("record_count"),
        "accepted_record_count": payload.get("accepted_record_count"),
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: external evidence intake artifact")
        print(f"- output: {result['output']}")
        print(f"- record_count: {result['record_count']}")
        print(f"- accepted_record_count: {result['accepted_record_count']}")
        for error in errors:
            print(f"- error: {error}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
