"""Deterministic loader and validator for capsule design v1 data."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


SCHEMA_VERSION = "capsule_design.v1"
DEFAULT_CAPSULE_DESIGN_PATH = Path(__file__).with_name("capsule_design.v1.json")
REQUIRED_STACK_LAYER_IDS = (
    "c_c_sic_tps",
    "al_li_bumper",
    "stand_off_gap",
    "b4c_ta_rear_wall",
    "ti_vault",
    "data_media_package",
    "redundancy_margin",
)
REQUIRED_SURVIVABILITY_INPUTS = (
    "frontal_area_m2",
    "shield_areal_density_kg_m2",
    "data_media_survival_margin",
    "material_degradation_mu_1_per_year",
)
ALLOWED_SURVIVABILITY_PROVENANCE = {"validated_source", "proxy", "assumption"}


def _is_finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def _bounds_pair(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        return None
    low, high = value
    if not _is_finite_number(low) or not _is_finite_number(high):
        return None
    low_f = float(low)
    high_f = float(high)
    if low_f > high_f:
        return None
    return low_f, high_f


def _validate_bounded_number(
    *,
    prefix: str,
    name: str,
    value: Any,
    bounds: Mapping[str, Any],
    errors: List[str],
) -> None:
    if not _is_finite_number(value):
        errors.append(f"{prefix}.{name} must be a finite number")
        return

    pair = _bounds_pair(bounds.get(name))
    if pair is None:
        errors.append(f"{prefix}.bounds.{name} must be [min, max] numbers")
        return

    low, high = pair
    numeric_value = float(value)
    if numeric_value < low or numeric_value > high:
        errors.append(f"{prefix}.{name} must be within declared bounds [{low}, {high}]")


def load_capsule_design(path: Path) -> Dict[str, Any]:
    """Load capsule design JSON from a local file path."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level JSON object")
    return payload


def load_default_capsule_design() -> Dict[str, Any]:
    """Load the checked-in capsule design v1 data file."""

    return load_capsule_design(DEFAULT_CAPSULE_DESIGN_PATH)


def summarize_mass_budget(design: Mapping[str, Any]) -> Dict[str, Any]:
    layers = design.get("layers", [])
    layer_ids: List[str] = []
    masses: List[float] = []
    if isinstance(layers, list):
        for layer in layers:
            if not isinstance(layer, Mapping):
                continue
            layer_id = layer.get("layer_id")
            if isinstance(layer_id, str):
                layer_ids.append(layer_id)
            mass = layer.get("mass_kg")
            if _is_finite_number(mass):
                masses.append(float(mass))

    mass_budget = design.get("mass_budget", {})
    configured_mass = 0.0
    declared_margin = 0.0
    if isinstance(mass_budget, Mapping):
        raw_configured_mass = mass_budget.get("configured_capsule_mass_kg")
        raw_margin = mass_budget.get("declared_margin_kg")
        if _is_finite_number(raw_configured_mass):
            configured_mass = float(raw_configured_mass)
        if _is_finite_number(raw_margin):
            declared_margin = float(raw_margin)

    component_mass = math.fsum(masses)
    closure_delta = component_mass - configured_mass
    return {
        "configured_capsule_mass_kg": round(configured_mass, 12),
        "component_mass_kg": round(component_mass, 12),
        "closure_delta_kg": round(closure_delta, 12),
        "declared_margin_kg": round(declared_margin, 12),
        "layer_ids": layer_ids,
    }


def _validate_materials(materials: Any) -> tuple[List[str], set[str]]:
    errors: List[str] = []
    material_ids: set[str] = set()
    if not isinstance(materials, list) or not materials:
        return ["materials must be a non-empty list"], material_ids

    for index, material in enumerate(materials):
        prefix = f"materials[{index}]"
        if not isinstance(material, Mapping):
            errors.append(f"{prefix} must be object")
            continue

        material_id = material.get("material_id")
        if not isinstance(material_id, str) or not material_id.strip():
            errors.append(f"{prefix}.material_id must be non-empty string")
        elif material_id in material_ids:
            errors.append(f"{prefix}.material_id duplicated: {material_id}")
        else:
            material_ids.add(material_id)

        name = material.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix}.name must be non-empty string")

        bounds = material.get("bounds", {})
        density = material.get("density_kg_m3")
        if density is not None:
            if not isinstance(bounds, Mapping):
                errors.append(f"{prefix}.bounds must be object when density_kg_m3 is set")
            else:
                _validate_bounded_number(
                    prefix=prefix,
                    name="density_kg_m3",
                    value=density,
                    bounds=bounds,
                    errors=errors,
                )

    return errors, material_ids


def _validate_layers(layers: Any, material_ids: set[str]) -> List[str]:
    errors: List[str] = []
    if not isinstance(layers, list) or not layers:
        return ["layers must be a non-empty list"]

    layer_ids: List[str] = []
    seen_ids: set[str] = set()
    for index, layer in enumerate(layers):
        prefix = f"layers[{index}]"
        if not isinstance(layer, Mapping):
            errors.append(f"{prefix} must be object")
            continue

        layer_id = layer.get("layer_id")
        if not isinstance(layer_id, str) or not layer_id.strip():
            errors.append(f"{prefix}.layer_id must be non-empty string")
            layer_id = f"<invalid-{index}>"
        elif layer_id in seen_ids:
            errors.append(f"{prefix}.layer_id duplicated: {layer_id}")
        else:
            seen_ids.add(layer_id)
            layer_ids.append(layer_id)

        radial_order = layer.get("radial_order")
        if not isinstance(radial_order, int) or isinstance(radial_order, bool):
            errors.append(f"{prefix}.radial_order must be integer")
        elif radial_order != index + 1:
            errors.append(f"{prefix}.radial_order must equal stack position {index + 1}")

        material_id = layer.get("material_id")
        if not isinstance(material_id, str) or material_id not in material_ids:
            errors.append(f"{prefix}.material_id must reference a declared material")

        bounds = layer.get("bounds")
        if not isinstance(bounds, Mapping):
            errors.append(f"{prefix}.bounds must be object")
            continue

        _validate_bounded_number(
            prefix=prefix,
            name="mass_kg",
            value=layer.get("mass_kg"),
            bounds=bounds,
            errors=errors,
        )

        if layer_id == "stand_off_gap":
            _validate_bounded_number(
                prefix=prefix,
                name="stand_off_gap_m",
                value=layer.get("stand_off_gap_m"),
                bounds=bounds,
                errors=errors,
            )
            if layer.get("mass_kg") != 0.0:
                errors.append(f"{prefix}.mass_kg must be 0.0 for stand_off_gap")
        elif "thickness_m" in layer:
            _validate_bounded_number(
                prefix=prefix,
                name="thickness_m",
                value=layer.get("thickness_m"),
                bounds=bounds,
                errors=errors,
            )

    if layer_ids != list(REQUIRED_STACK_LAYER_IDS):
        errors.append(
            "layers required stack order must be "
            + ", ".join(REQUIRED_STACK_LAYER_IDS)
        )

    return errors


def _validate_mass_budget(design: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    mass_budget = design.get("mass_budget")
    if not isinstance(mass_budget, Mapping):
        return ["mass_budget must be object"]

    configured_mass = mass_budget.get("configured_capsule_mass_kg")
    if not _is_finite_number(configured_mass) or float(configured_mass) <= 0:
        errors.append("mass_budget.configured_capsule_mass_kg must be positive finite number")

    declared_margin = mass_budget.get("declared_margin_kg")
    if not _is_finite_number(declared_margin) or float(declared_margin) < 0:
        errors.append("mass_budget.declared_margin_kg must be non-negative finite number")

    declared_component_mass = mass_budget.get("component_mass_kg")
    if not _is_finite_number(declared_component_mass):
        errors.append("mass_budget.component_mass_kg must be finite number")

    if errors:
        return errors

    summary = summarize_mass_budget(design)
    if abs(float(summary["component_mass_kg"]) - float(declared_component_mass)) > 1e-9:
        errors.append(
            "mass_budget.component_mass_kg must match computed layer sum: "
            f"declared={declared_component_mass} kg, computed={summary['component_mass_kg']} kg"
        )
    if abs(float(summary["closure_delta_kg"])) > float(summary["declared_margin_kg"]):
        errors.append(
            "mass closure exceeds declared margin: "
            f"components={summary['component_mass_kg']} kg, "
            f"configured={summary['configured_capsule_mass_kg']} kg, "
            f"delta={summary['closure_delta_kg']} kg, "
            f"margin={summary['declared_margin_kg']} kg"
        )

    return errors


def _validate_survivability_model_inputs(design: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    inputs = design.get("survivability_model_inputs")
    if not isinstance(inputs, Mapping):
        return ["survivability_model_inputs must be object"]

    bounds = design.get("survivability_uncertainty_bounds", {})
    if not isinstance(bounds, Mapping):
        errors.append("survivability_uncertainty_bounds must be object")
        bounds = {}

    for field in REQUIRED_SURVIVABILITY_INPUTS:
        prefix = f"survivability_model_inputs.{field}"
        entry = inputs.get(field)
        if not isinstance(entry, Mapping):
            errors.append(f"{prefix} must be object")
            continue
        value = entry.get("value")
        if not _is_finite_number(value):
            errors.append(f"{prefix}.value must be finite number")
            continue
        numeric_value = float(value)
        if field == "data_media_survival_margin":
            if not 0.0 <= numeric_value <= 1.0:
                errors.append(f"{prefix}.value must be in [0, 1]")
        elif numeric_value <= 0.0:
            errors.append(f"{prefix}.value must be > 0")

        provenance = entry.get("provenance")
        if provenance not in ALLOWED_SURVIVABILITY_PROVENANCE:
            errors.append(f"{prefix}.provenance must be one of {sorted(ALLOWED_SURVIVABILITY_PROVENANCE)}")
        source_ids = entry.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids or not all(isinstance(item, str) and item for item in source_ids):
            errors.append(f"{prefix}.source_ids must be a non-empty string array")

        if field in bounds:
            pair = _bounds_pair(bounds.get(field))
            if pair is None:
                errors.append(f"survivability_uncertainty_bounds.{field} must be [min, max] numbers")
            elif not pair[0] <= numeric_value <= pair[1]:
                errors.append(f"{prefix}.value must be within survivability uncertainty bounds")

    return errors


def validate_capsule_design(design: Mapping[str, Any]) -> List[str]:
    """Return contract errors for a capsule design payload."""

    errors: List[str] = []
    if not isinstance(design, Mapping):
        return ["capsule design must be object"]

    if design.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    material_errors, material_ids = _validate_materials(design.get("materials"))
    errors.extend(material_errors)
    errors.extend(_validate_layers(design.get("layers"), material_ids))
    errors.extend(_validate_mass_budget(design))
    errors.extend(_validate_survivability_model_inputs(design))

    return errors
