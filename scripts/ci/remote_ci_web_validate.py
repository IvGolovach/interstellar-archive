#!/usr/bin/env python3
"""Validate web-fallback CI proof for main branch."""

from __future__ import annotations

import argparse
import sys
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

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from scripts.ci import remote_proof_contract


def _render_text(result: Dict[str, Any]) -> str:
    status = result["status"]
    lines = [f"{status}: remote CI web proof validation"]
    lines.append(f"- proof_file: {result.get('proof_file', '<unknown>')}")
    lines.append(f"- expected_origin_main_sha: {result.get('expected_origin_main_sha', '<unknown>')}")
    lines.append(f"- commit_match: {result.get('commit_match')}")
    if result.get("required_contexts_present") is not None:
        lines.append("- required_contexts_present: " + ", ".join(result.get("required_contexts_present") or []))
    if result.get("errors"):
        lines.append("- errors:")
        for err in result["errors"]:
            lines.append(f"  - {err}")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate REMOTE_PROOF_CI_WEB.json against origin/main.")
    parser.add_argument("--proof-file", required=True, help="Path to REMOTE_PROOF_CI_WEB.json")
    parser.add_argument("--repo-root", default=".", help="Repository root path (default: .)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output", help="Optional path to write rendered output")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    proof_file = Path(args.proof_file)
    repo_root = Path(args.repo_root)
    try:
        result = remote_proof_contract.validate_ci_file(proof_file, repo_root)
        status = result["status"]
        rendered = render_output(
            result,
            output_format=args.format,
            text_renderer=_render_text,
            ensure_ascii=True,
        )
        if args.output:
            write_text(Path(args.output), rendered)
        print(rendered)
        return remote_proof_contract.EXIT_PASS if status == "PASS" else remote_proof_contract.EXIT_VIOLATION
    except remote_proof_contract.RemoteProofValidationError as exc:
        print(f"FAIL: remote CI web proof internal validation error: {exc}")
        return remote_proof_contract.EXIT_INTERNAL
    except Exception as exc:  # pragma: no cover
        print(f"FAIL: unexpected internal error: {exc}")
        return remote_proof_contract.EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
