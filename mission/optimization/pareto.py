"""Pareto frontier utilities for optimization outputs."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence


def _dominates(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    a_core = float(a.get("core_probability", 0.0))
    b_core = float(b.get("core_probability", 0.0))
    a_trust = float(a.get("trust_weighted_score", 0.0))
    b_trust = float(b.get("trust_weighted_score", 0.0))
    a_risk = float(a.get("risk_metric", 1.0))
    b_risk = float(b.get("risk_metric", 1.0))

    no_worse = (a_core >= b_core) and (a_trust >= b_trust) and (a_risk <= b_risk)
    strictly_better = (a_core > b_core) or (a_trust > b_trust) or (a_risk < b_risk)
    return no_worse and strictly_better


def pareto_frontier(candidates: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    pool = [item for item in candidates if bool(item.get("hard_feasible", False))]

    frontier: List[Dict[str, Any]] = []
    for candidate in pool:
        dominated = False
        for other in pool:
            if other is candidate:
                continue
            if _dominates(other, candidate):
                dominated = True
                break
        if not dominated:
            frontier.append(dict(candidate))

    frontier.sort(
        key=lambda item: (
            -float(item.get("core_probability", 0.0)),
            -float(item.get("trust_weighted_score", 0.0)),
            float(item.get("risk_metric", 1.0)),
            str(item.get("candidate_id", "")),
        )
    )
    return frontier
