#!/usr/bin/env python3
"""Build machine-readable evidence status snapshot."""

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
    from .script_io import write_json
except ImportError:
    from script_io import write_json
from typing import Any, Dict


REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from scripts.ci.evidence_validate import (  # noqa: E402
    DEFAULT_CHANGELOG,
    DEFAULT_EVIDENCE_REGISTRY,
    DEFAULT_EVIDENCE_SCHEMA,
    DEFAULT_MISSION_SCHEMA,
    DEFAULT_UNCERTAINTY_MODEL,
    run_validation,
)


def _git_head(repo_root: Path) -> str:
    return (
        subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            env={**os.environ, "LANG": "C", "LC_ALL": "C"},
            text=True,
        )
        .strip()
    )


def build_status(repo_root: Path) -> Dict[str, Any]:
    head = _git_head(repo_root)
    result = run_validation(
        repo_root=repo_root,
        evidence_schema_path=DEFAULT_EVIDENCE_SCHEMA,
        evidence_registry_path=DEFAULT_EVIDENCE_REGISTRY,
        mission_schema_path=DEFAULT_MISSION_SCHEMA,
        uncertainty_model_path=DEFAULT_UNCERTAINTY_MODEL,
        changelog_path=DEFAULT_CHANGELOG,
        base=head,
        head=head,
    )

    trust_distribution = dict(result.trust_distribution)
    realistic_parameters = trust_distribution.get("A", 0) + trust_distribution.get("B", 0) + trust_distribution.get("C", 0)
    speculative_parameters = trust_distribution.get("D", 0)
    payload: Dict[str, Any] = {
        "schema_version": "evidence_status.v1",
        "status": result.status,
        "total_parameters": result.total_parameters,
        "realistic_parameters": realistic_parameters,
        "speculative_parameters": speculative_parameters,
        "trust_distribution": trust_distribution,
        "missing_evidence_count": result.missing_evidence_count,
        "evidence_completeness_ratio": result.evidence_completeness_ratio,
        "realistic_D_violations": result.realistic_d_violations,
    }
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--output", default="artifacts/evidence_status_v1.json", help="Output status JSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_path = (repo_root / args.output).resolve()
    status = build_status(repo_root=repo_root)
    write_json(output_path, status)
    print(f"Wrote evidence status: {output_path}")
    print(
        "Summary: "
        f"status={status['status']} total={status['total_parameters']} "
        f"missing={status['missing_evidence_count']} ratio={status['evidence_completeness_ratio']:.6f}"
    )
    return 0 if status["status"] == "PASS" and status["missing_evidence_count"] == 0 and status["realistic_D_violations"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
