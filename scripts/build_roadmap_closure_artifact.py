#!/usr/bin/env python3
"""Build the full v2 roadmap closure artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mission.roadmap import build_roadmap_closure, validate_roadmap_closure


DEFAULT_OUTPUT = Path("artifacts/roadmap_closure.v1.json")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


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

    payload = build_roadmap_closure(repo_root)
    errors = validate_roadmap_closure(payload)
    status = "PASS" if not errors else "FAIL"
    if not errors:
        _write_json(output, payload)

    result = {
        "status": status,
        "output": _display_path(output, repo_root),
        "roadmap_item_count": payload.get("roadmap_item_count"),
        "external_evidence_gap_count": payload.get("closure_metrics", {}).get("external_evidence_gap_count"),
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{status}: roadmap closure artifact")
        print(f"- output: {result['output']}")
        print(f"- roadmap_item_count: {result['roadmap_item_count']}")
        print(f"- external_evidence_gap_count: {result['external_evidence_gap_count']}")
        for error in errors:
            print(f"- error: {error}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
