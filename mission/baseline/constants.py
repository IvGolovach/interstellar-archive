"""Shared constants for the mission baseline layer."""

from __future__ import annotations

from pathlib import Path

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
