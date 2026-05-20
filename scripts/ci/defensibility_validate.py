#!/usr/bin/env python3
"""Validate scientific defensibility contract for drilldown artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text

EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

ALLOWED_ORIGIN_TYPES = {"measured", "assumed", "derived", "computed"}
ALLOWED_UNCERTAINTY_TYPES = {"distribution", "interval", "fixed", "model-derived"}
ALLOWED_TRUST = {"A", "B", "C", "D"}
ALLOWED_METHODS = {"OAT", "delta_log_odds", "correlation"}

DEFAULT_MANIFEST = Path("artifacts/parameter_drilldown_manifest.json")
DEFAULT_EVIDENCE_INDEX = Path("artifacts/parameter_evidence_index.json")
DEFAULT_P_SUCCESS = Path("artifacts/p_success_defensibility.json")
DEFAULT_SENSITIVITY = Path("ops/reports/parameter-audit-latest/SENSITIVITY_RESULTS.json")


def validate_contract(
    *,
    manifest: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
    p_success: Mapping[str, Any],
    sensitivity: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    errors: List[str] = []

    manifest_params = manifest.get("parameters")
    if not isinstance(manifest_params, list) or not manifest_params:
        errors.append("manifest.parameters must be a non-empty list")
        manifest_params = []

    manifest_by_id: Dict[str, Dict[str, Any]] = {}
    for idx, item in enumerate(manifest_params):
        if not isinstance(item, Mapping):
            errors.append(f"manifest.parameters[{idx}] must be object")
            continue
        parameter_id = item.get("parameter_id")
        if not isinstance(parameter_id, str) or not parameter_id:
            errors.append(f"manifest.parameters[{idx}] missing parameter_id")
            continue
        manifest_by_id[parameter_id] = dict(item)

    for parameter_id, manifest_entry in sorted(manifest_by_id.items()):
        evidence_entry = evidence_index.get(parameter_id)
        if not isinstance(evidence_entry, Mapping):
            errors.append(f"{parameter_id}: missing evidence entry")
            continue

        value_origin_type = evidence_entry.get("value_origin_type")
        if value_origin_type not in ALLOWED_ORIGIN_TYPES:
            errors.append(f"{parameter_id}: invalid value_origin_type={value_origin_type!r}")

        trust_grade = evidence_entry.get("trust_grade")
        if trust_grade not in ALLOWED_TRUST:
            errors.append(f"{parameter_id}: invalid trust_grade={trust_grade!r}")

        source_ids = evidence_entry.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            errors.append(f"{parameter_id}: missing source_ids")

        uncertainty_type = evidence_entry.get("uncertainty_type")
        if uncertainty_type not in ALLOWED_UNCERTAINTY_TYPES:
            errors.append(f"{parameter_id}: invalid uncertainty_type={uncertainty_type!r}")

        affects_core = bool(manifest_entry.get("affects_core_probability", False))
        value_mode = str(manifest_entry.get("value_mode", ""))
        if affects_core and value_mode == "distribution" and uncertainty_type == "fixed":
            errors.append(f"{parameter_id}: stochastic core parameter cannot have fixed uncertainty")

        derivation_chain = evidence_entry.get("derivation_chain")
        if value_origin_type in {"derived", "computed"}:
            if not isinstance(derivation_chain, list) or not derivation_chain:
                errors.append(f"{parameter_id}: derived/computed value missing derivation_chain")

        if not bool(manifest_entry.get("has_source", False)):
            errors.append(f"{parameter_id}: manifest.has_source must be true")
        if not bool(manifest_entry.get("has_uncertainty", False)):
            errors.append(f"{parameter_id}: manifest.has_uncertainty must be true")
        if manifest_entry.get("defensibility_status") != "PASS":
            errors.append(f"{parameter_id}: manifest.defensibility_status must be PASS")

        if trust_grade == "D" and manifest_entry.get("mode") != "speculative":
            errors.append(f"{parameter_id}: trust D must be speculative mode")

        failure_surface = evidence_entry.get("failure_surface")
        if isinstance(failure_surface, list):
            for index, failure_item in enumerate(failure_surface):
                if not isinstance(failure_item, Mapping):
                    errors.append(f"{parameter_id}: failure_surface[{index}] must be object")
                    continue
                method = failure_item.get("dominant_driver_method")
                confidence = failure_item.get("confidence")
                failure_mode = failure_item.get("failure_mode")
                if not isinstance(failure_mode, str) or not failure_mode:
                    errors.append(f"{parameter_id}: failure_surface[{index}] missing failure_mode")
                if method not in ALLOWED_METHODS:
                    errors.append(f"{parameter_id}: failure_surface[{index}] invalid method={method!r}")
                if not isinstance(confidence, (int, float)) or confidence < 0.0 or confidence > 1.0:
                    errors.append(f"{parameter_id}: failure_surface[{index}] invalid confidence={confidence!r}")

    if p_success.get("formula") != "p_hit * p_survival * p_data_intact":
        errors.append("p_success_defensibility.formula mismatch")

    inputs = p_success.get("inputs")
    expected_inputs = ["p_hit", "p_survival", "p_data_intact"]
    if inputs != expected_inputs:
        errors.append(f"p_success_defensibility.inputs mismatch: {inputs!r}")

    input_origins = p_success.get("input_origins")
    if not isinstance(input_origins, Mapping):
        errors.append("p_success_defensibility.input_origins must be object")
        input_origins = {}

    for metric in expected_inputs:
        metric_entry = input_origins.get(metric)
        if not isinstance(metric_entry, Mapping):
            errors.append(f"p_success_defensibility.input_origins.{metric} missing")
            continue
        source_ids = metric_entry.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            errors.append(f"p_success_defensibility.input_origins.{metric} missing source_ids")

    propagation = p_success.get("uncertainty_propagation")
    if propagation not in {"MonteCarlo", "analytical", "hybrid"}:
        errors.append(f"p_success_defensibility.uncertainty_propagation invalid: {propagation!r}")

    mode_constraints = p_success.get("mode_constraints")
    if not isinstance(mode_constraints, Mapping):
        errors.append("p_success_defensibility.mode_constraints must be object")

    if sensitivity is not None:
        top_5 = sensitivity.get("top_5")
        if not isinstance(top_5, list) or not top_5:
            errors.append("sensitivity report missing top_5 list")
        else:
            for index, item in enumerate(top_5):
                if not isinstance(item, Mapping):
                    errors.append(f"sensitivity.top_5[{index}] must be object")
                    continue
                parameter_id = item.get("parameter_id")
                if not isinstance(parameter_id, str) or parameter_id not in manifest_by_id:
                    errors.append(f"sensitivity.top_5[{index}] unknown parameter_id={parameter_id!r}")
                    continue
                evidence_entry = evidence_index.get(parameter_id)
                if not isinstance(evidence_entry, Mapping):
                    errors.append(f"sensitivity.top_5[{index}] missing evidence entry for {parameter_id}")
                    continue
                if not evidence_entry.get("influence_path"):
                    errors.append(f"sensitivity.top_5[{index}] parameter {parameter_id} missing influence_path")

    return {
        "status": "PASS" if not errors else "FAIL",
        "parameter_count": len(manifest_by_id),
        "error_count": len(errors),
        "errors": errors,
    }


def _render_text(result: Mapping[str, Any]) -> str:
    lines = [
        f"{result['status']}: defensibility validation",
        f"- parameter_count: {result['parameter_count']}",
        f"- error_count: {result['error_count']}",
    ]
    if result["errors"]:
        lines.append("- errors:")
        for item in result["errors"]:
            lines.append(f"  - {item}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--evidence-index", default=str(DEFAULT_EVIDENCE_INDEX))
    parser.add_argument("--p-success-defensibility", default=str(DEFAULT_P_SUCCESS))
    parser.add_argument("--sensitivity", default=str(DEFAULT_SENSITIVITY))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = load_json(Path(args.manifest).resolve())
        evidence_index = load_json(Path(args.evidence_index).resolve())
        p_success = load_json(Path(args.p_success_defensibility).resolve())

        sensitivity_path = Path(args.sensitivity).resolve()
        sensitivity = load_json(sensitivity_path) if sensitivity_path.exists() else None

        result = validate_contract(
            manifest=manifest,
            evidence_index=evidence_index,
            p_success=p_success,
            sensitivity=sensitivity,
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
