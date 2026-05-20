"""Scoring and ranking helpers for optimization candidates."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple


def composite_score(candidate: Mapping[str, Any]) -> float:
    core = float(candidate.get("core_probability", 0.0))
    trust = float(candidate.get("trust_weighted_score", 0.0))
    penalty = float(candidate.get("penalty", 0.0))
    risk = float(candidate.get("risk_metric", 1.0))
    hard_feasible = bool(candidate.get("hard_feasible", False))

    base = core + 0.35 * trust - 0.50 * risk - penalty
    if not hard_feasible:
        base -= 10.0
    return round(base, 12)


def ranking_key(candidate: Mapping[str, Any]) -> Tuple[float, float, float, float, str]:
    return (
        0.0 if bool(candidate.get("hard_feasible", False)) else 1.0,
        -float(candidate.get("core_probability", 0.0)),
        -float(candidate.get("trust_weighted_score", 0.0)),
        float(candidate.get("risk_metric", 1.0)),
        str(candidate.get("candidate_id", "")),
    )


def ranking_record(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    out = dict(candidate)
    out["composite_score"] = composite_score(candidate)
    return out
