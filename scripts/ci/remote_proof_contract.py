#!/usr/bin/env python3
"""Shared contract validation for web-based remote CI and branch protection proofs."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

try:
    from .script_io import load_json
except ImportError:
    from script_io import load_json


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3


REQUIRED_CI_CONTEXTS = ("evidence", "governance", "verify-web-sim", "floating-point-stability")
REQUIRED_BRANCH_CHECKS = ("evidence", "governance")


class RemoteProofValidationError(RuntimeError):
    """Raised for internal validator errors."""


def _load_payload(path: Path) -> Dict[str, Any]:
    try:
        payload = load_json(path)
    except FileNotFoundError as exc:
        raise RemoteProofValidationError(f"missing proof file: {path}") from exc
    except ValueError as exc:
        raise RemoteProofValidationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RemoteProofValidationError(f"proof JSON must be an object: {path}")
    return payload


def _run_git(repo_root: Path, args: Sequence[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        env={**os.environ, "LANG": "C", "LC_ALL": "C"},
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RemoteProofValidationError(f"git {' '.join(args)} failed: {stderr}")
    return proc.stdout.decode("utf-8", errors="strict").strip()


def get_origin_main_sha(repo_root: Path) -> str:
    """Resolve the commit SHA used for remote-proof commit-match checks."""
    try:
        return _run_git(repo_root, ["rev-parse", "origin/main"])
    except RemoteProofValidationError:
        return _run_git(repo_root, ["rev-parse", "HEAD"])


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _to_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def _missing(items: Iterable[str], present: Iterable[str]) -> List[str]:
    present_set = set(present)
    return [item for item in items if item not in present_set]


def validate_ci_payload(
    payload: Mapping[str, Any],
    expected_origin_main_sha: str,
    required_contexts: Sequence[str] = REQUIRED_CI_CONTEXTS,
) -> Dict[str, Any]:
    """Validate CI proof payload from GitHub Web fallback."""
    errors: List[str] = []
    required_fields = [
        "source",
        "repository",
        "branch",
        "commit_sha",
        "actions_run_url",
        "run_status",
        "required_contexts_verified",
        "collected_at_utc",
    ]
    for field in required_fields:
        if field not in payload:
            errors.append(f"missing field: {field}")

    for field in ["source", "repository", "branch", "commit_sha", "actions_run_url", "run_status", "collected_at_utc"]:
        if field in payload and not _is_non_empty_string(payload.get(field)):
            errors.append(f"{field} must be non-empty string")

    if payload.get("branch") != "main":
        errors.append("branch must be 'main'")
    if payload.get("run_status") != "success":
        errors.append("run_status must be 'success'")

    commit_sha = str(payload.get("commit_sha", "")).strip()
    commit_match = commit_sha == expected_origin_main_sha
    if not commit_match:
        errors.append(
            "commit_sha mismatch: "
            f"proof={commit_sha or '<empty>'} expected={expected_origin_main_sha}"
        )

    contexts = _to_string_list(payload.get("required_contexts_verified"))
    if not contexts:
        errors.append("required_contexts_verified must be a non-empty list of strings")
    else:
        missing_required = _missing(required_contexts, contexts)
        if missing_required:
            errors.append(
                "required_contexts_verified missing required contexts: "
                + ", ".join(missing_required)
            )

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "errors": errors,
        "commit_match": commit_match,
        "expected_origin_main_sha": expected_origin_main_sha,
        "required_contexts_present": contexts,
    }


def validate_branch_payload(
    payload: Mapping[str, Any],
    required_status_checks: Sequence[str] = REQUIRED_BRANCH_CHECKS,
) -> Dict[str, Any]:
    """Validate branch protection proof payload from GitHub Web fallback."""
    errors: List[str] = []
    required_fields = [
        "source",
        "branch",
        "require_pr",
        "allow_force_pushes",
        "required_status_checks",
        "collected_at_utc",
    ]
    for field in required_fields:
        if field not in payload:
            errors.append(f"missing field: {field}")

    for field in ["source", "branch", "collected_at_utc"]:
        if field in payload and not _is_non_empty_string(payload.get(field)):
            errors.append(f"{field} must be non-empty string")

    if payload.get("branch") != "main":
        errors.append("branch must be 'main'")
    if payload.get("require_pr") is not True:
        errors.append("require_pr must be true")
    if payload.get("allow_force_pushes") is not False:
        errors.append("allow_force_pushes must be false")

    checks = _to_string_list(payload.get("required_status_checks"))
    if not checks:
        errors.append("required_status_checks must be a non-empty list of strings")
    else:
        missing_required = _missing(required_status_checks, checks)
        if missing_required:
            errors.append(
                "required_status_checks missing required checks: "
                + ", ".join(missing_required)
            )

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "errors": errors,
        "required_status_checks_present": checks,
    }


def validate_ci_file(ci_path: Path, repo_root: Path) -> Dict[str, Any]:
    payload = _load_payload(ci_path)
    expected_origin_main_sha = get_origin_main_sha(repo_root)
    result = validate_ci_payload(payload, expected_origin_main_sha=expected_origin_main_sha)
    result["proof_file"] = str(ci_path)
    return result


def validate_branch_file(branch_path: Path) -> Dict[str, Any]:
    payload = _load_payload(branch_path)
    result = validate_branch_payload(payload)
    result["proof_file"] = str(branch_path)
    return result
