#!/usr/bin/env python3
"""Validate parameter->evidence binding and trust rules."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Mapping, Set

try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3


DEFAULT_PARAMETER_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_EVIDENCE_SOURCES = Path("parameters/registry/evidence_sources.v1.json")
DEFAULT_PARAMETER_CLAIMS = Path("parameters/registry/parameter_claims.v1.json")

ALLOWED_SOURCE_TYPES = {"paper", "report", "dataset", "assumption"}
ALLOWED_TRUST = {"A", "B", "C", "D"}
ALLOWED_VALUE_MODE = {"scalar", "distribution"}
ALLOWED_MODE = {"realistic", "speculative", "both"}


def validate(
    parameter_registry: Mapping[str, Any],
    evidence_sources_payload: Mapping[str, Any],
    parameter_claims_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    parameters = parameter_registry.get("parameters")
    sources = evidence_sources_payload.get("sources")
    claims = parameter_claims_payload.get("claims")

    if parameter_registry.get("schema_version") != "parameter_registry.v1":
        errors.append("parameter registry schema_version must be parameter_registry.v1")
    if evidence_sources_payload.get("schema_version") != "evidence_sources.v1":
        errors.append("evidence sources schema_version must be evidence_sources.v1")
    if parameter_claims_payload.get("schema_version") != "parameter_claims.v1":
        errors.append("parameter claims schema_version must be parameter_claims.v1")

    if not isinstance(parameters, list) or not parameters:
        errors.append("parameter registry parameters must be non-empty list")
        parameters = []
    if not isinstance(sources, list) or not sources:
        errors.append("evidence sources must be non-empty list")
        sources = []
    if not isinstance(claims, list) or not claims:
        errors.append("parameter claims must be non-empty list")
        claims = []

    source_by_id: Dict[str, Dict[str, Any]] = {}
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be object")
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            errors.append(f"{prefix}.source_id must be non-empty string")
            continue
        if source_id in source_by_id:
            errors.append(f"{prefix}.source_id duplicated: {source_id}")
            continue
        source_by_id[source_id] = source

        source_type = source.get("type")
        if source_type not in ALLOWED_SOURCE_TYPES:
            errors.append(f"{prefix}.type '{source_type}' is invalid")
        for field in ("citation", "claim_scope", "notes"):
            value = source.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{field} must be non-empty string")
        url = source.get("url")
        if url is not None and (not isinstance(url, str) or not url.strip()):
            errors.append(f"{prefix}.url must be null or non-empty string")

    parameter_ids: Set[str] = set()
    parameter_meta: Dict[str, Dict[str, Any]] = {}
    for index, parameter in enumerate(parameters):
        prefix = f"parameters[{index}]"
        if not isinstance(parameter, dict):
            errors.append(f"{prefix} must be object")
            continue
        pid = parameter.get("parameter_id")
        if not isinstance(pid, str) or not pid.strip():
            errors.append(f"{prefix}.parameter_id must be non-empty string")
            continue
        parameter_ids.add(pid)
        parameter_meta[pid] = parameter

    claim_by_parameter: Dict[str, Dict[str, Any]] = {}
    trust_distribution = {grade: 0 for grade in ["A", "B", "C", "D"]}
    realistic_d_violations = 0

    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} must be object")
            continue

        pid = claim.get("parameter_id")
        if not isinstance(pid, str) or not pid.strip():
            errors.append(f"{prefix}.parameter_id must be non-empty string")
            continue
        if pid in claim_by_parameter:
            errors.append(f"{prefix}.parameter_id duplicated: {pid}")
        claim_by_parameter[pid] = claim

        if pid not in parameter_ids:
            errors.append(f"{prefix}.parameter_id '{pid}' not found in parameter registry")

        value_mode = claim.get("value_mode")
        if value_mode not in ALLOWED_VALUE_MODE:
            errors.append(f"{prefix}.value_mode '{value_mode}' is invalid")

        units = claim.get("units")
        if not isinstance(units, str) or not units.strip():
            errors.append(f"{prefix}.units must be non-empty string")
        elif pid in parameter_meta and isinstance(parameter_meta[pid].get("unit"), str):
            registry_unit = parameter_meta[pid]["unit"]
            if units != registry_unit:
                errors.append(f"{prefix}.units '{units}' must match registry unit '{registry_unit}'")

        mode = claim.get("mode")
        if mode not in ALLOWED_MODE:
            errors.append(f"{prefix}.mode '{mode}' is invalid")

        trust = claim.get("trust_grade")
        if trust not in ALLOWED_TRUST:
            errors.append(f"{prefix}.trust_grade '{trust}' is invalid")
        else:
            trust_distribution[trust] += 1

        if mode == "realistic" and trust == "D":
            realistic_d_violations += 1
            errors.append(f"{prefix}: realistic mode cannot use trust_grade D")
        if trust == "D" and mode != "speculative":
            errors.append(f"{prefix}: trust_grade D is only allowed for speculative mode")

        parameter_domain = str(parameter_meta.get(pid, {}).get("domain", ""))
        if trust == "D" and parameter_domain and parameter_domain != "speculative":
            errors.append(f"{prefix}: trust_grade D requires parameter domain=speculative")
        if mode == "realistic" and parameter_domain == "speculative":
            errors.append(f"{prefix}: realistic claim mode cannot target speculative-domain parameter")

        source_ids = claim.get("evidence_source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            errors.append(f"{prefix}.evidence_source_ids must be non-empty list")
            source_ids = []

        resolved_types: Set[str] = set()
        for source_id in source_ids:
            if not isinstance(source_id, str) or not source_id.strip():
                errors.append(f"{prefix}.evidence_source_ids contains invalid source id")
                continue
            source = source_by_id.get(source_id)
            if source is None:
                errors.append(f"{prefix}.evidence_source_ids contains unknown source '{source_id}'")
            else:
                resolved_types.add(str(source.get("type")))

        parameter = parameter_meta.get(pid)
        if parameter is not None:
            classification = parameter.get("classification")
            if classification == "assumed" and "assumption" not in resolved_types:
                errors.append(f"{prefix}: assumed classification requires at least one assumption source")

        justification = claim.get("justification")
        if not isinstance(justification, str) or len(justification.strip()) < 8:
            errors.append(f"{prefix}.justification must be at least 8 chars")
        reviewed = claim.get("last_reviewed_commit")
        if not isinstance(reviewed, str) or len(reviewed.strip()) < 7:
            errors.append(f"{prefix}.last_reviewed_commit must be commit SHA string")

    missing_claims = sorted(parameter_ids - set(claim_by_parameter.keys()))
    if missing_claims:
        errors.append("missing parameter claims for: " + ", ".join(missing_claims))

    total_parameters = len(parameter_ids)
    missing_evidence = len(missing_claims)
    completeness = 1.0 if total_parameters == 0 else (total_parameters - missing_evidence) / total_parameters

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "total_parameters": total_parameters,
        "missing_evidence_count": missing_evidence,
        "evidence_completeness_ratio": round(completeness, 6),
        "realistic_D_violations": realistic_d_violations,
        "trust_distribution": trust_distribution,
        "errors": errors,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--parameter-registry", default=str(DEFAULT_PARAMETER_REGISTRY))
    parser.add_argument("--evidence-sources", default=str(DEFAULT_EVIDENCE_SOURCES))
    parser.add_argument("--parameter-claims", default=str(DEFAULT_PARAMETER_CLAIMS))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def _render_text(payload: Mapping[str, Any]) -> str:
    lines = [
        f"{payload['status']}: parameter evidence validation",
        f"- total_parameters: {payload['total_parameters']}",
        f"- missing_evidence_count: {payload['missing_evidence_count']}",
        f"- evidence_completeness_ratio: {payload['evidence_completeness_ratio']:.6f}",
        f"- realistic_D_violations: {payload['realistic_D_violations']}",
        "- trust_distribution: "
        + ", ".join(f"{grade}={payload['trust_distribution'].get(grade, 0)}" for grade in ["A", "B", "C", "D"]),
    ]
    errors = payload.get("errors", [])
    if errors:
        lines.append("- errors:")
        for error in errors:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    try:
        result = validate(
            parameter_registry=load_json(repo_root / args.parameter_registry),
            evidence_sources_payload=load_json(repo_root / args.evidence_sources),
            parameter_claims_payload=load_json(repo_root / args.parameter_claims),
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
