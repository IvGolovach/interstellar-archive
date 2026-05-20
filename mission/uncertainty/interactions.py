"""Deterministic uncertainty interaction screen.

The artifact produced here evaluates pairwise stress residuals for the tracked
mission uncertainty dimensions. It deliberately keeps parameter correlations
and covariance evidence open instead of treating current independent bounds as
validated joint distributions.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from mission.baseline import compute_probabilities, load_claims_map


SCHEMA_VERSION = "uncertainty_interactions.v1"
GENERATOR = "scripts/build_uncertainty_interactions_artifact.py"
PUBLIC_SCOPE = "pairwise_uncertainty_interaction_screen"
SOURCE_BASELINE = "mission/BASELINE_SCENARIO_v1.json"
SOURCE_UNCERTAINTY_MODEL = "mission/UNCERTAINTY_MODEL_v1.json"
SOURCE_PARAMETER_CLAIMS = "parameters/registry/parameter_claims.v1.json"
SOURCE_RISK_ENVELOPE = "mission/objectives/risk_envelope.v1.json"
SOURCE_SENSITIVITY = "artifacts/parameter_sensitivity_summary.json"
SOURCE_P_SUCCESS = "artifacts/p_success_defensibility.json"
OPEN_STATUS = "external_correlation_evidence_required"
MODE = "realistic"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _round(value: float, digits: int = 12) -> float:
    rounded = float(f"{float(value):.{digits}f}")
    return 0.0 if rounded == 0.0 else rounded


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _get_path(payload: Mapping[str, Any], dotted_path: str) -> float:
    cursor: Any = payload
    for key in dotted_path.split("."):
        if not isinstance(cursor, Mapping):
            raise ValueError(f"{dotted_path} traverses a non-object")
        cursor = cursor[key]
    if not _is_number(cursor):
        raise ValueError(f"{dotted_path} is not numeric")
    return float(cursor)


def _set_path(payload: Dict[str, Any], dotted_path: str, value: float) -> None:
    cursor: Any = payload
    for key in dotted_path.split(".")[:-1]:
        cursor = cursor[key]
    cursor[dotted_path.split(".")[-1]] = value


def _probabilities_for(scenario: Mapping[str, Any]) -> Dict[str, float]:
    result = compute_probabilities(scenario, mode=MODE)
    return {
        "p_success": _round(float(result["p_success"])),
        "p_hit": _round(float(result["p_hit"])),
        "p_survive": _round(float(result["p_survive"])),
        "p_data_intact": _round(float(result["p_data_intact"])),
    }


def _scenario_with(base: Mapping[str, Any], updates: Mapping[str, float]) -> Dict[str, Any]:
    scenario = copy.deepcopy(dict(base))
    for parameter_id, value in updates.items():
        _set_path(scenario, parameter_id, float(value))
    return scenario


def _source_artifacts(repo_root: Path) -> List[Dict[str, str]]:
    paths = [
        SOURCE_BASELINE,
        SOURCE_UNCERTAINTY_MODEL,
        SOURCE_PARAMETER_CLAIMS,
        SOURCE_RISK_ENVELOPE,
        SOURCE_SENSITIVITY,
        SOURCE_P_SUCCESS,
    ]
    return [
        {
            "path": path,
            "sha256": _sha256_file(repo_root / path),
        }
        for path in paths
    ]


def _entry_id(parameter_id: str) -> str:
    return "ui-param-" + parameter_id.replace(".", "-").replace("_", "-")


def _pair_id(left: str, right: str) -> str:
    return "ui-pair-" + left.replace(".", "-").replace("_", "-") + "--" + right.replace(".", "-").replace("_", "-")


def _interaction_class(residual_abs: float) -> str:
    if residual_abs <= 1e-9:
        return "negligible"
    if residual_abs <= 1e-4:
        return "weak"
    return "material"


def _selected_entries(uncertainty_model: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    entries = uncertainty_model.get("entries")
    if not isinstance(entries, list):
        return []
    selected: List[Mapping[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        entry_mode = str(entry.get("mode", ""))
        if entry_mode in {"realistic", "both"}:
            selected.append(entry)
    selected.sort(key=lambda item: str(item.get("parameter_id", "")))
    return selected


def _stress_values(entry: Mapping[str, Any], baseline: Mapping[str, Any]) -> Dict[str, float]:
    parameter_id = str(entry["parameter_id"])
    bounds = entry.get("bounds")
    if not isinstance(bounds, Mapping):
        raise ValueError(f"{parameter_id}: bounds must be object")
    low = bounds.get("min")
    high = bounds.get("max")
    if not (_is_number(low) and _is_number(high)):
        raise ValueError(f"{parameter_id}: bounds.min/max must be finite numbers")
    if not float(low) < float(high):
        raise ValueError(f"{parameter_id}: bounds must satisfy min < max")
    nominal = _get_path(baseline, parameter_id)
    return {
        "low": _round(float(low)),
        "nominal": _round(nominal),
        "high": _round(float(high)),
    }


def _main_effect(
    *,
    baseline: Mapping[str, Any],
    baseline_probability: float,
    entry: Mapping[str, Any],
    claims_map: Mapping[str, Mapping[str, Any]],
    sensitivity_summary: Mapping[str, Any],
) -> Dict[str, Any]:
    parameter_id = str(entry["parameter_id"])
    stress = _stress_values(entry, baseline)
    low_p = _probabilities_for(_scenario_with(baseline, {parameter_id: stress["low"]}))["p_success"]
    high_p = _probabilities_for(_scenario_with(baseline, {parameter_id: stress["high"]}))["p_success"]
    low_effect = _round(low_p - baseline_probability)
    high_effect = _round(high_p - baseline_probability)
    claim = claims_map.get(parameter_id, {})
    summaries = sensitivity_summary.get("summaries", {}) if isinstance(sensitivity_summary, Mapping) else {}
    return {
        "entry_id": _entry_id(parameter_id),
        "parameter_id": parameter_id,
        "distribution": entry.get("distribution"),
        "units": entry.get("units"),
        "mode": entry.get("mode"),
        "category": entry.get("category"),
        "trust_grade": claim.get("trust_grade", "D") if isinstance(claim, Mapping) else "D",
        "source_rationale": entry.get("source_rationale") or entry.get("rationale"),
        "stress_values": stress,
        "p_success_low": low_p,
        "p_success_nominal": baseline_probability,
        "p_success_high": high_p,
        "effect_low": low_effect,
        "effect_high": high_effect,
        "max_abs_effect": _round(max(abs(low_effect), abs(high_effect))),
        "sensitivity_summary": summaries.get(parameter_id) if isinstance(summaries, Mapping) else None,
        "claim_boundary": "Endpoint stress over declared uncertainty bounds; not a validated probability mass or covariance model.",
    }


def _pair_row(
    *,
    baseline: Mapping[str, Any],
    baseline_probability: float,
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    main_effects: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    left_id = str(left["parameter_id"])
    right_id = str(right["parameter_id"])
    left_stress = main_effects[left_id]["stress_values"]
    right_stress = main_effects[right_id]["stress_values"]
    low_low = _probabilities_for(
        _scenario_with(baseline, {left_id: float(left_stress["low"]), right_id: float(right_stress["low"])})
    )["p_success"]
    high_high = _probabilities_for(
        _scenario_with(baseline, {left_id: float(left_stress["high"]), right_id: float(right_stress["high"])})
    )["p_success"]
    low_high = _probabilities_for(
        _scenario_with(baseline, {left_id: float(left_stress["low"]), right_id: float(right_stress["high"])})
    )["p_success"]
    high_low = _probabilities_for(
        _scenario_with(baseline, {left_id: float(left_stress["high"]), right_id: float(right_stress["low"])})
    )["p_success"]

    low_low_residual = _round(
        (low_low - baseline_probability)
        - float(main_effects[left_id]["effect_low"])
        - float(main_effects[right_id]["effect_low"])
    )
    high_high_residual = _round(
        (high_high - baseline_probability)
        - float(main_effects[left_id]["effect_high"])
        - float(main_effects[right_id]["effect_high"])
    )
    low_high_residual = _round(
        (low_high - baseline_probability)
        - float(main_effects[left_id]["effect_low"])
        - float(main_effects[right_id]["effect_high"])
    )
    high_low_residual = _round(
        (high_low - baseline_probability)
        - float(main_effects[left_id]["effect_high"])
        - float(main_effects[right_id]["effect_low"])
    )
    residual_abs = _round(
        max(
            abs(low_low_residual),
            abs(high_high_residual),
            abs(low_high_residual),
            abs(high_low_residual),
        )
    )
    return {
        "pair_id": _pair_id(left_id, right_id),
        "parameter_ids": [left_id, right_id],
        "status": OPEN_STATUS,
        "baseline_p_success": baseline_probability,
        "stress_p_success": {
            "low_low": low_low,
            "low_high": low_high,
            "high_low": high_low,
            "high_high": high_high,
        },
        "main_effect_reference": {
            left_id: {
                "effect_low": main_effects[left_id]["effect_low"],
                "effect_high": main_effects[left_id]["effect_high"],
            },
            right_id: {
                "effect_low": main_effects[right_id]["effect_low"],
                "effect_high": main_effects[right_id]["effect_high"],
            },
        },
        "interaction_residual": {
            "low_low": low_low_residual,
            "low_high": low_high_residual,
            "high_low": high_low_residual,
            "high_high": high_high_residual,
            "max_abs": residual_abs,
            "classification": _interaction_class(residual_abs),
        },
        "correlation": {
            "rho": None,
            "status": OPEN_STATUS,
            "evidence_gap_id": "validated_parameter_correlation_matrix",
        },
        "claim_boundary": "Pairwise endpoint residual is computed; correlation and covariance evidence remain external.",
    }


def build_uncertainty_interactions(repo_root: Path) -> Dict[str, Any]:
    baseline = _load_json(repo_root / SOURCE_BASELINE)
    uncertainty_model = _load_json(repo_root / SOURCE_UNCERTAINTY_MODEL)
    sensitivity_summary = _load_json(repo_root / SOURCE_SENSITIVITY)
    claims_map = load_claims_map(repo_root)
    baseline_probability = _probabilities_for(baseline)
    selected_entries = _selected_entries(uncertainty_model)
    main_effect_rows = [
        _main_effect(
            baseline=baseline,
            baseline_probability=baseline_probability["p_success"],
            entry=entry,
            claims_map=claims_map,
            sensitivity_summary=sensitivity_summary,
        )
        for entry in selected_entries
    ]
    main_effect_rows.sort(key=lambda item: (-float(item["max_abs_effect"]), item["parameter_id"]))
    main_by_id = {str(item["parameter_id"]): item for item in main_effect_rows}
    pair_rows = [
        _pair_row(
            baseline=baseline,
            baseline_probability=baseline_probability["p_success"],
            left=left,
            right=right,
            main_effects=main_by_id,
        )
        for left, right in combinations(selected_entries, 2)
    ]
    pair_rows.sort(
        key=lambda item: (-float(item["interaction_residual"]["max_abs"]), item["pair_id"])
    )
    dominant_pair = pair_rows[0]["pair_id"] if pair_rows else None
    material_pairs = [
        item["pair_id"]
        for item in pair_rows
        if item["interaction_residual"]["classification"] == "material"
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "public_scope": PUBLIC_SCOPE,
        "non_certification_notice": True,
        "mode": MODE,
        "source_artifacts": _source_artifacts(repo_root),
        "method": {
            "name": "deterministic_pairwise_endpoint_residual",
            "baseline_metric": "p_success",
            "definition": "interaction_residual = joint_endpoint_delta - sum(individual_endpoint_deltas)",
            "stress_policy": "low/high endpoints come from declared uncertainty_model bounds",
            "correlation_policy": "correlation coefficients remain null until external covariance evidence exists",
        },
        "baseline": baseline_probability,
        "uncertainty_entry_count": len(main_effect_rows),
        "interaction_pair_count": len(pair_rows),
        "main_effects": main_effect_rows,
        "pair_interactions": pair_rows,
        "rollup": {
            "dominant_pair_id": dominant_pair,
            "material_pair_count": len(material_pairs),
            "material_pair_ids": material_pairs,
            "pairs_requiring_external_correlation_evidence": len(pair_rows),
            "validated_correlation_count": 0,
            "full_uncertainty_interaction_closure": False,
        },
        "external_evidence_gaps": [
            "validated_parameter_correlation_matrix",
            "path_conditioned_uncertainty_distribution",
            "model_form_validation_for_joint_uncertainty",
        ],
        "blocked_claims": [
            "validated uncertainty independence",
            "closed covariance model",
            "certified probability interval",
            "flight ready",
        ],
        "interpretation_limits": [
            "Pairwise residuals are deterministic stress screens, not a full Sobol or covariance analysis.",
            "Correlation coefficients are intentionally null until external validation exists.",
            "The artifact ranks model interaction risk; it does not certify a mission probability interval.",
        ],
    }


def _source_hashes(payload: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    source_artifacts = payload.get("source_artifacts")
    if not isinstance(source_artifacts, list):
        return out
    for item in source_artifacts:
        if isinstance(item, Mapping) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str):
            out[str(item["path"])] = str(item["sha256"])
    return out


def _validate_probability(value: Any, prefix: str, errors: List[str]) -> None:
    if not _is_number(value) or not 0.0 <= float(value) <= 1.0:
        errors.append(f"{prefix} must be a finite probability in [0,1]")


def validate_uncertainty_interactions(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r}")
    if payload.get("generator") != GENERATOR:
        errors.append(f"generator mismatch: {payload.get('generator')!r}")
    if payload.get("public_scope") != PUBLIC_SCOPE:
        errors.append(f"public_scope mismatch: {payload.get('public_scope')!r}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("mode") != MODE:
        errors.append("mode must be realistic")

    source_hashes = _source_hashes(payload)
    for path in (
        SOURCE_BASELINE,
        SOURCE_UNCERTAINTY_MODEL,
        SOURCE_PARAMETER_CLAIMS,
        SOURCE_RISK_ENVELOPE,
        SOURCE_SENSITIVITY,
        SOURCE_P_SUCCESS,
    ):
        value = source_hashes.get(path)
        if not isinstance(value, str) or len(value) != 64:
            errors.append(f"source_artifacts missing sha256 for {path}")

    baseline = payload.get("baseline")
    if not isinstance(baseline, Mapping):
        errors.append("baseline must be object")
    else:
        for key in ("p_success", "p_hit", "p_survive", "p_data_intact"):
            _validate_probability(baseline.get(key), f"baseline.{key}", errors)

    main_effects = payload.get("main_effects")
    if not isinstance(main_effects, list) or len(main_effects) < 2:
        errors.append("main_effects must contain at least two rows")
        main_effects = []
    if payload.get("uncertainty_entry_count") != len(main_effects):
        errors.append("uncertainty_entry_count must match main_effects length")

    main_by_id: Dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(main_effects):
        if not isinstance(row, Mapping):
            errors.append(f"main_effects[{index}] must be object")
            continue
        parameter_id = row.get("parameter_id")
        if not isinstance(parameter_id, str) or not parameter_id:
            errors.append(f"main_effects[{index}].parameter_id must be non-empty string")
            continue
        if parameter_id in main_by_id:
            errors.append(f"duplicate main_effect parameter_id: {parameter_id}")
        main_by_id[parameter_id] = row
        stress = row.get("stress_values")
        if not isinstance(stress, Mapping):
            errors.append(f"main_effects[{index}].stress_values must be object")
        else:
            for key in ("low", "nominal", "high"):
                if not _is_number(stress.get(key)):
                    errors.append(f"main_effects[{index}].stress_values.{key} must be numeric")
            if _is_number(stress.get("low")) and _is_number(stress.get("high")):
                if not float(stress["low"]) < float(stress["high"]):
                    errors.append(f"main_effects[{index}].stress_values must satisfy low < high")
        for key in ("p_success_low", "p_success_nominal", "p_success_high"):
            _validate_probability(row.get(key), f"main_effects[{index}].{key}", errors)
        if not _is_number(row.get("max_abs_effect")) or float(row.get("max_abs_effect", -1.0)) < 0.0:
            errors.append(f"main_effects[{index}].max_abs_effect must be >= 0")

    pairs = payload.get("pair_interactions")
    if not isinstance(pairs, list):
        errors.append("pair_interactions must be list")
        pairs = []
    expected_pair_count = len(main_effects) * (len(main_effects) - 1) // 2
    if payload.get("interaction_pair_count") != len(pairs):
        errors.append("interaction_pair_count must match pair_interactions length")
    if len(pairs) != expected_pair_count:
        errors.append(f"pair_interactions must contain nC2 rows: {len(pairs)} != {expected_pair_count}")

    seen_pairs: set[str] = set()
    baseline_p = baseline.get("p_success") if isinstance(baseline, Mapping) else None
    for index, pair in enumerate(pairs):
        if not isinstance(pair, Mapping):
            errors.append(f"pair_interactions[{index}] must be object")
            continue
        pair_id = pair.get("pair_id")
        if not isinstance(pair_id, str) or not pair_id:
            errors.append(f"pair_interactions[{index}].pair_id must be non-empty string")
        elif pair_id in seen_pairs:
            errors.append(f"duplicate pair_id: {pair_id}")
        else:
            seen_pairs.add(pair_id)
        if pair.get("status") != OPEN_STATUS:
            errors.append(f"pair_interactions[{index}].status must be {OPEN_STATUS}")
        parameter_ids = pair.get("parameter_ids")
        if not isinstance(parameter_ids, list) or len(parameter_ids) != 2:
            errors.append(f"pair_interactions[{index}].parameter_ids must contain two ids")
            parameter_ids = []
        for parameter_id in parameter_ids:
            if parameter_id not in main_by_id:
                errors.append(f"pair_interactions[{index}] references unknown parameter {parameter_id!r}")
        stress = pair.get("stress_p_success")
        if not isinstance(stress, Mapping):
            errors.append(f"pair_interactions[{index}].stress_p_success must be object")
            stress = {}
        for key in ("low_low", "low_high", "high_low", "high_high"):
            _validate_probability(stress.get(key), f"pair_interactions[{index}].stress_p_success.{key}", errors)
        residual = pair.get("interaction_residual")
        if not isinstance(residual, Mapping):
            errors.append(f"pair_interactions[{index}].interaction_residual must be object")
            residual = {}
        if residual.get("classification") not in {"negligible", "weak", "material"}:
            errors.append(f"pair_interactions[{index}].interaction_residual.classification invalid")
        if not _is_number(residual.get("max_abs")) or float(residual.get("max_abs", -1.0)) < 0.0:
            errors.append(f"pair_interactions[{index}].interaction_residual.max_abs must be >= 0")
        correlation = pair.get("correlation")
        if not isinstance(correlation, Mapping):
            errors.append(f"pair_interactions[{index}].correlation must be object")
        elif correlation.get("rho") is not None or correlation.get("status") != OPEN_STATUS:
            errors.append(f"pair_interactions[{index}].correlation must keep rho null and status open")
        if (
            len(parameter_ids) == 2
            and _is_number(baseline_p)
            and all(parameter_id in main_by_id for parameter_id in parameter_ids)
        ):
            left = main_by_id[str(parameter_ids[0])]
            right = main_by_id[str(parameter_ids[1])]
            combos = {
                "low_low": ("effect_low", "effect_low"),
                "low_high": ("effect_low", "effect_high"),
                "high_low": ("effect_high", "effect_low"),
                "high_high": ("effect_high", "effect_high"),
            }
            for name, (left_key, right_key) in combos.items():
                if not (_is_number(stress.get(name)) and _is_number(left.get(left_key)) and _is_number(right.get(right_key))):
                    continue
                expected = _round(
                    float(stress[name]) - float(baseline_p) - float(left[left_key]) - float(right[right_key])
                )
                actual = residual.get(name)
                if not _is_number(actual) or abs(float(actual) - expected) > 1e-12:
                    errors.append(f"pair_interactions[{index}].interaction_residual.{name} formula mismatch")

    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
    else:
        if rollup.get("validated_correlation_count") != 0:
            errors.append("rollup.validated_correlation_count must remain 0")
        if rollup.get("full_uncertainty_interaction_closure") is not False:
            errors.append("rollup.full_uncertainty_interaction_closure must be false")
        if rollup.get("pairs_requiring_external_correlation_evidence") != len(pairs):
            errors.append("rollup.pairs_requiring_external_correlation_evidence must equal pair count")

    for field in ("external_evidence_gaps", "blocked_claims", "interpretation_limits"):
        value = payload.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"{field} must be a non-empty list")
    blocked = payload.get("blocked_claims")
    if isinstance(blocked, list):
        forbidden = {"certified probability interval", "validated uncertainty independence"}
        if not forbidden.issubset({str(item) for item in blocked}):
            errors.append("blocked_claims must block probability interval and independence closure claims")
    return errors
