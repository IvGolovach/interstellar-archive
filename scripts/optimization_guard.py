#!/usr/bin/env python3
"""CLI wrapper for mission optimization guardrails."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.guards.optimization import validate_plan


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_PLAN = Path("mission/OPTIMIZATION_PLAN_v1.json")
DEFAULT_PARAMETER_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_PARAMETER_CLAIMS = Path("parameters/registry/parameter_claims.v1.json")


def _render_text(payload):
    lines = [
        f"{payload['status']}: optimization guard",
        f"- mode: {payload.get('mode')}",
        f"- tuned_parameters: {', '.join(payload.get('tuned_parameters', []))}",
        f"- accepted_parameters: {', '.join(payload.get('accepted_parameters', []))}",
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
    parser.add_argument("--plan", default=str(DEFAULT_PLAN))
    parser.add_argument("--parameter-registry", default=str(DEFAULT_PARAMETER_REGISTRY))
    parser.add_argument("--parameter-claims", default=str(DEFAULT_PARAMETER_CLAIMS))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    try:
        result = validate_plan(
            plan=load_json(repo_root / args.plan),
            registry=load_json(repo_root / args.parameter_registry),
            claims=load_json(repo_root / args.parameter_claims),
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
