"""Baseline output, verification, and CLI runner helpers."""

from __future__ import annotations

import copy
import hashlib
import math
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .constants import ALLOWED_RUN_MODES, MISSION_ENGINE_VERSION, REQUIRED_OUTPUTS
from .model import _core_probability, _trust_weighted_score, compute_probabilities
from .utils import canonical_json, load_claims_map, load_json
from .validation import validate_scenario, validate_schema_contract


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
