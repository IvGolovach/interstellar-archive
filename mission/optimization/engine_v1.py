"""Deterministic realistic-only optimization engine v1."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from mission.baseline import build_output, load_claims_map
from mission.optimization import constraints, scoring
from mission.optimization.search_space import ResolveResult, SearchParameter, apply_parameter_values


@dataclass(frozen=True)
class OptimizationConfig:
    mode: str
    samples: int
    seed: int
    refine_top_k: int
    refine_steps: int


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _round(value: float) -> float:
    return float(f"{value:.12f}")


def _canonical_params(params: Mapping[str, float]) -> str:
    return json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _lhs_samples(parameters: Sequence[SearchParameter], samples: int, seed: int) -> List[Dict[str, float]]:
    if samples <= 0:
        raise ValueError("samples must be > 0")

    values_by_param: Dict[str, List[float]] = {}
    for index, parameter in enumerate(parameters):
        rng = random.Random(seed + (index + 1) * 104_729)
        bins = list(range(samples))
        rng.shuffle(bins)

        values: List[float] = []
        span = parameter.high - parameter.low
        for bin_index in bins:
            fraction = (bin_index + rng.random()) / samples
            value = parameter.low + fraction * span
            values.append(_round(value))
        values_by_param[parameter.parameter_id] = values

    out: List[Dict[str, float]] = []
    for sample_index in range(samples):
        row: Dict[str, float] = {}
        for parameter in parameters:
            row[parameter.parameter_id] = values_by_param[parameter.parameter_id][sample_index]
        out.append(row)
    return out


def _load_claims_map(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    return load_claims_map(repo_root)


def _evaluate_candidate(
    *,
    candidate_id: str,
    phase: str,
    baseline_scenario: Mapping[str, Any],
    param_values: Mapping[str, float],
    claims_map: Mapping[str, Dict[str, Any]],
) -> Dict[str, Any]:
    scenario = apply_parameter_values(baseline_scenario, param_values)
    output = build_output(scenario, mode="realistic", claims_map=claims_map)

    hard_violations = constraints.evaluate_hard_constraints(scenario, output)
    if output.get("speculative_parameters_used"):
        hard_violations.append("speculative_usage_detected")

    soft = constraints.evaluate_soft_constraints(
        baseline_scenario=baseline_scenario,
        scenario=scenario,
        output=output,
    )

    candidate: Dict[str, Any] = {
        "candidate_id": candidate_id,
        "phase": phase,
        "params": dict(sorted({key: _round(float(value)) for key, value in param_values.items()}.items())),
        "core_probability": _round(float(output["core_probability"])),
        "trust_weighted_score": _round(float(output["trust_weighted_score"])),
        "p_success": _round(float(output["p_success"])),
        "p_hit": _round(float(output["p_hit"])),
        "p_survive": _round(float(output["p_survive"])),
        "p_data_intact": _round(float(output["p_data_intact"])),
        "risk_metric": _round(float(soft["risk_metric"])),
        "penalty": _round(float(soft["penalty"])),
        "hard_feasible": len(hard_violations) == 0,
        "hard_violations": sorted(set(hard_violations)),
        "soft_violations": list(soft["soft_violations"]),
        "constraint_components": dict(soft["components"]),
        "speculative_parameters_used": list(output.get("speculative_parameters_used", [])),
    }
    candidate["composite_score"] = scoring.composite_score(candidate)
    return candidate


def _find_parameter(parameters: Sequence[SearchParameter], parameter_id: str) -> SearchParameter:
    for item in parameters:
        if item.parameter_id == parameter_id:
            return item
    raise KeyError(parameter_id)


def _sorted_unique_candidates(candidates: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for candidate in candidates:
        key = _canonical_params(candidate.get("params", {}))
        current = seen.get(key)
        if current is None or scoring.ranking_key(candidate) < scoring.ranking_key(current):
            seen[key] = dict(candidate)

    out = list(seen.values())
    out.sort(key=scoring.ranking_key)
    return out


def _local_refine(
    *,
    baseline_scenario: Mapping[str, Any],
    parameters: Sequence[SearchParameter],
    claims_map: Mapping[str, Dict[str, Any]],
    base_candidates: Sequence[Mapping[str, Any]],
    config: OptimizationConfig,
) -> List[Dict[str, Any]]:
    refined: List[Dict[str, Any]] = []
    target_candidates = list(base_candidates[: max(1, config.refine_top_k)])

    for base_index, base_candidate in enumerate(target_candidates):
        current_params = dict(base_candidate.get("params", {}))
        current = _evaluate_candidate(
            candidate_id=f"refine-{base_index}-seed",
            phase="refine",
            baseline_scenario=baseline_scenario,
            param_values=current_params,
            claims_map=claims_map,
        )
        refined.append(current)

        for step in range(config.refine_steps):
            step_scale = 0.20 / (2**step)
            improved = False

            for parameter_id in sorted(current_params.keys()):
                spec = _find_parameter(parameters, parameter_id)
                span = spec.high - spec.low
                delta = span * step_scale
                if delta <= 0:
                    continue

                for direction in (-1.0, 1.0):
                    candidate_params = dict(current_params)
                    candidate_params[parameter_id] = _round(
                        _clamp(candidate_params[parameter_id] + direction * delta, spec.low, spec.high)
                    )

                    candidate_eval = _evaluate_candidate(
                        candidate_id=f"refine-{base_index}-s{step}-{parameter_id}-{int(direction > 0)}",
                        phase="refine",
                        baseline_scenario=baseline_scenario,
                        param_values=candidate_params,
                        claims_map=claims_map,
                    )
                    refined.append(candidate_eval)

                    if scoring.ranking_key(candidate_eval) < scoring.ranking_key(current):
                        current = candidate_eval
                        current_params = dict(candidate_eval["params"])
                        improved = True

            if not improved:
                break

    return _sorted_unique_candidates(refined)


def run_optimization(
    *,
    repo_root: Path,
    baseline_scenario: Mapping[str, Any],
    search_space: ResolveResult,
    config: OptimizationConfig,
) -> Dict[str, Any]:
    if config.mode != "realistic":
        raise ValueError("optimization engine v1 supports only realistic mode")

    claims_map = _load_claims_map(repo_root)

    parameters = list(search_space.parameters)
    samples = _lhs_samples(parameters=parameters, samples=config.samples, seed=config.seed)

    coarse: List[Dict[str, Any]] = []
    for index, values in enumerate(samples):
        coarse.append(
            _evaluate_candidate(
                candidate_id=f"coarse-{index:05d}",
                phase="coarse",
                baseline_scenario=baseline_scenario,
                param_values=values,
                claims_map=claims_map,
            )
        )

    coarse_ranked = _sorted_unique_candidates(coarse)
    refined_ranked = _local_refine(
        baseline_scenario=baseline_scenario,
        parameters=parameters,
        claims_map=claims_map,
        base_candidates=coarse_ranked,
        config=config,
    )

    all_ranked = _sorted_unique_candidates([*coarse_ranked, *refined_ranked])

    top_k = [dict(item) for item in all_ranked[:10]]
    violations = constraints.summarize_constraint_violations(all_ranked)

    return {
        "config": {
            "engine_version": "optimization-engine-v1",
            "mode": config.mode,
            "samples": config.samples,
            "seed": config.seed,
            "refine_top_k": config.refine_top_k,
            "refine_steps": config.refine_steps,
        },
        "search_space": search_space.to_dict(),
        "sample_results": all_ranked,
        "top_k": top_k,
        "constraint_violations": violations,
    }
