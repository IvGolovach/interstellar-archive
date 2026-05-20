#!/usr/bin/env python3
"""Validate failure-surface baseline artifact contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Set

try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text

EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_ARTIFACT = Path("artifacts/failure_surface_baseline.v1.json")
DEFAULT_TAXONOMY = Path("mission/dag/registry/failure_taxonomy.v1.json")
DEFAULT_MANIFEST = Path("artifacts/parameter_drilldown_manifest.json")

STAGE_ORDER = ("S0", "S1", "S2", "S3")
ALLOWED_OUTCOME = {"SUCCESS", "FAIL", "UNHEALTHY", "INVALID"}
ALLOWED_STAGE_WITH_NONE = set(STAGE_ORDER) | {"NONE"}
ALLOWED_TIMELINE_STATUS = {"PASS", "FAIL", "N/A"}
ALLOWED_DRIVER_METHODS = {"OAT", "delta_p_success", "taxonomy_attribution"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _taxonomy_ids(payload: Mapping[str, Any]) -> Set[str]:
    out: Set[str] = set()
    for item in payload.get("failure_modes", []):
        if isinstance(item, Mapping):
            failure_id = item.get("id")
            if isinstance(failure_id, str) and failure_id:
                out.add(failure_id)
    return out


def _manifest_ids(payload: Mapping[str, Any]) -> Set[str]:
    out: Set[str] = set()
    for item in payload.get("parameters", []):
        if isinstance(item, Mapping):
            parameter_id = item.get("parameter_id")
            if isinstance(parameter_id, str) and parameter_id:
                out.add(parameter_id)
    return out


def validate_contract(
    *,
    artifact: Mapping[str, Any],
    taxonomy_ids: Set[str],
    manifest_parameter_ids: Set[str],
) -> Dict[str, Any]:
    errors: List[str] = []

    if artifact.get("schema_version") != "failure_surface.v1":
        errors.append("schema_version must be failure_surface.v1")

    engine = artifact.get("engine")
    if not isinstance(engine, Mapping):
        errors.append("engine must be object")
        engine = {}
    commit_sha = engine.get("commit_sha")
    if not isinstance(commit_sha, str) or not commit_sha.strip():
        errors.append("engine.commit_sha must be non-empty string")
    signature = engine.get("determinism_signature")
    if not isinstance(signature, str) or not SHA256_RE.match(signature):
        errors.append("engine.determinism_signature must be 64-hex sha256")
    mode = engine.get("mode")
    if mode not in {"realistic", "speculative", "dual"}:
        errors.append("engine.mode must be realistic|speculative|dual")
    seed = engine.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        errors.append("engine.seed must be integer")
    scenario_ref = engine.get("scenario_ref")
    if not isinstance(scenario_ref, str) or not scenario_ref.strip():
        errors.append("engine.scenario_ref must be non-empty string")
    elif "ops/" in scenario_ref.replace("\\", "/"):
        errors.append("engine.scenario_ref must not reference ops/**")

    outcome = artifact.get("outcome")
    if not isinstance(outcome, Mapping):
        errors.append("outcome must be object")
        outcome = {}
    outcome_class = outcome.get("outcome_class")
    if outcome_class not in ALLOWED_OUTCOME:
        errors.append("outcome.outcome_class must be SUCCESS|FAIL|UNHEALTHY|INVALID")
    p_success = outcome.get("p_success")
    if isinstance(p_success, bool) or not isinstance(p_success, (int, float)):
        errors.append("outcome.p_success must be numeric")
    elif not (0.0 <= float(p_success) <= 1.0):
        errors.append("outcome.p_success must be in [0,1]")
    failure_mode = outcome.get("failure_mode")
    if not isinstance(failure_mode, str) or not failure_mode:
        errors.append("outcome.failure_mode must be non-empty string")
    elif failure_mode != "NONE" and failure_mode not in taxonomy_ids:
        errors.append(f"outcome.failure_mode unknown taxonomy id: {failure_mode}")
    failure_stage = outcome.get("failure_stage")
    if failure_stage not in ALLOWED_STAGE_WITH_NONE:
        errors.append("outcome.failure_stage must be S0|S1|S2|S3|NONE")
    if failure_mode == "NONE" and failure_stage != "NONE":
        errors.append("outcome.failure_stage must be NONE when failure_mode=NONE")
    if outcome_class == "SUCCESS" and (failure_mode != "NONE" or failure_stage != "NONE"):
        errors.append("SUCCESS outcome must use failure_mode=NONE and failure_stage=NONE")

    timeline = artifact.get("timeline")
    if not isinstance(timeline, list):
        errors.append("timeline must be list")
        timeline = []
    seen_stages: List[str] = []
    for index, entry in enumerate(timeline):
        if not isinstance(entry, Mapping):
            errors.append(f"timeline[{index}] must be object")
            continue
        stage = entry.get("stage")
        status = entry.get("status")
        summary = entry.get("summary")
        if stage not in STAGE_ORDER:
            errors.append(f"timeline[{index}].stage must be S0|S1|S2|S3")
        else:
            seen_stages.append(stage)
        if status not in ALLOWED_TIMELINE_STATUS:
            errors.append(f"timeline[{index}].status must be PASS|FAIL|N/A")
        if not isinstance(summary, str) or not summary.strip():
            errors.append(f"timeline[{index}].summary must be non-empty string")
    if seen_stages != list(STAGE_ORDER):
        errors.append("timeline must contain exactly S0,S1,S2,S3 in order")

    drivers = artifact.get("dominant_drivers")
    if not isinstance(drivers, Mapping):
        errors.append("dominant_drivers must be object")
        drivers = {}
    method = drivers.get("method")
    if method not in ALLOWED_DRIVER_METHODS:
        errors.append("dominant_drivers.method must be OAT|delta_p_success|taxonomy_attribution")
    confidence = drivers.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        errors.append("dominant_drivers.confidence must be numeric")
    elif not (0.0 <= float(confidence) <= 1.0):
        errors.append("dominant_drivers.confidence must be in [0,1]")
    top3 = drivers.get("top3")
    if not isinstance(top3, list):
        errors.append("dominant_drivers.top3 must be list")
        top3 = []
    if len(top3) != 3:
        errors.append("dominant_drivers.top3 must contain exactly 3 entries")
    seen_driver_ids: Set[str] = set()
    for index, item in enumerate(top3):
        if not isinstance(item, Mapping):
            errors.append(f"dominant_drivers.top3[{index}] must be object")
            continue
        parameter_id = item.get("parameter_id")
        reason = item.get("reason")
        evidence_ref = item.get("evidence_ref")
        if not isinstance(parameter_id, str) or not parameter_id:
            errors.append(f"dominant_drivers.top3[{index}].parameter_id must be non-empty string")
            continue
        if parameter_id in seen_driver_ids:
            errors.append(f"dominant_drivers.top3 has duplicated parameter_id: {parameter_id}")
        seen_driver_ids.add(parameter_id)
        if parameter_id not in manifest_parameter_ids:
            errors.append(f"dominant_drivers.top3[{index}] unknown parameter_id: {parameter_id}")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"dominant_drivers.top3[{index}].reason must be non-empty string")
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            errors.append(f"dominant_drivers.top3[{index}].evidence_ref must be non-empty string")
        else:
            expected_ref = f"artifacts/parameter_evidence_index.json#{parameter_id}"
            if evidence_ref != expected_ref:
                errors.append(
                    f"dominant_drivers.top3[{index}].evidence_ref must equal {expected_ref!r}, got {evidence_ref!r}"
                )

    encoded = json.dumps(artifact, sort_keys=True)
    if "ops/" in encoded or "ops\\\\" in encoded:
        errors.append("artifact must not reference ops/** paths")

    return {
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
    }


def _render_text(result: Mapping[str, Any]) -> str:
    lines = [
        f"{result['status']}: failure surface validation",
        f"- error_count: {result['error_count']}",
    ]
    if result["errors"]:
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--failure-taxonomy", default=str(DEFAULT_TAXONOMY))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        artifact = load_json(Path(args.artifact).resolve())
        taxonomy = load_json(Path(args.failure_taxonomy).resolve())
        manifest = load_json(Path(args.manifest).resolve())
        result = validate_contract(
            artifact=artifact,
            taxonomy_ids=_taxonomy_ids(taxonomy),
            manifest_parameter_ids=_manifest_ids(manifest),
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
