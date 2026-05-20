#!/usr/bin/env python3
"""Build the Independent Physics Backend Comparison artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mission.external_proof import (
    build_independent_physics_backend_comparison,
    validate_independent_physics_backend_comparison,
)


DEFAULT_OUTPUT = Path("artifacts/independent_physics_backend_comparison.v1.json")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


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

    payload = build_independent_physics_backend_comparison(repo_root)
    errors = validate_independent_physics_backend_comparison(payload, repo_root=repo_root)
    if not errors:
        _write_json(output, payload)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "output": str(output.relative_to(repo_root)),
        "analytic_check_count": payload.get("analytic_check_count"),
        "max_relative_error": payload.get("rollup", {}).get("max_relative_error"),
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: independent physics backend comparison artifact")
        print(f"- output: {result['output']}")
        print(f"- analytic_check_count: {result['analytic_check_count']}")
        print(f"- max_relative_error: {result['max_relative_error']}")
        for error in errors:
            print(f"- error: {error}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
