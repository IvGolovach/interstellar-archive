"""Public baseline mission-definition API."""

from mission.baseline.constants import (
    ALLOWED_RUN_MODES,
    MISSION_ENGINE_VERSION,
    PARAMETER_CLAIMS_PATH,
    REQUIRED_OUTPUTS,
    SPECULATIVE_NEUTRAL_VALUES,
)
from mission.baseline.model import compute_probabilities, schwarzschild_radius_m
from mission.baseline.output import build_output, dual_result, run_baseline, verify_required_outputs
from mission.baseline.utils import canonical_json, load_claims_map, load_json
from mission.baseline.validation import validate_schema_contract, validate_scenario

__all__ = [
    "ALLOWED_RUN_MODES",
    "MISSION_ENGINE_VERSION",
    "PARAMETER_CLAIMS_PATH",
    "REQUIRED_OUTPUTS",
    "SPECULATIVE_NEUTRAL_VALUES",
    "build_output",
    "canonical_json",
    "compute_probabilities",
    "dual_result",
    "load_claims_map",
    "load_json",
    "run_baseline",
    "schwarzschild_radius_m",
    "validate_schema_contract",
    "validate_scenario",
    "verify_required_outputs",
]
