#!/usr/bin/env python3
"""Build the deterministic Uncertainty Interactions artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.uncertainty import build_uncertainty_interactions, validate_uncertainty_interactions


DEFAULT_OUTPUT = Path("artifacts/uncertainty_interactions.v1.json")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = repo_root / output
    payload = build_uncertainty_interactions(repo_root)
    errors = validate_uncertainty_interactions(payload)
    if not errors:
        _write_json(output, payload)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "output": str(output.relative_to(repo_root)),
        "uncertainty_entry_count": payload.get("uncertainty_entry_count"),
        "interaction_pair_count": payload.get("interaction_pair_count"),
        "dominant_pair_id": payload.get("rollup", {}).get("dominant_pair_id"),
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: uncertainty interactions artifact")
        print(f"- output: {result['output']}")
        print(f"- uncertainty_entry_count: {result['uncertainty_entry_count']}")
        print(f"- interaction_pair_count: {result['interaction_pair_count']}")
        print(f"- dominant_pair_id: {result['dominant_pair_id']}")
        for error in errors:
            print(f"- error: {error}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
