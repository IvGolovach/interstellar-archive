#!/usr/bin/env python3
"""Run realistic-only optimization engine v1 and emit audit artifacts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import render_output, write_text
except ImportError:
    from script_io import render_output, write_text
from typing import Any, Dict

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.optimization.engine_v1 import OptimizationConfig
from mission.optimization.runner import RunContext, execute_and_write


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3


def _default_run_id(repo_root: Path) -> str:
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short_sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    return f"{ts}-{short_sha}-optimization-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="mission/BASELINE_SCENARIO_v1.json")
    parser.add_argument("--plan", default="mission/OPTIMIZATION_PLAN_v1.json")
    parser.add_argument("--parameter-registry", default="parameters/registry/parameter_registry.v1.json")
    parser.add_argument("--parameter-claims", default="parameters/registry/parameter_claims.v1.json")
    parser.add_argument("--mode", default="realistic", choices=("realistic", "speculative"))
    parser.add_argument("--samples", type=int, default=96)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--refine-top-k", type=int, default=8)
    parser.add_argument("--refine-steps", type=int, default=3)
    parser.add_argument("--output-root", default="ops/reports/optimization-v1")
    parser.add_argument("--run-id")
    parser.add_argument("--verify-deterministic", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def _render_text(payload: Dict[str, Any]) -> str:
    lines = [
        "PASS: optimization run",
        f"- run_id: {payload['run_id']}",
        f"- output_dir: {payload['output_dir']}",
        f"- best_core_probability: {payload['best_core_probability']:.12f}",
        f"- trust_weighted_score: {payload['trust_weighted_score']:.12f}",
        f"- pareto_size: {payload['pareto_size']}",
        f"- pack_hash: {payload['pack_hash']}",
        f"- determinism_verdict: {payload['determinism']['verdict']}",
        f"- negative_proof_verdict: {payload['negative_proof']['verdict']}",
        f"- final_verdict: {payload['meta']['verdict']}",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = REPO_ROOT

    if args.mode != "realistic":
        print("FAIL: Optimization Engine v1 supports only --mode realistic")
        return EXIT_VIOLATION

    run_id = args.run_id or _default_run_id(repo_root)
    output_dir = (repo_root / args.output_root / run_id).resolve()

    context = RunContext(
        repo_root=repo_root,
        scenario_path=(repo_root / args.scenario).resolve(),
        plan_path=(repo_root / args.plan).resolve(),
        parameter_registry_path=(repo_root / args.parameter_registry).resolve(),
        parameter_claims_path=(repo_root / args.parameter_claims).resolve(),
    )

    config = OptimizationConfig(
        mode=args.mode,
        samples=int(args.samples),
        seed=int(args.seed),
        refine_top_k=int(args.refine_top_k),
        refine_steps=int(args.refine_steps),
    )

    try:
        result = execute_and_write(
            context=context,
            config=config,
            output_dir=output_dir,
            run_id=run_id,
            verify_deterministic=bool(args.verify_deterministic),
        )

        rendered = render_output(result, output_format=args.format, text_renderer=_render_text)
        print(rendered)

        if args.output:
            write_text(Path(args.output), rendered)

        return EXIT_PASS if result["meta"]["verdict"] == "PASS" else EXIT_VIOLATION
    except ValueError as exc:
        message = f"FAIL: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_VIOLATION
    except Exception as exc:  # noqa: BLE001
        message = f"INTERNAL ERROR: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
