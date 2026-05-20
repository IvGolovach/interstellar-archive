#!/usr/bin/env python3
"""Validate the full v2 roadmap closure artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mission.roadmap import validate_roadmap_closure


DEFAULT_ARTIFACT = Path("artifacts/roadmap_closure.v1.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact = Path(args.artifact)
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    errors = validate_roadmap_closure(payload)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "artifact": str(artifact),
        "error_count": len(errors),
        "roadmap_item_count": payload.get("roadmap_item_count"),
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: roadmap closure validation")
        print(f"- artifact: {artifact}")
        print(f"- roadmap_item_count: {result['roadmap_item_count']}")
        print(f"- error_count: {len(errors)}")
        for error in errors:
            print(f"- error: {error}")
    return 0 if not errors or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
