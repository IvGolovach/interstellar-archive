#!/usr/bin/env python3
"""CLI wrapper for mission parameter-domain guardrails."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import render_output, write_text
except ImportError:
    from script_io import render_output, write_text

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from mission.guards.parameter_domain import (
    DEFAULT_MISSION_SCRIPT,
    DEFAULT_PARAMETER_CLAIMS,
    DEFAULT_PARAMETER_REGISTRY,
    DEFAULT_SCENARIO,
    run_guard,
)


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3


def _render_text(payload):
    lines = [
        f"{payload['status']}: parameter domain guard",
        f"- realistic_mode_verified: {payload['realistic_mode_verified']}",
        f"- speculative_mode_enabled: {payload['speculative_mode_enabled']}",
        f"- divergence_multiplier: {float(payload['divergence_multiplier']):.6g}",
        f"- divergence_threshold: {float(payload['divergence_threshold']):.6g}",
    ]
    errors = payload.get("errors", [])
    if errors:
        lines.append("- errors:")
        for error in errors:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--parameter-registry", default=str(DEFAULT_PARAMETER_REGISTRY))
    parser.add_argument("--parameter-claims", default=str(DEFAULT_PARAMETER_CLAIMS))
    parser.add_argument("--scenario", default=str(DEFAULT_SCENARIO))
    parser.add_argument("--mission-script", default=str(DEFAULT_MISSION_SCRIPT))
    parser.add_argument("--divergence-threshold", type=float, default=20.0)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    try:
        result = run_guard(
            repo_root=repo_root,
            parameter_registry_path=Path(args.parameter_registry),
            parameter_claims_path=Path(args.parameter_claims),
            scenario_path=Path(args.scenario),
            mission_script_path=Path(args.mission_script),
            divergence_threshold=float(args.divergence_threshold),
        )
        rendered = render_output(result, output_format=args.format, text_renderer=_render_text)
        print(rendered)
        if args.output:
            write_text(Path(args.output), rendered)
        if result["status"] == "PASS":
            return EXIT_PASS
        return EXIT_VIOLATION if args.strict else EXIT_PASS
    except Exception as exc:  # noqa: BLE001
        message = f"INTERNAL ERROR: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
