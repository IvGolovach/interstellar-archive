"""Schema and scenario validation for mission baseline v1."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List

from .constants import (
    ALLOWED_DISTRIBUTIONS,
    ALLOWED_ENV_MODES,
    ALLOWED_MISSION_MODES,
    ALLOWED_PARAM_CATEGORIES,
    ALLOWED_PARAM_MODES,
    REQUIRED_OUTPUTS,
)


def _require(condition: bool, message: str, errors: List[str]) -> None:
    if not condition:
        errors.append(message)


def validate_schema_contract(schema: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    required_top = {
        "schema_version",
        "mission_mode",
        "success_threshold",
        "bh_model",
        "environment_acceptance_mode",
        "seed",
        "bh_parameters",
        "trajectory_model",
        "correction_window",
        "capsule_model",
        "environment_model",
        "uncertainty_model",
        "speculative_overrides",
        "parameter_tags",
        "outputs_required",
    }

    _require(schema.get("type") == "object", "MISSION_SCHEMA must have type=object", errors)
    _require(
        "properties" in schema and isinstance(schema["properties"], dict),
        "MISSION_SCHEMA must define properties",
        errors,
    )

    properties = schema.get("properties", {})
    _require(
        "schema_version" in properties
        and properties["schema_version"].get("const") == "mission_schema.v1",
        "MISSION_SCHEMA properties.schema_version.const must be mission_schema.v1",
        errors,
    )
    _require(
        set(schema.get("required", [])) >= required_top,
        "MISSION_SCHEMA required list is missing mandatory top-level fields",
        errors,
    )

    _require(
        properties.get("mission_mode", {}).get("enum") == ["realistic", "speculative"],
        "MISSION_SCHEMA mission_mode enum must be [realistic, speculative]",
        errors,
    )
    _require(
        properties.get("bh_model", {}).get("const") == "schwarzschild",
        "MISSION_SCHEMA bh_model must be fixed to schwarzschild in v1",
        errors,
    )
    _require(
        properties.get("environment_acceptance_mode", {}).get("enum") == ["strict", "proxy"],
        "MISSION_SCHEMA environment_acceptance_mode enum must be [strict, proxy]",
        errors,
    )
    _require(
        "allOf" in schema and len(schema.get("allOf", [])) > 0,
        "MISSION_SCHEMA must encode mode-separation rules in allOf",
        errors,
    )

    return errors


def _validate_uncertainty_model(uncertainty_model: Iterable[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    seen_names: set[str] = set()
    for index, entry in enumerate(uncertainty_model):
        prefix = f"uncertainty_model[{index}]"
        parameter_id = str(entry.get("parameter_id", "")).strip()
        name = str(entry.get("name", "")).strip()
        distribution = str(entry.get("distribution", "")).strip()
        parameters = entry.get("parameters")
        bounds = entry.get("bounds")
        units = str(entry.get("units", "")).strip()
        mode = str(entry.get("mode", "")).strip()
        category = str(entry.get("category", "")).strip()
        rationale = str(entry.get("rationale", "")).strip()

        if not parameter_id:
            errors.append(f"{prefix}.parameter_id must be non-empty")
        if not name:
            errors.append(f"{prefix}.name must be non-empty")
        elif name in seen_names:
            errors.append(f"{prefix}.name '{name}' is duplicated")
        else:
            seen_names.add(name)

        if distribution not in ALLOWED_DISTRIBUTIONS:
            errors.append(f"{prefix}.distribution '{distribution}' is invalid")
        if not isinstance(parameters, dict) or len(parameters) == 0:
            errors.append(f"{prefix}.parameters must be a non-empty object")
        else:
            for key, value in parameters.items():
                if not isinstance(key, str) or not key:
                    errors.append(f"{prefix}.parameters contains invalid key")
                if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    errors.append(f"{prefix}.parameters.{key} must be a finite number")

        if not isinstance(bounds, dict):
            errors.append(f"{prefix}.bounds must be object")
        else:
            low = bounds.get("min")
            high = bounds.get("max")
            if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
                errors.append(f"{prefix}.bounds must contain numeric min and max")
            elif float(low) >= float(high):
                errors.append(f"{prefix}.bounds requires min < max")

        if not units:
            errors.append(f"{prefix}.units must be non-empty")
        if mode not in ALLOWED_PARAM_MODES:
            errors.append(f"{prefix}.mode '{mode}' is invalid")
        if category not in ALLOWED_PARAM_CATEGORIES:
            errors.append(f"{prefix}.category '{category}' is invalid")
        if len(rationale) < 8:
            errors.append(f"{prefix}.rationale must be descriptive")

    return errors


def validate_scenario(schema: Dict[str, Any], scenario: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    required_fields = list(schema.get("required", []))
    for field in required_fields:
        if field not in scenario:
            errors.append(f"scenario missing required field '{field}'")

    unknown_fields = sorted(set(scenario.keys()) - set(required_fields))
    if unknown_fields:
        errors.append(f"scenario contains unknown top-level fields: {', '.join(unknown_fields)}")

    if scenario.get("schema_version") != "mission_schema.v1":
        errors.append("scenario.schema_version must be mission_schema.v1")

    mission_mode = scenario.get("mission_mode")
    if mission_mode not in ALLOWED_MISSION_MODES:
        errors.append("scenario.mission_mode must be realistic|speculative")

    success_threshold = scenario.get("success_threshold")
    if not isinstance(success_threshold, (int, float)) or not (0 <= float(success_threshold) <= 1):
        errors.append("scenario.success_threshold must be in [0,1]")

    if scenario.get("bh_model") != "schwarzschild":
        errors.append("scenario.bh_model must be schwarzschild")

    if scenario.get("environment_acceptance_mode") not in ALLOWED_ENV_MODES:
        errors.append("scenario.environment_acceptance_mode must be strict|proxy")

    if not isinstance(scenario.get("seed"), str) or not scenario.get("seed").strip():
        errors.append("scenario.seed must be non-empty string")

    bh = scenario.get("bh_parameters", {})
    if not isinstance(bh, dict):
        errors.append("scenario.bh_parameters must be object")
    else:
        for name in [
            "mass_kg",
            "periapsis_distance_m",
            "distance_from_earth_ly",
            "max_radiative_flux_w_m2",
            "max_plasma_density_proxy_m3",
            "max_dust_flux_scale",
        ]:
            value = bh.get(name)
            if not isinstance(value, (int, float)) or float(value) <= 0:
                errors.append(f"scenario.bh_parameters.{name} must be positive number")

    trajectory = scenario.get("trajectory_model", {})
    if not isinstance(trajectory, dict):
        errors.append("scenario.trajectory_model must be object")
    else:
        if trajectory.get("deterministic_baseline") is not True:
            errors.append("trajectory_model.deterministic_baseline must be true")
        for name in [
            "initial_state_sigma_m",
            "nav_position_sigma_m",
            "nav_velocity_sigma_mps",
            "integration_step_s",
            "non_physical_capture_bias",
        ]:
            value = trajectory.get(name)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                errors.append(f"scenario.trajectory_model.{name} must be finite number")

    correction = scenario.get("correction_window", {})
    if not isinstance(correction, dict):
        errors.append("scenario.correction_window must be object")
    else:
        if not isinstance(correction.get("enabled"), bool):
            errors.append("scenario.correction_window.enabled must be boolean")
        if correction.get("actuation_model") not in {"deterministic_impulse", "low_thrust_profile"}:
            errors.append("scenario.correction_window.actuation_model is invalid")
        for name in [
            "start_year",
            "end_year",
            "max_duration_years",
            "delta_v_budget_mps",
            "specific_impulse_s",
            "power_available_w",
            "actuator_efficiency",
            "guidance_sigma_rad",
            "execution_sigma_fraction",
        ]:
            value = correction.get(name)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                errors.append(f"scenario.correction_window.{name} must be finite number")
        if isinstance(correction.get("start_year"), (int, float)) and isinstance(
            correction.get("end_year"),
            (int, float),
        ):
            if float(correction["end_year"]) < float(correction["start_year"]):
                errors.append("scenario.correction_window.end_year must be >= start_year")
        if isinstance(correction.get("max_duration_years"), (int, float)) and float(
            correction["max_duration_years"]
        ) > 2000:
            errors.append("scenario.correction_window.max_duration_years must be <= 2000")

    capsule = scenario.get("capsule_model", {})
    if not isinstance(capsule, dict):
        errors.append("scenario.capsule_model must be object")
    else:
        for name in [
            "mass_kg",
            "frontal_area_m2",
            "shield_areal_density_kg_m2",
            "data_media_survival_margin",
            "material_degradation_mu_1_per_year",
        ]:
            value = capsule.get(name)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                errors.append(f"scenario.capsule_model.{name} must be finite number")

    environment = scenario.get("environment_model", {})
    if not isinstance(environment, dict):
        errors.append("scenario.environment_model must be object")
    else:
        for name in [
            "radiative_flux_w_m2",
            "plasma_density_proxy_m3",
            "dust_flux_scale",
            "accretion_luminosity_fraction",
            "non_physical_safety_multiplier",
        ]:
            value = environment.get(name)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                errors.append(f"scenario.environment_model.{name} must be finite number")

    uncertainty_model = scenario.get("uncertainty_model")
    if not isinstance(uncertainty_model, list) or len(uncertainty_model) < 4:
        errors.append("scenario.uncertainty_model must be array with >=4 entries")
    else:
        errors.extend(_validate_uncertainty_model(uncertainty_model))

    speculative_overrides = scenario.get("speculative_overrides")
    if not isinstance(speculative_overrides, list):
        errors.append("scenario.speculative_overrides must be array")
    elif mission_mode == "realistic" and len(speculative_overrides) > 0:
        errors.append("realistic mode forbids speculative_overrides")

    parameter_tags = scenario.get("parameter_tags")
    if not isinstance(parameter_tags, dict) or len(parameter_tags) == 0:
        errors.append("scenario.parameter_tags must be non-empty object")
    else:
        for key, value in parameter_tags.items():
            if not isinstance(value, dict):
                errors.append(f"scenario.parameter_tags.{key} must be object")
                continue
            category = value.get("category")
            mode = value.get("mode")
            warning_text = value.get("warning_text")
            parameter_id = value.get("parameter_id")
            if category not in ALLOWED_PARAM_CATEGORIES:
                errors.append(f"scenario.parameter_tags.{key}.category invalid")
            if mode not in ALLOWED_PARAM_MODES:
                errors.append(f"scenario.parameter_tags.{key}.mode invalid")
            if not isinstance(warning_text, str) or len(warning_text.strip()) == 0:
                errors.append(
                    f"scenario.parameter_tags.{key}.warning_text must be non-empty string"
                )
            if not isinstance(parameter_id, str) or len(parameter_id.strip()) == 0:
                errors.append(
                    f"scenario.parameter_tags.{key}.parameter_id must be non-empty string"
                )

    outputs_required = scenario.get("outputs_required")
    if not isinstance(outputs_required, list) or len(outputs_required) == 0:
        errors.append("scenario.outputs_required must be non-empty array")
    else:
        missing_outputs = sorted(REQUIRED_OUTPUTS - set(outputs_required))
        if missing_outputs:
            errors.append(
                f"scenario.outputs_required missing fields: {', '.join(missing_outputs)}"
            )

    return errors
