#!/usr/bin/env python3
"""Validate the consolidated browser-facing dataset artifact."""

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
import sys
from typing import Any, Dict

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from scripts.build_browser_dataset_artifact import validate_browser_dataset


DEFAULT_BROWSER_DATASET = Path("artifacts/browser_dataset.v1.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--browser-dataset", default=str(DEFAULT_BROWSER_DATASET))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true", default=True)
    parser.add_argument("--no-strict", dest="strict", action="store_false")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    browser_dataset_path = (repo_root / args.browser_dataset).resolve()

    payload = load_json(browser_dataset_path)
    errors = validate_browser_dataset(payload=payload, repo_root=repo_root)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "browser_dataset": str(Path(args.browser_dataset)),
        "error_count": len(errors),
        "errors": errors,
    }

    if args.format == "json":
        print(render_json(result))
    else:
        print(f"{result['status']}: browser dataset validation")
        print(f"- browser_dataset: {result['browser_dataset']}")
        print(f"- error_count: {result['error_count']}")
        for error in errors:
            print(f"  - {error}")

    if errors and args.strict:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
