#!/usr/bin/env python3
"""Validate parameter registry structure and uncertainty contract."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3


ALLOWED_TYPES = {"scalar", "distribution"}
ALLOWED_CATEGORIES = {"safe", "advanced", "non_physical"}
ALLOWED_MODES = {"realistic", "speculative", "both"}
ALLOWED_DOMAINS = {"realistic", "speculative"}
ALLOWED_CLASSIFICATIONS = {"derived", "measured", "estimated", "assumed", "design_choice"}
ALLOWED_VISIBILITIES = {"public", "internal"}
ALLOWED_PUBLIC_SURFACES = {"browser", "optimization"}
ALLOWED_AUDIT_SCOPES = {"mission_parameter", "code_literal"}
ALLOWED_DISTRIBUTIONS = {"normal", "lognormal", "uniform", "triangular"}
ALLOWED_USED_IN = {"p_hit", "p_survival", "p_data_intact", "p_success", "benchmark_guard", "mission_validation"}
LEGACY_CODE_LITERAL_ID_RE = re.compile(r"^code_literal\.[A-Za-z0-9_]+_py_\d+_\d+$")


DEFAULT_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_UNCERTAINTY = Path("mission/UNCERTAINTY_MODEL_v1.json")


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_bounds(bounds: Any, prefix: str, errors: List[str], allow_equal: bool = True) -> Tuple[float, float] | None:
    if not isinstance(bounds, list) or len(bounds) != 2:
        errors.append(f"{prefix}.bounds must be [min,max]")
        return None
    low, high = bounds
    if not _numeric(low) or not _numeric(high):
        errors.append(f"{prefix}.bounds values must be numeric")
        return None
    low_f = float(low)
    high_f = float(high)
    if allow_equal:
        if low_f > high_f:
            errors.append(f"{prefix}.bounds requires min <= max")
            return None
    else:
        if low_f >= high_f:
            errors.append(f"{prefix}.bounds requires min < max")
            return None
    return (low_f, high_f)


def _uncertainty_map(uncertainty_payload: Mapping[str, Any], errors: List[str]) -> Dict[str, Dict[str, Any]]:
    entries = uncertainty_payload.get("entries")
    if not isinstance(entries, list):
        errors.append("mission/UNCERTAINTY_MODEL_v1.json must contain entries list")
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        prefix = f"uncertainty.entries[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be object")
            continue
        pid = entry.get("parameter_id")
        if not isinstance(pid, str) or not pid.strip():
            errors.append(f"{prefix}.parameter_id must be non-empty string")
            continue
        distribution = entry.get("distribution")
        if distribution not in ALLOWED_DISTRIBUTIONS:
            errors.append(f"{prefix}.distribution '{distribution}' is invalid")
        bounds = entry.get("bounds")
        if not isinstance(bounds, dict):
            errors.append(f"{prefix}.bounds must be object")
        else:
            low = bounds.get("min")
            high = bounds.get("max")
            if not _numeric(low) or not _numeric(high) or float(low) >= float(high):
                errors.append(f"{prefix}.bounds requires numeric min < max")
        out[pid] = entry
    return out


def validate(
    registry_payload: Mapping[str, Any],
    uncertainty_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if registry_payload.get("schema_version") != "parameter_registry.v1":
        errors.append("schema_version must be parameter_registry.v1")

    parameters = registry_payload.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        errors.append("parameters must be non-empty list")
        return {
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
            "parameter_count": 0,
            "distribution_parameter_count": 0,
        }

    uncertainty_by_pid = _uncertainty_map(uncertainty_payload, errors)
    seen_ids: Dict[str, int] = {}
    distribution_count = 0

    for index, entry in enumerate(parameters):
        prefix = f"parameters[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be object")
            continue

        parameter_id = entry.get("parameter_id")
        if not isinstance(parameter_id, str) or not parameter_id.strip():
            errors.append(f"{prefix}.parameter_id must be non-empty string")
            continue
        parameter_id = parameter_id.strip()
        if parameter_id.startswith("code_literal.") and LEGACY_CODE_LITERAL_ID_RE.fullmatch(parameter_id):
            errors.append(f"{prefix}.parameter_id uses legacy line-based code literal naming")
        seen_ids[parameter_id] = seen_ids.get(parameter_id, 0) + 1

        for field in ("name", "unit", "notes"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{field} must be non-empty string")

        entry_type = entry.get("type")
        if entry_type not in ALLOWED_TYPES:
            errors.append(f"{prefix}.type '{entry_type}' is invalid")

        default = entry.get("default")
        if not _numeric(default):
            errors.append(f"{prefix}.default must be numeric")

        _validate_bounds(entry.get("bounds"), prefix, errors, allow_equal=True)

        category = entry.get("category")
        if category not in ALLOWED_CATEGORIES:
            errors.append(f"{prefix}.category '{category}' is invalid")

        mode = entry.get("mode")
        if mode not in ALLOWED_MODES:
            errors.append(f"{prefix}.mode '{mode}' is invalid")

        domain = entry.get("domain")
        if domain not in ALLOWED_DOMAINS:
            errors.append(f"{prefix}.domain '{domain}' is invalid")

        affects_core_probability = entry.get("affects_core_probability")
        if not isinstance(affects_core_probability, bool):
            errors.append(f"{prefix}.affects_core_probability must be boolean")

        classification = entry.get("classification")
        if classification not in ALLOWED_CLASSIFICATIONS:
            errors.append(f"{prefix}.classification '{classification}' is invalid")

        visibility = entry.get("visibility")
        if visibility not in ALLOWED_VISIBILITIES:
            errors.append(f"{prefix}.visibility '{visibility}' is invalid")

        public_surfaces_raw = entry.get("public_surfaces")
        public_surfaces: List[str] = []
        if not isinstance(public_surfaces_raw, list):
            errors.append(f"{prefix}.public_surfaces must be an array")
        else:
            for surface in public_surfaces_raw:
                if surface not in ALLOWED_PUBLIC_SURFACES:
                    errors.append(f"{prefix}.public_surfaces includes unsupported surface '{surface}'")
                elif surface in public_surfaces:
                    errors.append(f"{prefix}.public_surfaces contains duplicate surface '{surface}'")
                else:
                    public_surfaces.append(surface)

        audit_scope = entry.get("audit_scope")
        if audit_scope not in ALLOWED_AUDIT_SCOPES:
            errors.append(f"{prefix}.audit_scope '{audit_scope}' is invalid")

        is_code_literal = parameter_id.startswith("code_literal.")
        if is_code_literal:
            if visibility != "internal":
                errors.append(f"{prefix}: code_literal parameter requires visibility=internal")
            if public_surfaces:
                errors.append(f"{prefix}: code_literal parameter must not declare public_surfaces")
            if audit_scope != "code_literal":
                errors.append(f"{prefix}: code_literal parameter requires audit_scope=code_literal")
        elif visibility == "internal":
            if public_surfaces:
                errors.append(f"{prefix}: internal visibility must not declare public_surfaces")
            if audit_scope != "code_literal":
                errors.append(f"{prefix}: internal visibility requires audit_scope=code_literal")
        elif visibility == "public":
            if not public_surfaces:
                errors.append(f"{prefix}: public visibility requires at least one public surface")
            if audit_scope != "mission_parameter":
                errors.append(f"{prefix}: public visibility requires audit_scope=mission_parameter")

        used_in = entry.get("used_in")
        if not isinstance(used_in, list) or not used_in:
            errors.append(f"{prefix}.used_in must be non-empty list")
        else:
            for target in used_in:
                if target not in ALLOWED_USED_IN:
                    errors.append(f"{prefix}.used_in includes unsupported target '{target}'")
            has_core_use = any(target in {"p_hit", "p_survival", "p_data_intact", "p_success"} for target in used_in)
            if isinstance(affects_core_probability, bool) and affects_core_probability != has_core_use:
                errors.append(f"{prefix}.affects_core_probability must match used_in core targets")

        code_refs = entry.get("code_refs")
        json_refs = entry.get("json_refs")
        if not isinstance(code_refs, list) or not isinstance(json_refs, list):
            errors.append(f"{prefix}.code_refs/json_refs must be arrays")
            code_refs = []
            json_refs = []

        if not code_refs and not json_refs:
            errors.append(f"{prefix} must have at least one code_ref or json_ref")

        for ref in code_refs:
            if not isinstance(ref, str) or not ref.strip():
                errors.append(f"{prefix}.code_refs contains invalid ref")
        for ref in json_refs:
            if not isinstance(ref, str) or not ref.strip():
                errors.append(f"{prefix}.json_refs contains invalid ref")

        dependencies = entry.get("dependencies", [])
        if dependencies is None:
            dependencies = []
        if not isinstance(dependencies, list):
            errors.append(f"{prefix}.dependencies must be an array when provided")
        else:
            for dep in dependencies:
                if not isinstance(dep, str) or not dep.strip():
                    errors.append(f"{prefix}.dependencies contains invalid parameter_id")

        if category == "non_physical" and domain != "speculative":
            errors.append(f"{prefix}: non_physical category requires domain=speculative")
        if "non_physical_" in parameter_id and domain != "speculative":
            errors.append(f"{prefix}: non_physical parameter_id requires domain=speculative")

        if entry_type == "distribution":
            distribution_count += 1
            distribution = entry.get("distribution")
            if not isinstance(distribution, dict):
                errors.append(f"{prefix}.distribution must be object for distribution type")
                continue

            dist_type = distribution.get("type")
            if dist_type not in ALLOWED_DISTRIBUTIONS:
                errors.append(f"{prefix}.distribution.type '{dist_type}' is invalid")
            params = distribution.get("parameters")
            if not isinstance(params, dict) or not params:
                errors.append(f"{prefix}.distribution.parameters must be non-empty object")
            else:
                for key, value in params.items():
                    if not isinstance(key, str) or not key.strip() or not _numeric(value):
                        errors.append(f"{prefix}.distribution.parameters has invalid entry")

            dist_bounds = distribution.get("bounds")
            _validate_bounds(dist_bounds, f"{prefix}.distribution", errors, allow_equal=False)

            evidence_refs = distribution.get("evidence_source_ids")
            if not isinstance(evidence_refs, list) or not evidence_refs:
                errors.append(f"{prefix}.distribution.evidence_source_ids must be non-empty list")
            else:
                for src in evidence_refs:
                    if not isinstance(src, str) or not src.strip():
                        errors.append(f"{prefix}.distribution.evidence_source_ids contains invalid source id")

            uncertainty_entry = uncertainty_by_pid.get(parameter_id)
            if uncertainty_entry is None:
                warnings.append(f"{prefix}: no matching mission uncertainty entry for distribution parameter")

    duplicates = sorted(pid for pid, count in seen_ids.items() if count > 1)
    for pid in duplicates:
        errors.append(f"duplicate parameter_id: {pid}")

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "parameter_count": len(parameters),
        "distribution_parameter_count": distribution_count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def _render_text(payload: Mapping[str, Any]) -> str:
    lines = [
        f"{payload['status']}: parameter registry validation",
        f"- parameter_count: {payload['parameter_count']}",
        f"- distribution_parameter_count: {payload['distribution_parameter_count']}",
    ]
    warnings = payload.get("warnings", [])
    errors = payload.get("errors", [])
    if warnings:
        lines.append("- warnings:")
        for warning in warnings:
            lines.append(f"  - {warning}")
    if errors:
        lines.append("- errors:")
        for error in errors:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    try:
        registry_payload = load_json(repo_root / args.registry)
        uncertainty_payload = load_json(repo_root / args.uncertainty)
        result = validate(registry_payload, uncertainty_payload)

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
