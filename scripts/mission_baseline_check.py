#!/usr/bin/env python3
"""Deterministic mission-definition v1 validator and baseline checker."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.baseline import ALLOWED_RUN_MODES, run_baseline


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and run mission-definition v1 baseline check.")
    parser.add_argument("--schema", default="mission/MISSION_SCHEMA_v1.json")
    parser.add_argument("--scenario", default="mission/BASELINE_SCENARIO_v1.json")
    parser.add_argument("--output", default=None)
    parser.add_argument("--mode", choices=sorted(ALLOWED_RUN_MODES), default="dual")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--verify-deterministic", action="store_true")

    args = parser.parse_args()
    output_path = Path(args.output) if args.output else None
    return run_baseline(
        schema_path=Path(args.schema),
        scenario_path=Path(args.scenario),
        mode=str(args.mode),
        validate_only=bool(args.validate_only),
        verify_deterministic=bool(args.verify_deterministic),
        output_path=output_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
