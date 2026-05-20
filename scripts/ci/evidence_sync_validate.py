#!/usr/bin/env python3
"""Validate synchronization between canonical parameter evidence and mission cross-check evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Tuple

try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_PARAMETER_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_PARAMETER_CLAIMS = Path("parameters/registry/parameter_claims.v1.json")
DEFAULT_EVIDENCE_SOURCES = Path("parameters/registry/evidence_sources.v1.json")
DEFAULT_MISSION_REGISTRY = Path("mission/EVIDENCE_REGISTRY_v1.json")


def _canonical(obj: Mapping[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _map_parameter_claims(payload: Mapping[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    errors: List[str] = []
    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, list):
        return {}, ["parameter claims payload must contain list field 'claims'"]

    out: Dict[str, Dict[str, Any]] = {}
    for idx, claim in enumerate(raw_claims):
        prefix = f"parameter_claims.claims[{idx}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} must be object")
            continue
        pid = claim.get("parameter_id")
        if not isinstance(pid, str) or not pid.strip():
            errors.append(f"{prefix}.parameter_id must be non-empty string")
            continue
        if pid in out:
            errors.append(f"{prefix}.parameter_id duplicated: {pid}")
            continue
        out[pid] = dict(claim)
    return out, errors


def _map_parameter_sources(payload: Mapping[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    errors: List[str] = []
    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list):
        return {}, ["evidence sources payload must contain list field 'sources'"]

    out: Dict[str, Dict[str, Any]] = {}
    for idx, source in enumerate(raw_sources):
        prefix = f"evidence_sources.sources[{idx}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be object")
            continue
        sid = source.get("source_id")
        if not isinstance(sid, str) or not sid.strip():
            errors.append(f"{prefix}.source_id must be non-empty string")
            continue
        if sid in out:
            errors.append(f"{prefix}.source_id duplicated: {sid}")
            continue
        out[sid] = dict(source)
    return out, errors


def _map_mission_claims(payload: Mapping[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    errors: List[str] = []
    raw_claims = payload.get("parameter_claims")
    if not isinstance(raw_claims, list):
        return {}, ["mission registry must contain list field 'parameter_claims'"]

    out: Dict[str, Dict[str, Any]] = {}
    for idx, claim in enumerate(raw_claims):
        prefix = f"mission.parameter_claims[{idx}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} must be object")
            continue
        pid = claim.get("parameter_id")
        if not isinstance(pid, str) or not pid.strip():
            errors.append(f"{prefix}.parameter_id must be non-empty string")
            continue
        if pid in out:
            errors.append(f"{prefix}.parameter_id duplicated: {pid}")
            continue
        out[pid] = dict(claim)
    return out, errors


def _map_mission_sources(payload: Mapping[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    errors: List[str] = []
    raw_sources = payload.get("evidence_sources")
    if not isinstance(raw_sources, list):
        return {}, ["mission registry must contain list field 'evidence_sources'"]

    out: Dict[str, Dict[str, Any]] = {}
    for idx, source in enumerate(raw_sources):
        prefix = f"mission.evidence_sources[{idx}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be object")
            continue
        sid = source.get("id")
        if not isinstance(sid, str) or not sid.strip():
            errors.append(f"{prefix}.id must be non-empty string")
            continue
        if sid in out:
            errors.append(f"{prefix}.id duplicated: {sid}")
            continue
        out[sid] = dict(source)
    return out, errors


def validate_sync(
    *,
    parameter_registry: Mapping[str, Any],
    parameter_claims: Mapping[str, Any],
    evidence_sources: Mapping[str, Any],
    mission_registry: Mapping[str, Any],
) -> Dict[str, Any]:
    errors: List[str] = []
    notes: List[str] = []

    parameters = parameter_registry.get("parameters")
    if not isinstance(parameters, list):
        errors.append("parameter registry must contain list field 'parameters'")
        parameters = []
    parameter_ids = {
        item.get("parameter_id")
        for item in parameters
        if isinstance(item, dict) and isinstance(item.get("parameter_id"), str)
    }

    param_claim_by_id, claim_errors = _map_parameter_claims(parameter_claims)
    param_source_by_id, source_errors = _map_parameter_sources(evidence_sources)
    mission_claim_by_id, mission_claim_errors = _map_mission_claims(mission_registry)
    mission_source_by_id, mission_source_errors = _map_mission_sources(mission_registry)

    errors.extend(claim_errors)
    errors.extend(source_errors)
    errors.extend(mission_claim_errors)
    errors.extend(mission_source_errors)

    if parameter_registry.get("schema_version") != "parameter_registry.v1":
        errors.append("parameter_registry.schema_version must be parameter_registry.v1")
    if parameter_claims.get("schema_version") != "parameter_claims.v1":
        errors.append("parameter_claims.schema_version must be parameter_claims.v1")
    if evidence_sources.get("schema_version") != "evidence_sources.v1":
        errors.append("evidence_sources.schema_version must be evidence_sources.v1")
    if mission_registry.get("schema_version") != "evidence_registry.v1":
        errors.append("mission registry schema_version must be evidence_registry.v1")

    trust_mismatch_count = 0
    mode_mismatch_count = 0
    source_mismatch_count = 0
    mission_missing_parameter_count = 0

    for parameter_id, mission_claim in sorted(mission_claim_by_id.items()):
        if parameter_id not in parameter_ids:
            mission_missing_parameter_count += 1
            errors.append(
                f"mission claim parameter_id '{parameter_id}' is missing from parameters/registry/parameter_registry.v1.json"
            )
            continue

        canonical_claim = param_claim_by_id.get(parameter_id)
        if canonical_claim is None:
            errors.append(
                f"mission claim parameter_id '{parameter_id}' has no canonical claim in parameters/registry/parameter_claims.v1.json"
            )
            continue

        mission_trust = mission_claim.get("trust_grade")
        canonical_trust = canonical_claim.get("trust_grade")
        if mission_trust != canonical_trust:
            trust_mismatch_count += 1
            errors.append(
                f"trust mismatch for '{parameter_id}': mission={mission_trust!r} canonical={canonical_trust!r}"
            )

        mission_mode = mission_claim.get("mode")
        canonical_mode = canonical_claim.get("mode")
        if mission_mode != canonical_mode:
            mode_mismatch_count += 1
            errors.append(f"mode mismatch for '{parameter_id}': mission={mission_mode!r} canonical={canonical_mode!r}")

        mission_units = mission_claim.get("units")
        canonical_units = canonical_claim.get("units")
        if mission_units != canonical_units:
            errors.append(
                f"units mismatch for '{parameter_id}': mission={mission_units!r} canonical={canonical_units!r}"
            )

        mission_value_mode = mission_claim.get("value_mode")
        canonical_value_mode = canonical_claim.get("value_mode")
        if mission_value_mode != canonical_value_mode:
            errors.append(
                f"value_mode mismatch for '{parameter_id}': mission={mission_value_mode!r} canonical={canonical_value_mode!r}"
            )

        mission_source_ids = mission_claim.get("evidence_source_ids")
        canonical_source_ids = canonical_claim.get("evidence_source_ids")
        mission_source_ids_list = mission_source_ids if isinstance(mission_source_ids, list) else []
        canonical_source_ids_list = canonical_source_ids if isinstance(canonical_source_ids, list) else []

        for sid in mission_source_ids_list:
            if sid not in mission_source_by_id:
                errors.append(f"mission claim '{parameter_id}' references unknown mission source id '{sid}'")
            if sid not in param_source_by_id:
                errors.append(f"mission claim '{parameter_id}' references source id '{sid}' missing in canonical sources")

        for sid in canonical_source_ids_list:
            if sid not in mission_source_by_id:
                errors.append(f"canonical source id '{sid}' for '{parameter_id}' missing in mission evidence_sources")

        if sorted(str(s) for s in mission_source_ids_list) != sorted(str(s) for s in canonical_source_ids_list):
            source_mismatch_count += 1
            errors.append(
                f"evidence_source_ids mismatch for '{parameter_id}': mission={mission_source_ids_list} canonical={canonical_source_ids_list}"
            )

    for source_id, mission_source in sorted(mission_source_by_id.items()):
        canonical_source = param_source_by_id.get(source_id)
        if canonical_source is None:
            errors.append(f"mission evidence source '{source_id}' missing in canonical evidence_sources")
            continue

        comparable_mission = {
            "type": mission_source.get("type"),
            "citation": mission_source.get("citation"),
            "url": mission_source.get("url"),
            "claim_scope": mission_source.get("claim_scope"),
            "notes": mission_source.get("notes"),
        }
        comparable_canonical = {
            "type": canonical_source.get("type"),
            "citation": canonical_source.get("citation"),
            "url": canonical_source.get("url"),
            "claim_scope": canonical_source.get("claim_scope"),
            "notes": canonical_source.get("notes"),
        }
        if _canonical(comparable_mission) != _canonical(comparable_canonical):
            errors.append(
                f"source payload mismatch for '{source_id}' between mission and canonical evidence layers"
            )

    notes.append(f"canonical_parameter_count={len(parameter_ids)}")
    notes.append(f"canonical_claim_count={len(param_claim_by_id)}")
    notes.append(f"mission_claim_count={len(mission_claim_by_id)}")

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "mission_claim_count": len(mission_claim_by_id),
        "mission_source_count": len(mission_source_by_id),
        "canonical_parameter_count": len(parameter_ids),
        "canonical_claim_count": len(param_claim_by_id),
        "canonical_source_count": len(param_source_by_id),
        "mission_missing_parameter_count": mission_missing_parameter_count,
        "trust_mismatch_count": trust_mismatch_count,
        "mode_mismatch_count": mode_mismatch_count,
        "source_mismatch_count": source_mismatch_count,
        "errors": errors,
        "notes": notes,
    }


def _render_text(payload: Mapping[str, Any]) -> str:
    lines = [
        f"{payload['status']}: evidence sync validation",
        f"- mission_claim_count: {payload['mission_claim_count']}",
        f"- canonical_parameter_count: {payload['canonical_parameter_count']}",
        f"- mission_missing_parameter_count: {payload['mission_missing_parameter_count']}",
        f"- trust_mismatch_count: {payload['trust_mismatch_count']}",
        f"- mode_mismatch_count: {payload['mode_mismatch_count']}",
        f"- source_mismatch_count: {payload['source_mismatch_count']}",
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
    parser.add_argument("--evidence-sources", default=str(DEFAULT_EVIDENCE_SOURCES))
    parser.add_argument("--mission-registry", default=str(DEFAULT_MISSION_REGISTRY))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    try:
        result = validate_sync(
            parameter_registry=load_json(repo_root / args.parameter_registry),
            parameter_claims=load_json(repo_root / args.parameter_claims),
            evidence_sources=load_json(repo_root / args.evidence_sources),
            mission_registry=load_json(repo_root / args.mission_registry),
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
