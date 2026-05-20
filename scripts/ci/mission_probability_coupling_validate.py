#!/usr/bin/env python3
"""Validate the Mission Probability Coupling artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from mission.probability import validate_mission_probability_coupling


DEFAULT_ARTIFACT = Path("artifacts/mission_probability_coupling.v1.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact = Path(args.artifact)
    if not artifact.is_absolute():
        artifact = REPO_ROOT / artifact
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    errors = validate_mission_probability_coupling(payload)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "artifact": str(artifact.relative_to(REPO_ROOT)),
        "coupling_count": payload.get("coupling_count"),
        "error_count": len(errors),
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: mission probability coupling validation")
        print(f"- artifact: {result['artifact']}")
        print(f"- coupling_count: {result['coupling_count']}")
        print(f"- error_count: {result['error_count']}")
        for error in errors:
            print(f"- error: {error}")
    return 0 if not errors or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
