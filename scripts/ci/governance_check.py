#!/usr/bin/env python3
"""Deterministic governance enforcement entrypoint."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import render_json as render_json_output, write_text
except ImportError:
    from script_io import render_json as render_json_output, write_text


REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from scripts.ci.governance.report import render_json, render_text
from scripts.ci.governance.rules import run_governance_checks


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base commit SHA for diff range")
    parser.add_argument("--head", required=True, help="Head commit SHA for diff range")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root path (default: current directory)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format",
    )
    parser.add_argument("--output", help="Optional output file path")
    parser.add_argument("--strict", action="store_true", default=True, help="Fail on violations (default: true)")
    parser.add_argument("--no-strict", action="store_true", help="Report violations without non-zero exit code")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    strict = args.strict and not args.no_strict
    repo_root = Path(args.repo_root).resolve()
    base = args.base
    if base == "0000000000000000000000000000000000000000":
        parent = subprocess.run(
            ["git", "rev-parse", f"{args.head}^"],
            cwd=repo_root,
            env={**os.environ, "LANG": "C", "LC_ALL": "C"},
            text=True,
            capture_output=True,
            check=False,
        )
        if parent.returncode == 0:
            base = parent.stdout.strip()
        else:
            base = args.head
    try:
        result = run_governance_checks(repo_root=repo_root, base=base, head=args.head)
    except Exception as exc:  # noqa: BLE001
        message = f"INTERNAL ERROR: {exc}"
        if args.format == "json":
            payload = render_json_output(
                {
                    "status": "FAIL",
                    "base": base,
                    "head": args.head,
                    "violations": [],
                    "notes": [message],
                },
                sort_keys=False,
            )
            print(payload)
            if args.output:
                write_text(Path(args.output), payload)
        else:
            print(message)
            if args.output:
                write_text(Path(args.output), message)
        return EXIT_INTERNAL

    rendered = render_json(result) if args.format == "json" else render_text(result)
    print(rendered)
    if args.output:
        write_text(Path(args.output), rendered)

    if result.status == "PASS":
        return EXIT_PASS
    if strict:
        return EXIT_VIOLATION
    return EXIT_PASS


if __name__ == "__main__":
    raise SystemExit(main())
