#!/usr/bin/env python3
"""Aggregate and enforce web-fallback remote proof contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import render_json, write_json
except ImportError:
    from script_io import render_json, write_json
from typing import Dict, Optional

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from scripts.ci import remote_proof_contract


def _detect_latest_branch_convergence_dir(repo_root: Path) -> Path:
    base = repo_root / "ops" / "reports" / "branch-convergence-v1"
    if not base.is_dir():
        raise remote_proof_contract.RemoteProofValidationError(
            "proof-dir not provided and ops/reports/branch-convergence-v1 does not exist"
        )
    candidates = sorted([path for path in base.iterdir() if path.is_dir()])
    if not candidates:
        raise remote_proof_contract.RemoteProofValidationError(
            "proof-dir not provided and no branch-convergence run directory exists"
        )
    return candidates[-1]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate remote CI + branch-protection web proofs.")
    parser.add_argument("--proof-dir", help="Directory containing REMOTE_PROOF_CI_WEB.json and REMOTE_PROOF_BRANCH_PROTECTION_WEB.json")
    parser.add_argument("--repo-root", default=".", help="Repository root path (default: .)")
    parser.add_argument("--output", help="Optional output path for REMOTE_PROOF_SUMMARY.json")
    return parser.parse_args()


def _summary(
    ci_result: Dict[str, object],
    branch_result: Dict[str, object],
    expected_origin_main_sha: str,
    proof_dir: Path,
) -> Dict[str, object]:
    ci_pass = ci_result.get("status") == "PASS"
    branch_pass = branch_result.get("status") == "PASS"
    commit_match = bool(ci_result.get("commit_match"))
    verdict = "PASS" if (ci_pass and branch_pass and commit_match) else "FAIL"
    return {
        "ci_proof": "PASS" if ci_pass else "FAIL",
        "branch_protection_proof": "PASS" if branch_pass else "FAIL",
        "commit_match": commit_match,
        "expected_origin_main_sha": expected_origin_main_sha,
        "proof_dir": str(proof_dir),
        "ci_proof_file": str(proof_dir / "REMOTE_PROOF_CI_WEB.json"),
        "branch_proof_file": str(proof_dir / "REMOTE_PROOF_BRANCH_PROTECTION_WEB.json"),
        "verdict": verdict,
        "errors": {
            "ci": ci_result.get("errors", []),
            "branch_protection": branch_result.get("errors", []),
        },
    }


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root).resolve()
    try:
        proof_dir = Path(args.proof_dir).resolve() if args.proof_dir else _detect_latest_branch_convergence_dir(repo_root)
        ci_file = proof_dir / "REMOTE_PROOF_CI_WEB.json"
        branch_file = proof_dir / "REMOTE_PROOF_BRANCH_PROTECTION_WEB.json"
        output_path = Path(args.output).resolve() if args.output else proof_dir / "REMOTE_PROOF_SUMMARY.json"

        ci_result = remote_proof_contract.validate_ci_file(ci_file, repo_root)
        branch_result = remote_proof_contract.validate_branch_file(branch_file)
        summary = _summary(
            ci_result=ci_result,
            branch_result=branch_result,
            expected_origin_main_sha=str(ci_result.get("expected_origin_main_sha", "")),
            proof_dir=proof_dir,
        )

        write_json(output_path, summary, ensure_ascii=True)
        print(render_json(summary, ensure_ascii=True))
        if summary["verdict"] == "PASS":
            return remote_proof_contract.EXIT_PASS
        return remote_proof_contract.EXIT_VIOLATION
    except remote_proof_contract.RemoteProofValidationError as exc:
        print(f"FAIL: remote proof aggregate internal validation error: {exc}")
        return remote_proof_contract.EXIT_INTERNAL
    except Exception as exc:  # pragma: no cover
        print(f"FAIL: unexpected internal error: {exc}")
        return remote_proof_contract.EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
