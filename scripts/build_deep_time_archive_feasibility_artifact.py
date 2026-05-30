#!/usr/bin/env python3
"""Build the integrated Deep-Time Archive Feasibility artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from .script_io import render_json, write_json
except ImportError:
    from script_io import render_json, write_json

REPO_ROOT_FALLBACK = Path(__file__).resolve().parents[1]
if str(REPO_ROOT_FALLBACK) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FALLBACK))

from mission.deep_time import build_deep_time_archive_feasibility, validate_deep_time_archive_feasibility


DEFAULT_OUTPUT = Path("artifacts/deep_time_archive_feasibility.v1.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = repo_root / output
    payload = build_deep_time_archive_feasibility(repo_root)
    errors = validate_deep_time_archive_feasibility(payload, repo_root=repo_root)
    if not errors:
        write_json(output, payload)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "output": str(output.relative_to(repo_root)),
        "source_record_count": payload.get("rollup", {}).get("source_record_count"),
        "blocked_claim_count": payload.get("rollup", {}).get("blocked_claim_count"),
        "errors": errors,
    }
    if args.format == "json":
        print(render_json(result))
    else:
        print(f"{result['status']}: deep-time archive feasibility artifact")
        print(f"- output: {result['output']}")
        print(f"- source_record_count: {result['source_record_count']}")
        print(f"- blocked_claim_count: {result['blocked_claim_count']}")
        for error in errors:
            print(f"  - {error}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
