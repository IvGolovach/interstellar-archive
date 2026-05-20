#!/usr/bin/env python3
"""Build the deterministic Mission Feasibility Screen artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mission.feasibility import build_feasibility_screen, validate_feasibility_screen


DEFAULT_OUTPUT = Path("artifacts/mission_feasibility_screen.v1.json")


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

    payload = build_feasibility_screen(repo_root)
    errors = validate_feasibility_screen(payload)
    if not errors:
        _write_json(output, payload)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "output": str(output.relative_to(repo_root)),
        "scenario_count": payload.get("scenario_count"),
        "default_black_hole_flight_years": payload.get("default_black_hole_flight_years"),
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: mission feasibility screen artifact")
        print(f"- output: {result['output']}")
        print(f"- scenario_count: {result['scenario_count']}")
        print(f"- default_black_hole_flight_years: {result['default_black_hole_flight_years']}")
        for error in errors:
            print(f"- error: {error}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
