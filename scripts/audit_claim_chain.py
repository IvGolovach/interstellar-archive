#!/usr/bin/env python3
"""Audit claim traceability and numeric consistency."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
import sys
from typing import Any, Dict, List, Sequence, Tuple

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from models.evidence_io import (
    REFS_BIB_PATH,
    load_assumptions,
    load_claims,
    load_sources,
    parse_bibliography_keys,
    value_at_path,
)


def _parse_ref(ref: str) -> Tuple[Path, int]:
    if ":" not in ref:
        raise ValueError(f"invalid reference format: {ref}")
    file_part, line_part = ref.rsplit(":", 1)
    line_no = int(line_part)
    return REPO_ROOT / file_part, line_no


def _validate_reference(ref: str) -> str | None:
    try:
        file_path, line_no = _parse_ref(ref)
    except Exception as exc:  # noqa: BLE001
        return f"{ref}: {exc}"
    if not file_path.exists():
        return f"{ref}: file does not exist"
    line_count = sum(1 for _ in file_path.open("r", encoding="utf-8"))
    if line_no <= 0 or line_no > line_count:
        return f"{ref}: line out of range 1..{line_count}"
    return None


def _check_claim_fields(claim: Dict[str, Any], required: Sequence[str]) -> List[str]:
    errors: List[str] = []
    for key in required:
        if key not in claim:
            errors.append(f"{claim.get('id', '<missing-id>')}: missing field '{key}'")
    return errors


def _validate_check_contract(claim: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    verification_mode = claim.get("verification_mode", "numeric")
    checks = claim["checks"]

    if checks:
        if verification_mode == "qualitative":
            errors.append(f"{claim['id']}: qualitative claim must not define numeric checks")
        return errors

    if verification_mode != "qualitative":
        errors.append(f"{claim['id']}: missing checks without qualitative verification_mode")
    return errors


def _validate_model(model_def: Dict[str, str]) -> str | None:
    module = importlib.import_module(model_def["module"])
    function_name = model_def["function"]
    if not hasattr(module, function_name):
        return f"model function missing: {model_def['module']}.{function_name}"
    return None


def _validate_numeric_checks(
    claim_id: str,
    claim_values: Dict[str, Any],
    checks: Sequence[Dict[str, Any]],
) -> List[str]:
    errors: List[str] = []
    for check in checks:
        path = check["path"]
        value = float(value_at_path(claim_values, path))
        minimum = float(check["min"])
        maximum = float(check["max"])
        if not minimum <= value <= maximum:
            errors.append(
                f"{claim_id}:{path} value={value:.9g} outside [{minimum:.9g}, {maximum:.9g}]"
            )
    return errors


def _validate_artifacts(claim: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for artifact_rel in claim["artifacts"]:
        artifact_path = REPO_ROOT / artifact_rel
        if not artifact_path.exists():
            errors.append(f"{claim['id']}: missing artifact {artifact_rel}")
    return errors


def _validate_bibliography_sources(sources: Dict[str, Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    bib_keys = parse_bibliography_keys(REFS_BIB_PATH.read_text(encoding="utf-8"))
    for source in sources.values():
        if source["kind"] != "bibliography":
            continue
        key = source.get("cite_key")
        if not key:
            errors.append(f"{source['id']}: bibliography source missing cite_key")
            continue
        if key not in bib_keys:
            errors.append(f"{source['id']}: cite_key '{key}' not found in refs/bibliography.bib")
    return errors


def audit(skip_artifacts: bool) -> int:
    claim_registry = load_claims()
    claims = claim_registry["claims"]
    assumptions = load_assumptions()
    sources = load_sources()

    errors: List[str] = []
    claim_ids = [claim["id"] for claim in claims]
    if len(set(claim_ids)) != len(claim_ids):
        errors.append("duplicate claim IDs detected")
    assumption_ids = set(assumptions.keys())
    source_ids = set(sources.keys())

    errors.extend(_validate_bibliography_sources(sources))

    required_fields = (
        "id",
        "statement",
        "whitepaper_refs",
        "assumption_ids",
        "source_ids",
        "model",
        "artifacts",
        "checks",
    )

    model_invokers: Dict[Tuple[str, str], Any] = {}
    claim_values_cache_by_model: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}

    for claim in claims:
        field_errors = _check_claim_fields(claim, required_fields)
        errors.extend(field_errors)
        if field_errors:
            continue
        errors.extend(_validate_check_contract(claim))

        for assumption_id in claim["assumption_ids"]:
            if assumption_id not in assumption_ids:
                errors.append(f"{claim['id']}: unknown assumption_id {assumption_id}")
        for source_id in claim["source_ids"]:
            if source_id not in source_ids:
                errors.append(f"{claim['id']}: unknown source_id {source_id}")

        for ref in claim["whitepaper_refs"]:
            ref_error = _validate_reference(ref)
            if ref_error:
                errors.append(f"{claim['id']}: invalid whitepaper ref {ref_error}")

        model_key = (claim["model"]["module"], claim["model"]["function"])
        if model_key not in model_invokers:
            model_error = _validate_model(claim["model"])
            if model_error:
                errors.append(f"{claim['id']}: {model_error}")
                continue
            module = importlib.import_module(claim["model"]["module"])
            model_invokers[model_key] = getattr(module, claim["model"]["function"])

        if model_key not in claim_values_cache_by_model:
            invoker = model_invokers[model_key]
            claim_values_cache_by_model[model_key] = invoker()
        claim_values_cache = claim_values_cache_by_model[model_key]

        if claim["id"] not in claim_values_cache:
            errors.append(f"{claim['id']}: missing computed values in model output")
            continue

        errors.extend(
            _validate_numeric_checks(
                claim_id=claim["id"],
                claim_values=claim_values_cache[claim["id"]],
                checks=claim["checks"],
            )
        )

        if not skip_artifacts:
            errors.extend(_validate_artifacts(claim))

    total_checks = sum(len(claim["checks"]) for claim in claims)
    if errors:
        print("AUDIT FAILED")
        for item in errors:
            print(f"- {item}")
        print(f"Summary: claims={len(claims)} checks={total_checks} errors={len(errors)}")
        return 1

    print("AUDIT PASSED")
    print(
        f"Summary: claims={len(claims)} checks={total_checks} assumptions={len(assumptions)} sources={len(sources)}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-artifacts",
        action="store_true",
        help="Skip artifact file existence checks.",
    )
    args = parser.parse_args()
    return audit(skip_artifacts=args.skip_artifacts)


if __name__ == "__main__":
    raise SystemExit(main())
