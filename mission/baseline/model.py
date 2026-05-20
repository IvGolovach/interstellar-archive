"""Core mission baseline probability model."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .constants import (
    C,
    G,
    MISSION_ENGINE_VERSION,
    SPECULATIVE_NEUTRAL_VALUES,
    TRUST_WEIGHTS,
)
from .utils import _clamp, _get_path, _round, _set_path, canonical_json


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
