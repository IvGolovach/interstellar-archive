"""Deterministic risk-envelope helpers for realistic optimization artifacts."""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from mission.baseline import compute_probabilities

ALLOWED_DISTRIBUTIONS = {"normal", "lognormal", "uniform", "triangular"}
ALLOWED_REALISTIC_TRUST = {"A", "B", "C"}


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _is_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _set_path(data: Dict[str, Any], dotted_path: str, value: float) -> None:
    cursor: Any = data
    parts = dotted_path.split(".")
    for key in parts[:-1]:
        cursor = cursor[key]
    cursor[parts[-1]] = value


def _u01(*, seed: int, sample_index: int, entry_index: int, stream: int) -> float:
    payload = f"{seed}:{sample_index}:{entry_index}:{stream}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    value = int.from_bytes(digest[:8], "big")
    return (value + 0.5) / 18446744073709551616.0  # 2**64


def _normal_from_u(*, u1: float, u2: float) -> float:
    safe_u1 = min(max(u1, 1e-15), 1.0 - 1e-15)
    return math.sqrt(-2.0 * math.log(safe_u1)) * math.cos(2.0 * math.pi * u2)


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("quantile requires non-empty values")
    if not (0.0 <= float(q) <= 1.0):
        raise ValueError("quantile q must be in [0,1]")
    ordered = sorted(float(item) for item in values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] + (ordered[high] - ordered[low]) * weight


def _sample_uncertain_value(
    *,
    entry: Mapping[str, Any],
    sample_index: int,
    entry_index: int,
    seed: int,
) -> float:
    distribution = str(entry.get("distribution", ""))
    if distribution not in ALLOWED_DISTRIBUTIONS:
        raise ValueError(f"unsupported uncertainty distribution: {distribution!r}")

    parameters = entry.get("parameters")
    bounds = entry.get("bounds")
    if not isinstance(parameters, Mapping):
        raise ValueError("uncertainty entry parameters must be object")
    if not isinstance(bounds, Mapping):
        raise ValueError("uncertainty entry bounds must be object")

    bmin = bounds.get("min")
    bmax = bounds.get("max")
    if not (_is_number(bmin) and _is_number(bmax)):
        raise ValueError("uncertainty bounds.min/max must be finite numbers")
    low = float(bmin)
    high = float(bmax)
    if not low < high:
        raise ValueError("uncertainty bounds must satisfy min < max")

    u1 = _u01(seed=seed, sample_index=sample_index, entry_index=entry_index, stream=0)
    u2 = _u01(seed=seed, sample_index=sample_index, entry_index=entry_index, stream=1)

    value: float
    if distribution == "uniform":
        pmin = float(parameters.get("min", low))
        pmax = float(parameters.get("max", high))
        if not pmin < pmax:
            raise ValueError("uniform distribution parameters require min < max")
        value = pmin + u1 * (pmax - pmin)
    elif distribution == "triangular":
        tmin = float(parameters.get("min", low))
        tmode = float(parameters.get("mode", (low + high) / 2.0))
        tmax = float(parameters.get("max", high))
        if not (tmin < tmax and tmin <= tmode <= tmax):
            raise ValueError("triangular parameters require min < max and min <= mode <= max")
        if tmax == tmin:
            value = tmin
        else:
            cutoff = (tmode - tmin) / (tmax - tmin)
            if u1 <= cutoff:
                value = tmin + math.sqrt(u1 * (tmax - tmin) * (tmode - tmin))
            else:
                value = tmax - math.sqrt((1.0 - u1) * (tmax - tmin) * (tmax - tmode))
    elif distribution == "normal":
        mean = float(parameters.get("mean", 0.0))
        sigma = float(parameters.get("sigma", 0.0))
        if sigma <= 0.0:
            raise ValueError("normal distribution sigma must be > 0")
        value = mean + sigma * _normal_from_u(u1=u1, u2=u2)
    else:  # lognormal
        mu = float(parameters.get("mu", 0.0))
        sigma = float(parameters.get("sigma", 0.0))
        if sigma <= 0.0:
            raise ValueError("lognormal distribution sigma must be > 0")
        value = math.exp(mu + sigma * _normal_from_u(u1=u1, u2=u2))

    return _round(_clamp(float(value), low, high))


def validate_risk_entries_for_mode(
    *,
    scenario: Mapping[str, Any],
    mode: str,
    claims_map: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    if mode not in {"realistic", "speculative"}:
        raise ValueError(f"unsupported risk mode: {mode}")

    uncertainty_model = scenario.get("uncertainty_model")
    if not isinstance(uncertainty_model, list) or not uncertainty_model:
        raise ValueError("scenario.uncertainty_model must be a non-empty list")

    selected: List[Dict[str, Any]] = []
    for raw in uncertainty_model:
        if not isinstance(raw, Mapping):
            raise ValueError("uncertainty_model entries must be objects")
        item = dict(raw)
        parameter_id = item.get("parameter_id")
        if not isinstance(parameter_id, str) or not parameter_id:
            raise ValueError("uncertainty entry parameter_id must be non-empty string")
        entry_mode = str(item.get("mode", ""))
        if mode == "realistic":
            if entry_mode not in {"realistic", "both"}:
                continue
            claim = claims_map.get(parameter_id)
            trust = str(claim.get("trust_grade", "D")) if isinstance(claim, Mapping) else "D"
            if trust not in ALLOWED_REALISTIC_TRUST:
                raise ValueError(
                    f"risk envelope realistic mode cannot use trust={trust!r} parameter {parameter_id}"
                )
        selected.append(item)

    if mode == "realistic" and not selected:
        raise ValueError("risk envelope realistic mode requires at least one uncertainty entry")

    return selected


def risk_envelope_from_scenario(
    *,
    scenario: Mapping[str, Any],
    claims_map: Mapping[str, Mapping[str, Any]],
    mode: str,
    seed: int,
    samples: int,
    quantile: float,
) -> Dict[str, Any]:
    if samples <= 1:
        raise ValueError("risk envelope samples must be > 1")
    if not (0.0 < float(quantile) < 1.0):
        raise ValueError("risk envelope quantile must be in (0,1)")

    uncertainty_entries = validate_risk_entries_for_mode(
        scenario=scenario,
        mode=mode,
        claims_map=claims_map,
    )

    draws: List[float] = []
    for sample_index in range(int(samples)):
        sampled = copy.deepcopy(dict(scenario))
        for entry_index, entry in enumerate(uncertainty_entries):
            parameter_id = str(entry["parameter_id"])
            sampled_value = _sample_uncertain_value(
                entry=entry,
                sample_index=sample_index,
                entry_index=entry_index,
                seed=int(seed),
            )
            _set_path(sampled, parameter_id, sampled_value)
        probabilities = compute_probabilities(sampled, mode=mode)
        draws.append(float(probabilities["p_success"]))

    q_value = _quantile(draws, float(quantile))
    risk = _clamp(1.0 - q_value, 0.0, 1.0)

    return {
        "method": "lower_quantile",
        "quantile": float(quantile),
        "distribution_size": int(samples),
        "q_value": _round(q_value),
        "risk_envelope": _round(risk),
        "p_success_min": _round(min(draws)),
        "p_success_max": _round(max(draws)),
    }


def parse_quantile_from_spec(spec: Mapping[str, Any]) -> float:
    quantile = spec.get("quantile")
    if not _is_number(quantile):
        raise ValueError("risk spec quantile must be numeric")
    q = float(quantile)
    if not (0.0 < q < 1.0):
        raise ValueError("risk spec quantile must be in (0,1)")
    return q


def parse_samples_from_spec(spec: Mapping[str, Any], default: int = 64) -> int:
    samples = spec.get("monte_carlo_samples", default)
    if isinstance(samples, bool) or not isinstance(samples, int):
        raise ValueError("risk spec monte_carlo_samples must be integer")
    if samples <= 1:
        raise ValueError("risk spec monte_carlo_samples must be > 1")
    return int(samples)
