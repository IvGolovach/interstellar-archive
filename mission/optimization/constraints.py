"""Constraint evaluation for realistic optimization."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence


def evaluate_hard_constraints(scenario: Mapping[str, Any], output: Mapping[str, Any]) -> List[str]:
    violations: List[str] = []

    if not bool(output.get("crossing_condition_met", False)):
        violations.append("horizon_crossing_not_met")

    if not bool(output.get("environment_acceptable", False)):
        violations.append("environment_filter_rejected")

    correction = scenario.get("correction_window", {})
    if isinstance(correction, Mapping):
        try:
            start = float(correction.get("start_year", 0.0))
            end = float(correction.get("end_year", 0.0))
            max_duration = float(correction.get("max_duration_years", 0.0))
        except (TypeError, ValueError):
            violations.append("correction_window_invalid")
        else:
            if end < start:
                violations.append("correction_window_negative_duration")
            if max_duration > 0 and (end - start) > max_duration:
                violations.append("correction_window_exceeds_max_duration")

    return violations


def evaluate_soft_constraints(
    *,
    baseline_scenario: Mapping[str, Any],
    scenario: Mapping[str, Any],
    output: Mapping[str, Any],
) -> Dict[str, Any]:
    p_survive = float(output.get("p_survive", 0.0))
    p_data_intact = float(output.get("p_data_intact", 0.0))

    risk_metric = max(0.0, min(1.0, 0.65 * (1.0 - p_survive) + 0.35 * (1.0 - p_data_intact)))

    correction = scenario.get("correction_window", {})
    baseline_correction = baseline_scenario.get("correction_window", {})

    power_penalty = 0.0
    delta_v_penalty = 0.0
    duration_penalty = 0.0

    if isinstance(correction, Mapping) and isinstance(baseline_correction, Mapping):
        baseline_power = float(baseline_correction.get("power_available_w", 1.0))
        baseline_delta_v = float(baseline_correction.get("delta_v_budget_mps", 1.0))
        baseline_duration = float(baseline_correction.get("max_duration_years", 1.0))

        power = float(correction.get("power_available_w", baseline_power))
        delta_v = float(correction.get("delta_v_budget_mps", baseline_delta_v))
        duration = float(correction.get("end_year", 0.0)) - float(correction.get("start_year", 0.0))

        if baseline_power > 0 and power > baseline_power:
            power_penalty = (power - baseline_power) / baseline_power
        if baseline_delta_v > 0 and delta_v > baseline_delta_v:
            delta_v_penalty = (delta_v - baseline_delta_v) / baseline_delta_v
        if baseline_duration > 0 and duration > baseline_duration:
            duration_penalty = (duration - baseline_duration) / baseline_duration

    penalty = risk_metric + 0.5 * power_penalty + 0.5 * delta_v_penalty + 0.5 * duration_penalty

    soft_violations: List[str] = []
    if power_penalty > 0:
        soft_violations.append("power_above_baseline")
    if delta_v_penalty > 0:
        soft_violations.append("delta_v_above_baseline")
    if duration_penalty > 0:
        soft_violations.append("correction_window_above_baseline")

    return {
        "risk_metric": round(risk_metric, 12),
        "penalty": round(penalty, 12),
        "soft_violations": soft_violations,
        "components": {
            "risk_metric": round(risk_metric, 12),
            "power_penalty": round(power_penalty, 12),
            "delta_v_penalty": round(delta_v_penalty, 12),
            "duration_penalty": round(duration_penalty, 12),
        },
    }


def summarize_constraint_violations(candidates: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    hard: Dict[str, int] = {}
    soft: Dict[str, int] = {}

    for item in candidates:
        for violation in item.get("hard_violations", []):
            hard[str(violation)] = hard.get(str(violation), 0) + 1
        for violation in item.get("soft_violations", []):
            soft[str(violation)] = soft.get(str(violation), 0) + 1

    return {
        "hard": dict(sorted(hard.items())),
        "soft": dict(sorted(soft.items())),
        "hard_total": sum(hard.values()),
        "soft_total": sum(soft.values()),
    }
