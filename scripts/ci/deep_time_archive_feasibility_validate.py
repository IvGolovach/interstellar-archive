#!/usr/bin/env python3
"""Validate the integrated Deep-Time Archive Feasibility artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from mission.deep_time import validate_deep_time_archive_feasibility
from scripts.script_io import load_json, render_json


DEFAULT_ARTIFACT = Path("artifacts/deep_time_archive_feasibility.v1.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true", default=True)
    parser.add_argument("--no-strict", dest="strict", action="store_false")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    artifact = Path(args.artifact)
    payload = load_json(repo_root / artifact)
    errors = validate_deep_time_archive_feasibility(payload, repo_root=repo_root)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "artifact": str(artifact),
        "error_count": len(errors),
        "errors": errors,
    }
    if args.format == "json":
        print(render_json(result))
    else:
        print(f"{result['status']}: deep-time archive feasibility validation")
        print(f"- artifact: {result['artifact']}")
        print(f"- error_count: {result['error_count']}")
        for error in errors:
            print(f"  - {error}")
    return 0 if not errors or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
