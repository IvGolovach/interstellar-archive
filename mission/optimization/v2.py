"""Optimization v2 decision-surface helpers.

The v2 layer deliberately wraps the existing realistic frontier instead of
replacing it.  It adds two bounded screening axes that are useful for review,
while keeping the objective aggregation Pareto-first and non-certifying.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


SCHEMA_VERSION = "optimization_v2_frontier.v1"
GENERATOR = "scripts/build_optimization_v2_artifact.py"
MODE = "realistic"
AXIS_IDS = ("p_success", "risk_envelope", "qualification_gap", "cost_proxy")
MINIMIZE_AXES = {"risk_envelope", "qualification_gap", "cost_proxy"}
TRUST_PENALTY = {"A": 0.0, "B": 0.25, "C": 0.65}
COST_PROXY_WEIGHTS = {
    "correction_window.delta_v_budget_mps": 0.30,
    "correction_window.power_available_w": 0.20,
    "correction_window.specific_impulse_s": 0.15,
    "correction_window.max_duration_years": 0.15,
    "bh_parameters.distance_from_earth_ly": 0.20,
}
BLOCKED_CLAIMS = [
    "global optimum proven",
    "procurement-grade cost estimate",
    "qualification complete",
    "flight-ready design selected",
]
EXTERNAL_EVIDENCE_GAPS = [
    "larger search campaign with solver diversity",
    "calibrated mission utility and cost model",
    "stack-level qualification evidence tied to optimized parameters",
    "external review of candidate dominance assumptions",
]
INTERPRETATION_LIMITS = [
    "Cost proxy is an engineering-resource screen, not a procurement quote.",
    "Qualification gap is a trust/evidence screen, not a hardware qualification result.",
    "Pareto membership is computed over reduced-order deterministic artifacts only.",
    "No global optimum, launch readiness, or physical certification is claimed.",
]


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_artifacts(repo_root: Path, paths: Sequence[str]) -> List[Dict[str, str]]:
    return [{"path": path, "sha256": _sha256_file(repo_root / path)} for path in paths]


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _claim_by_id(parameter_claims: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {
        str(item["parameter_id"]): item
        for item in parameter_claims.get("claims", [])
        if isinstance(item, Mapping) and isinstance(item.get("parameter_id"), str)
    }


def _search_entry_by_id(search_space: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {
        str(item["parameter_id"]): item
        for item in search_space.get("parameters_considered", [])
        if isinstance(item, Mapping) and isinstance(item.get("parameter_id"), str)
    }


def _normalized_position(value: float, low: float, high: float) -> float:
    if not all(math.isfinite(item) for item in (value, low, high)) or high <= low:
        return 0.0
    if low > 0.0 and high / low >= 1_000.0 and value > 0.0:
        low_l = math.log10(low)
        high_l = math.log10(high)
        value_l = math.log10(max(low, min(high, value)))
        return _clamp01((value_l - low_l) / (high_l - low_l))
    return _clamp01((value - low) / (high - low))


def _excursion(entry: Mapping[str, Any], value: float) -> float:
    bounds = entry.get("bounds")
    baseline = entry.get("baseline_value")
    if (
        not isinstance(bounds, list)
        or len(bounds) != 2
        or not _is_number(bounds[0])
        or not _is_number(bounds[1])
        or not _is_number(baseline)
    ):
        return 0.0
    low = float(bounds[0])
    high = float(bounds[1])
    base = float(baseline)
    if high <= low:
        return 0.0
    return abs(_normalized_position(value, low, high) - _normalized_position(base, low, high))


def qualification_gap(
    *,
    candidate_parameters: Mapping[str, Any],
    search_space: Mapping[str, Any],
    parameter_claims: Mapping[str, Any],
) -> Dict[str, Any]:
    claims = _claim_by_id(parameter_claims)
    search_entries = _search_entry_by_id(search_space)
    contributions: List[Dict[str, Any]] = []

    for parameter_id, raw_value in sorted(candidate_parameters.items()):
        entry = search_entries.get(parameter_id)
        claim = claims.get(parameter_id)
        if entry is None or not _is_number(raw_value):
            continue
        trust = str((claim or {}).get("trust_grade", entry.get("trust_grade", "UNKNOWN")))
        penalty = float(TRUST_PENALTY.get(trust, 1.0))
        excursion = _excursion(entry, float(raw_value))
        contribution = penalty * (0.5 + excursion)
        contributions.append(
            {
                "parameter_id": parameter_id,
                "trust_grade": trust,
                "penalty": _round(penalty),
                "excursion": _round(excursion),
                "contribution": _round(contribution),
            }
        )

    denominator = max(1.0, 1.5 * len(contributions))
    score = _clamp01(sum(float(item["contribution"]) for item in contributions) / denominator)
    top = sorted(contributions, key=lambda item: (-float(item["contribution"]), str(item["parameter_id"])))[:5]
    trust_distribution: Dict[str, int] = {}
    for item in contributions:
        trust = str(item["trust_grade"])
        trust_distribution[trust] = trust_distribution.get(trust, 0) + 1

    return {
        "score": _round(score),
        "method": "trust_weighted_search_excursion",
        "trust_penalty": dict(TRUST_PENALTY),
        "trust_distribution": dict(sorted(trust_distribution.items())),
        "top_gap_drivers": top,
    }


def cost_proxy(
    *,
    candidate_parameters: Mapping[str, Any],
    search_space: Mapping[str, Any],
) -> Dict[str, Any]:
    search_entries = _search_entry_by_id(search_space)
    components: List[Dict[str, Any]] = []
    weighted_sum = 0.0
    total_weight = 0.0

    for parameter_id, weight in COST_PROXY_WEIGHTS.items():
        entry = search_entries.get(parameter_id)
        if entry is None:
            continue
        raw_value = candidate_parameters.get(parameter_id, entry.get("baseline_value"))
        if not _is_number(raw_value):
            continue
        bounds = entry.get("bounds")
        if not (
            isinstance(bounds, list)
            and len(bounds) == 2
            and _is_number(bounds[0])
            and _is_number(bounds[1])
        ):
            continue
        position = _normalized_position(float(raw_value), float(bounds[0]), float(bounds[1]))
        if parameter_id == "correction_window.specific_impulse_s":
            position = 1.0 - position
        weighted_sum += weight * position
        total_weight += weight
        components.append(
            {
                "parameter_id": parameter_id,
                "weight": _round(weight),
                "normalized_pressure": _round(position),
                "value": _round(float(raw_value)),
            }
        )

    score = _clamp01(weighted_sum / total_weight) if total_weight else 0.0
    return {
        "score": _round(score),
        "method": "normalized_engineering_resource_pressure",
        "source_boundary": "screening proxy only; not procurement or launch pricing",
        "components": components,
    }


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_scores = left.get("scores", {})
    right_scores = right.get("scores", {})
    if not isinstance(left_scores, Mapping) or not isinstance(right_scores, Mapping):
        return False

    better_or_equal = True
    strictly_better = False
    for axis in AXIS_IDS:
        if axis not in left_scores or axis not in right_scores:
            return False
        lv = float(left_scores[axis])
        rv = float(right_scores[axis])
        if axis in MINIMIZE_AXES:
            if lv > rv + 1e-12:
                better_or_equal = False
                break
            if lv < rv - 1e-12:
                strictly_better = True
        else:
            if lv < rv - 1e-12:
                better_or_equal = False
                break
            if lv > rv + 1e-12:
                strictly_better = True
    return better_or_equal and strictly_better


def pareto_candidate_ids(candidates: Sequence[Mapping[str, Any]]) -> List[str]:
    out: List[str] = []
    for index, candidate in enumerate(candidates):
        dominated = False
        for other_index, other in enumerate(candidates):
            if index == other_index:
                continue
            if _dominates(other, candidate):
                dominated = True
                break
        if not dominated and isinstance(candidate.get("candidate_id"), str):
            out.append(str(candidate["candidate_id"]))
    return out


def axis_contract() -> Dict[str, Any]:
    return {
        "aggregation_policy": "pareto_first_no_hidden_weighted_sum",
        "axes": [
            {
                "id": "p_success",
                "direction": "maximize",
                "status": "computed",
                "source_ref": "artifacts/optimization_frontier_realistic.v1.json",
            },
            {
                "id": "risk_envelope",
                "direction": "minimize",
                "status": "computed",
                "source_ref": "mission/objectives/risk_envelope.v1.json",
            },
            {
                "id": "qualification_gap",
                "direction": "minimize",
                "status": "screening_proxy",
                "source_ref": "parameters/registry/parameter_claims.v1.json",
                "method": "trust_weighted_search_excursion",
            },
            {
                "id": "cost_proxy",
                "direction": "minimize",
                "status": "screening_proxy",
                "source_ref": "artifacts/optimization_search_space.v1.json",
                "method": "normalized_engineering_resource_pressure",
            },
        ],
        "blocked_claims": list(BLOCKED_CLAIMS),
    }
