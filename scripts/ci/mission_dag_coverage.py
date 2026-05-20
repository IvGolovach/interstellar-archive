#!/usr/bin/env python3
"""Run Mission DAG tests and report statement coverage."""

from __future__ import annotations

import argparse
import ast
import os
import sys
import trace
import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple

try:
    from ._bootstrap import bootstrap_repo_root, ensure_repo_on_path
except ImportError:
    from _bootstrap import bootstrap_repo_root, ensure_repo_on_path
try:
    from .script_io import render_output, write_text
except ImportError:
    from script_io import render_output, write_text

REPO_ROOT = bootstrap_repo_root(__file__, levels=2, add_to_sys_path=False)
TARGETS = [
    REPO_ROOT / "mission" / "dag" / "__init__.py",
    REPO_ROOT / "mission" / "dag" / "contracts.py",
    REPO_ROOT / "mission" / "dag" / "hashchain.py",
    REPO_ROOT / "mission" / "dag" / "runner_v1.py",
]
DEFAULT_TESTS = [
    "tests.test_mission_dag_schema",
    "tests.test_mission_dag_determinism",
    "tests.test_mission_dag_contracts_unit",
    "tests.test_mission_dag_runner_branches",
    "tests.test_module_contract_enforcement",
    "tests.test_module_failure_taxonomy",
    "tests.test_mission_dag_realistic_speculative_isolation",
]


def _statement_lines(path: Path) -> Set[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines: Set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and hasattr(node, "lineno"):
            lines.add(int(node.lineno))
    return lines


def run_coverage(min_coverage: float) -> Tuple[bool, float, Dict[str, Dict[str, float]], bool]:
    tracer = trace.Trace(count=True, trace=False)

    def _execute() -> unittest.result.TestResult:
        suite = unittest.defaultTestLoader.loadTestsFromNames(DEFAULT_TESTS)
        runner = unittest.TextTestRunner(verbosity=1)
        return runner.run(suite)

    test_result = tracer.runfunc(_execute)
    trace_results = tracer.results()

    executed_by_file: Dict[str, Set[int]] = {}
    for (filename, lineno), _count in trace_results.counts.items():
        executed_by_file.setdefault(str(Path(filename).resolve()), set()).add(int(lineno))

    details: Dict[str, Dict[str, float]] = {}
    total_statements = 0
    total_executed = 0

    for target in TARGETS:
        if not target.exists():
            continue
        normalized = str(target.resolve())
        statements = _statement_lines(target)
        executed = executed_by_file.get(normalized, set())
        covered = len(statements & executed)
        total = len(statements)
        percent = 100.0 if total == 0 else (covered / total) * 100.0

        details[str(target.relative_to(REPO_ROOT))] = {
            "statements": float(total),
            "executed": float(covered),
            "coverage_percent": percent,
        }

        total_statements += total
        total_executed += covered

    overall = 100.0 if total_statements == 0 else (total_executed / total_statements) * 100.0
    passed = bool(test_result.wasSuccessful()) and overall >= min_coverage
    return passed, overall, details, bool(test_result.wasSuccessful())


def main() -> int:
    ensure_repo_on_path(REPO_ROOT)
    os.chdir(REPO_ROOT)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min", type=float, default=90.0)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    args = parser.parse_args()

    passed, overall, details, tests_ok = run_coverage(args.min)

    payload = {
        "status": "PASS" if passed else "FAIL",
        "tests_ok": tests_ok,
        "minimum_percent": args.min,
        "overall_percent": overall,
        "files": details,
    }

    def _render_text(payload: Dict[str, object]) -> str:
        lines: List[str] = [
            f"Mission DAG coverage status: {payload['status']}",
            f"Tests OK: {tests_ok}",
            f"Coverage: {overall:.2f}% (required >= {args.min:.2f}%)",
        ]
        for file_path, file_data in details.items():
            lines.append(
                f"- {file_path}: {file_data['coverage_percent']:.2f}% "
                f"({int(file_data['executed'])}/{int(file_data['statements'])})"
            )
        return "\n".join(lines)

    rendered = render_output(payload, output_format=args.format, text_renderer=_render_text)

    print(rendered)
    if args.output:
        write_text(Path(args.output), rendered)

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
