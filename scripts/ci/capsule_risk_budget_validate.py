#!/usr/bin/env python3
"""Validate the deterministic Capsule Risk Budget v2 artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_json
except ImportError:
    from script_io import load_json, render_json

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from mission.survivability.risk_budget import validate_capsule_risk_budget_artifact


DEFAULT_ARTIFACT = Path("artifacts/capsule_risk_budget.v1.json")


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
    artifact_path = Path(args.artifact)
    payload = load_json(repo_root / artifact_path)
    errors = validate_capsule_risk_budget_artifact(payload)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "artifact": str(artifact_path),
        "error_count": len(errors),
        "errors": errors,
    }
    if args.format == "json":
        print(render_json(result))
    else:
        print(f"{result['status']}: capsule risk budget validation")
        print(f"- artifact: {result['artifact']}")
        print(f"- error_count: {result['error_count']}")
        for error in errors:
            print(f"  - {error}")
    return 0 if not errors or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
