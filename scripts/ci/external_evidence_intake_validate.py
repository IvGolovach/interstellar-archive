#!/usr/bin/env python3
"""Validate the External Evidence Intake artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mission.external_reproduction import validate_external_evidence_intake


DEFAULT_ARTIFACT = Path("artifacts/external_evidence_intake.v1.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--records-dir")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    artifact = Path(args.artifact)
    if not artifact.is_absolute():
        artifact = repo_root / artifact
    records_dir = Path(args.records_dir).resolve() if args.records_dir else None
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    errors = validate_external_evidence_intake(payload, repo_root=repo_root, records_dir=records_dir)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "artifact": str(artifact.relative_to(repo_root)),
        "record_count": payload.get("record_count"),
        "accepted_record_count": payload.get("accepted_record_count"),
        "error_count": len(errors),
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: external evidence intake validation")
        print(f"- artifact: {result['artifact']}")
        print(f"- record_count: {result['record_count']}")
        print(f"- accepted_record_count: {result['accepted_record_count']}")
        print(f"- error_count: {result['error_count']}")
        for error in errors:
            print(f"- error: {error}")
    return 0 if not errors or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
