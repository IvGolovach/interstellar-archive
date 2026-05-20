#!/usr/bin/env python3
"""Run evidence-validator tests and compute statement coverage."""

from __future__ import annotations

import argparse
import ast
import os
import sys
import trace
import unittest
from pathlib import Path
from typing import Dict, Set, Tuple

try:
    from ._bootstrap import bootstrap_repo_root, ensure_repo_on_path
except ImportError:
    from _bootstrap import bootstrap_repo_root, ensure_repo_on_path
try:
    from .script_io import render_output, write_text
except ImportError:
    from script_io import render_output, write_text

REPO_ROOT = bootstrap_repo_root(__file__, levels=2, add_to_sys_path=False)
TARGET_FILE = REPO_ROOT / "scripts" / "ci" / "evidence_validate.py"
DEFAULT_TESTS = [
    "tests.test_evidence_contract",
    "tests.test_evidence_negative_cases",
]


def _statement_lines(path: Path) -> Set[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines: Set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and hasattr(node, "lineno"):
            lines.add(int(node.lineno))
    return lines


def run_coverage(min_coverage: float) -> Tuple[bool, float, Dict[str, float], bool]:
    tracer = trace.Trace(count=True, trace=False)

    def _execute() -> unittest.result.TestResult:
        suite = unittest.defaultTestLoader.loadTestsFromNames(DEFAULT_TESTS)
        runner = unittest.TextTestRunner(verbosity=1)
        return runner.run(suite)

    test_result = tracer.runfunc(_execute)
    trace_results = tracer.results()
    executed: Set[int] = set()
    normalized = str(TARGET_FILE.resolve())
    for (filename, lineno), _count in trace_results.counts.items():
        if str(Path(filename).resolve()) == normalized:
            executed.add(int(lineno))

    statements = _statement_lines(TARGET_FILE)
    covered = len(statements & executed)
    total = len(statements)
    percent = 100.0 if total == 0 else (covered / total) * 100.0
    passed = bool(test_result.wasSuccessful()) and percent >= min_coverage
    details = {
        "statements": float(total),
        "executed": float(covered),
        "coverage_percent": percent,
    }
    return passed, percent, details, bool(test_result.wasSuccessful())


def main() -> int:
    ensure_repo_on_path(REPO_ROOT)
    os.chdir(REPO_ROOT)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min", type=float, default=95.0)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", help="Optional output file")
    args = parser.parse_args()

    passed, percent, details, tests_ok = run_coverage(args.min)
    payload = {
        "status": "PASS" if passed else "FAIL",
        "tests_ok": tests_ok,
        "minimum_percent": args.min,
        "overall_percent": percent,
        "file": str(TARGET_FILE.relative_to(REPO_ROOT)),
        "details": details,
    }
    def _render_text(payload: Dict[str, object]) -> str:
        return "\n".join(
            [
                f"Evidence coverage status: {payload['status']}",
                f"Tests OK: {tests_ok}",
                f"Coverage: {percent:.2f}% (required >= {args.min:.2f}%)",
                f"- {payload['file']}: {details['coverage_percent']:.2f}% ({int(details['executed'])}/{int(details['statements'])})",
            ]
        )
    rendered = render_output(payload, output_format=args.format, text_renderer=_render_text)
    print(rendered)
    if args.output:
        write_text(Path(args.output), rendered)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
