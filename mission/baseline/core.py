"""Deterministic mission-definition v1 baseline core."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

G = 6.67430e-11
C = 299_792_458.0
MISSION_ENGINE_VERSION = "mission-definition-v1"
PARAMETER_CLAIMS_PATH = Path("parameters/registry/parameter_claims.v1.json")

ALLOWED_MISSION_MODES = {"realistic", "speculative"}
ALLOWED_RUN_MODES = {"realistic", "speculative", "dual"}
ALLOWED_ENV_MODES = {"strict", "proxy"}
ALLOWED_DISTRIBUTIONS = {"normal", "lognormal", "uniform", "triangular"}
ALLOWED_PARAM_CATEGORIES = {"safe", "advanced", "non_physical"}
ALLOWED_PARAM_MODES = {"realistic", "speculative", "both"}
SPECULATIVE_PARAMETER_PATHS = (
    "trajectory_model.non_physical_capture_bias",
    "environment_model.non_physical_safety_multiplier",
)
SPECULATIVE_NEUTRAL_VALUES = {
    "trajectory_model.non_physical_capture_bias": 0.0,
    "environment_model.non_physical_safety_multiplier": 1.0,
}
TRUST_WEIGHTS = {"A": 1.0, "B": 0.9, "C": 0.75, "D": 0.5}
REQUIRED_OUTPUTS = {
    "schwarzschild_radius_m",
    "crossing_condition_met",
    "environment_acceptable",
    "p_hit",
    "p_survive",
    "p_data_intact",
    "p_success",
    "success_threshold",
    "success",
    "mode",
    "speculative_parameters_used",
    "trust_weighted_score",
    "core_probability",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_claims_map(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    claims_path = repo_root / PARAMETER_CLAIMS_PATH
    if not claims_path.exists():
        return {}
    payload = load_json(claims_path)
    claims = payload.get("claims", [])
    if not isinstance(claims, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for claim in claims:
        if isinstance(claim, dict) and isinstance(claim.get("parameter_id"), str):
            out[str(claim["parameter_id"])] = claim
    return out


def _round(value: float, digits: int = 12) -> float:
    return float(f"{value:.{digits}f}")


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _get_path(data: Mapping[str, Any], dotted_path: str) -> float:
    cursor: Any = data
    for key in dotted_path.split("."):
        cursor = cursor[key]
    if isinstance(cursor, bool) or not isinstance(cursor, (int, float)):
        raise TypeError(f"path '{dotted_path}' is not numeric")
    return float(cursor)


def _set_path(data: Dict[str, Any], dotted_path: str, value: float) -> None:
    cursor: Any = data
    parts = dotted_path.split(".")
    for key in parts[:-1]:
        cursor = cursor[key]
    cursor[parts[-1]] = value

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


def schwarzschild_radius_m(mass_kg: float) -> float:
    return 2.0 * G * mass_kg / (C**2)


def is_bh_environment_acceptable(scenario: Dict[str, Any]) -> bool:
    mode = scenario["environment_acceptance_mode"]
    alpha = 1.0 if mode == "strict" else 1.2

    env = scenario["environment_model"]
    bh = scenario["bh_parameters"]

    checks = (
        env["radiative_flux_w_m2"] <= alpha * bh["max_radiative_flux_w_m2"],
        env["plasma_density_proxy_m3"] <= alpha * bh["max_plasma_density_proxy_m3"],
        env["dust_flux_scale"] <= alpha * bh["max_dust_flux_scale"],
    )
    return all(checks)


def _project_realistic(scenario: Dict[str, Any]) -> Dict[str, Any]:
    projected = copy.deepcopy(scenario)
    projected["mission_mode"] = "realistic"
    for path, neutral in SPECULATIVE_NEUTRAL_VALUES.items():
        _set_path(projected, path, float(neutral))
    return projected


def _resolve_mode_controls(scenario: Dict[str, Any], mode: str) -> Tuple[float, float, List[str]]:
    if mode not in {"realistic", "speculative"}:
        raise ValueError(f"unsupported mode: {mode}")
    if mode == "realistic":
        return (
            float(SPECULATIVE_NEUTRAL_VALUES["trajectory_model.non_physical_capture_bias"]),
            float(SPECULATIVE_NEUTRAL_VALUES["environment_model.non_physical_safety_multiplier"]),
            [],
        )

    capture_bias = _get_path(scenario, "trajectory_model.non_physical_capture_bias")
    safety_multiplier = _get_path(
        scenario,
        "environment_model.non_physical_safety_multiplier",
    )
    used: List[str] = []
    if not math.isclose(
        capture_bias,
        float(SPECULATIVE_NEUTRAL_VALUES["trajectory_model.non_physical_capture_bias"]),
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        used.append("trajectory_model.non_physical_capture_bias")
    if not math.isclose(
        safety_multiplier,
        float(SPECULATIVE_NEUTRAL_VALUES["environment_model.non_physical_safety_multiplier"]),
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        used.append("environment_model.non_physical_safety_multiplier")
    return capture_bias, safety_multiplier, used


def _compute_core_probabilities(
    scenario: Dict[str, Any],
    capture_bias: float,
    safety_multiplier: float,
) -> Dict[str, float]:
    bh = scenario["bh_parameters"]
    env = scenario["environment_model"]
    traj = scenario["trajectory_model"]
    correction = scenario["correction_window"]
    capsule = scenario["capsule_model"]

    r_s = schwarzschild_radius_m(float(bh["mass_kg"]))
    r_periapsis = float(bh["periapsis_distance_m"])
    d_miss = max(0.0, r_periapsis - r_s)

    sigma_nav = float(traj["nav_position_sigma_m"])
    sigma_guidance = r_periapsis * float(correction["guidance_sigma_rad"])
    sigma_exec = r_periapsis * float(correction["execution_sigma_fraction"]) * 1e-3
    sigma_eff = max(1.0, math.sqrt(sigma_nav**2 + sigma_guidance**2 + sigma_exec**2))

    p_hit = math.exp(-0.5 * (d_miss / sigma_eff) ** 2)
    p_hit = _clamp(p_hit + float(capture_bias))

    h_f = float(env["radiative_flux_w_m2"]) / float(bh["max_radiative_flux_w_m2"])
    h_rho = float(env["plasma_density_proxy_m3"]) / float(bh["max_plasma_density_proxy_m3"])
    h_s = float(env["dust_flux_scale"]) / float(bh["max_dust_flux_scale"])
    h_max = max(h_f, h_rho, h_s)

    env_ok = is_bh_environment_acceptable(scenario)
    mu_deg = float(capsule["material_degradation_mu_1_per_year"])

    p_survive = math.exp(-0.8 * h_max - mu_deg)
    p_survive *= float(safety_multiplier)
    if not env_ok:
        p_survive *= 0.01
    p_survive = _clamp(p_survive)

    media_margin = float(capsule["data_media_survival_margin"])
    p_data_intact = media_margin * math.exp(-0.6 * h_f) * max(0.0, 1.0 - mu_deg)
    p_data_intact = _clamp(p_data_intact)

    p_success = _clamp(p_hit * p_survive * p_data_intact)

    return {
        "schwarzschild_radius_m": _round(r_s),
        "crossing_condition_met": r_periapsis <= r_s,
        "environment_acceptable": env_ok,
        "p_hit": _round(p_hit),
        "p_survive": _round(p_survive),
        "p_data_intact": _round(p_data_intact),
        "p_success": _round(p_success),
    }


def compute_probabilities(scenario: Dict[str, Any], mode: str) -> Dict[str, Any]:
    capture_bias, safety_multiplier, speculative_used = _resolve_mode_controls(scenario, mode)
    probabilities = _compute_core_probabilities(
        scenario=scenario,
        capture_bias=capture_bias,
        safety_multiplier=safety_multiplier,
    )
    probabilities["speculative_parameters_used"] = speculative_used
    return probabilities


def _core_probability(scenario: Dict[str, Any]) -> float:
    projected = _project_realistic(scenario)
    probabilities = compute_probabilities(projected, mode="realistic")
    return float(probabilities["p_success"])


def _trust_weighted_score(
    p_success: float,
    mode: str,
    claims_map: Mapping[str, Dict[str, Any]],
    speculative_parameters_used: Sequence[str],
) -> float:
    core_ids: List[str] = []
    for parameter_id, claim in claims_map.items():
        if parameter_id.startswith("code_literal."):
            continue
        if "non_physical_" in parameter_id and mode == "realistic":
            continue
        core_ids.append(parameter_id)

    if mode == "speculative":
        core_ids.extend(speculative_parameters_used)

    weights: List[float] = []
    for parameter_id in sorted(set(core_ids)):
        grade = str(claims_map.get(parameter_id, {}).get("trust_grade", "D"))
        weights.append(float(TRUST_WEIGHTS.get(grade, TRUST_WEIGHTS["D"])))

    mean_weight = sum(weights) / len(weights) if weights else TRUST_WEIGHTS["D"]
    return _round(float(p_success) * mean_weight, 12)

def verify_required_outputs(output: Dict[str, Any], required: Iterable[str]) -> list[str]:
    errors: list[str] = []
    output_keys = set(output.keys())
    for field in required:
        if field not in output_keys:
            errors.append(
                f"required output field '{field}' missing from mission baseline output"
            )
    return errors


def dual_result(realistic_output: Dict[str, Any], speculative_output: Dict[str, Any]) -> Dict[str, Any]:
    realistic = float(realistic_output["p_success"])
    speculative = float(speculative_output["p_success"])
    multiplier = float("inf") if realistic <= 0 else speculative / realistic
    payload: Dict[str, Any] = {
        "mode": "dual",
        "realistic_result": realistic_output,
        "speculative_result": speculative_output,
        "divergence": {
            "absolute_delta": float(f"{abs(speculative - realistic):.12f}"),
            "multiplier": float(f"{multiplier if math.isfinite(multiplier) else 1e12:.12f}"),
        },
    }
    payload["deterministic_signature"] = hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return payload


def print_dual_report(
    realistic_output: Mapping[str, Any],
    speculative_output: Mapping[str, Any],
) -> None:
    print("=== REALISTIC RESULT ===")
    print(f"p_success_realistic={realistic_output['p_success']}")
    print(f"core_probability={realistic_output['core_probability']}")
    print("=== SPECULATIVE RESULT ===")
    print(f"p_success_speculative={speculative_output['p_success']}")
    print(
        "speculative_parameters_used="
        f"{','.join(speculative_output['speculative_parameters_used']) or 'none'}"
    )


def build_output(
    scenario: Dict[str, Any],
    mode: str,
    claims_map: Mapping[str, Dict[str, Any]],
) -> Dict[str, Any]:
    if mode not in {"realistic", "speculative"}:
        raise ValueError(f"unsupported mode for output: {mode}")

    scenario_for_mode = copy.deepcopy(scenario)
    scenario_for_mode["mission_mode"] = mode

    probabilities = compute_probabilities(scenario_for_mode, mode=mode)
    speculative_parameters_used = list(probabilities.pop("speculative_parameters_used"))
    core_probability = _core_probability(scenario_for_mode)
    success_threshold = float(scenario["success_threshold"])
    success = probabilities["p_success"] >= success_threshold

    correction = scenario_for_mode["correction_window"]
    duration_years = float(correction["end_year"]) - float(correction["start_year"])

    output: Dict[str, Any] = {
        "mission_schema_version": scenario["schema_version"],
        "mission_engine_version": MISSION_ENGINE_VERSION,
        "mode": mode,
        "mission_mode": mode,
        "bh_model": scenario_for_mode["bh_model"],
        "environment_acceptance_mode": scenario_for_mode["environment_acceptance_mode"],
        "seed": scenario_for_mode["seed"],
        **probabilities,
        "speculative_parameters_used": speculative_parameters_used,
        "core_probability": float(f"{core_probability:.12f}"),
        "trust_weighted_score": _trust_weighted_score(
            p_success=float(probabilities["p_success"]),
            mode=mode,
            claims_map=claims_map,
            speculative_parameters_used=speculative_parameters_used,
        ),
        "success_threshold": float(f"{success_threshold:.12f}"),
        "success": success,
        "correction_window": {
            "enabled": bool(correction["enabled"]),
            "start_year": float(f"{float(correction['start_year']):.6f}"),
            "end_year": float(f"{float(correction['end_year']):.6f}"),
            "duration_years": float(f"{duration_years:.6f}"),
            "delta_v_budget_mps": float(f"{float(correction['delta_v_budget_mps']):.6f}"),
            "power_available_w": float(f"{float(correction['power_available_w']):.6f}"),
        },
        "uncertainty_count": len(scenario_for_mode["uncertainty_model"]),
    }

    output_payload = canonical_json(output)
    output["deterministic_signature"] = hashlib.sha256(
        output_payload.encode("utf-8")
    ).hexdigest()
    return output


def run_baseline(
    schema_path: Path,
    scenario_path: Path,
    mode: str,
    validate_only: bool,
    verify_deterministic: bool,
    output_path: Path | None,
) -> int:
    schema = load_json(schema_path)
    scenario = load_json(scenario_path)
    claims_map = load_claims_map(Path.cwd())

    errors: list[str] = []
    errors.extend(validate_schema_contract(schema))
    errors.extend(validate_scenario(schema, scenario))
    if mode not in ALLOWED_RUN_MODES:
        errors.append(f"unsupported run mode: {mode}")

    if errors:
        print("FAIL: mission definition validation")
        for item in errors:
            print(f"- {item}")
        return 2

    if validate_only:
        print("PASS: mission schema and baseline scenario validation")
        return 0

    if mode == "dual":
        realistic_a = build_output(scenario, mode="realistic", claims_map=claims_map)
        speculative_a = build_output(scenario, mode="speculative", claims_map=claims_map)
        output_a = dual_result(realistic_a, speculative_a)
        realistic_b = build_output(scenario, mode="realistic", claims_map=claims_map)
        speculative_b = build_output(scenario, mode="speculative", claims_map=claims_map)
        output_b = dual_result(realistic_b, speculative_b)
    else:
        output_a = build_output(scenario, mode=mode, claims_map=claims_map)
        output_b = build_output(scenario, mode=mode, claims_map=claims_map)

    if verify_deterministic and canonical_json(output_a) != canonical_json(output_b):
        print("FAIL: mission baseline output is non-deterministic")
        return 2

    required_outputs = scenario.get("outputs_required", [])
    if mode == "dual":
        output_errors = verify_required_outputs(output_a["realistic_result"], required_outputs)
        output_errors.extend(
            verify_required_outputs(output_a["speculative_result"], required_outputs)
        )
    else:
        output_errors = verify_required_outputs(output_a, required_outputs)
    if output_errors:
        print("FAIL: mission baseline output structure")
        for item in output_errors:
            print(f"- {item}")
        return 2

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(output_a, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if mode == "dual":
        print_dual_report(output_a["realistic_result"], output_a["speculative_result"])
        print(
            "PASS: mission baseline dual-mode check "
            f"(realistic={output_a['realistic_result']['p_success']}, "
            f"speculative={output_a['speculative_result']['p_success']}, "
            f"multiplier={output_a['divergence']['multiplier']})"
        )
    else:
        print(
            "PASS: mission baseline check "
            f"(mode={mode}, p_success={output_a['p_success']}, "
            f"threshold={output_a['success_threshold']}, success={output_a['success']})"
        )
    return 0
