"""Resolve realistic-only optimization search space."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


ALLOWED_TRUST = {"A", "B", "C"}


@dataclass(frozen=True)
class SearchParameter:
    parameter_id: str
    low: float
    high: float
    neutral: float
    trust_grade: str
    dependencies: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_id": self.parameter_id,
            "bounds": [self.low, self.high],
            "realistic_neutral_value": self.neutral,
            "trust_grade": self.trust_grade,
            "dependencies": list(self.dependencies),
        }


@dataclass(frozen=True)
class RejectedParameter:
    parameter_id: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return {"parameter_id": self.parameter_id, "reason": self.reason}


@dataclass(frozen=True)
class ResolveResult:
    mode: str
    parameters: Tuple[SearchParameter, ...]
    rejected: Tuple[RejectedParameter, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "parameter_count": len(self.parameters),
            "parameters": [item.to_dict() for item in self.parameters],
            "rejected": [item.to_dict() for item in self.rejected],
        }


def _get_path(payload: Mapping[str, Any], dotted_path: str) -> float:
    cursor: Any = payload
    for key in dotted_path.split("."):
        if not isinstance(cursor, Mapping) or key not in cursor:
            raise KeyError(dotted_path)
        cursor = cursor[key]
    if isinstance(cursor, bool) or not isinstance(cursor, (int, float)):
        raise TypeError(f"path '{dotted_path}' is not numeric")
    return float(cursor)


def _claims_map(parameter_claims: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for claim in parameter_claims.get("claims", []):
        if isinstance(claim, dict) and isinstance(claim.get("parameter_id"), str):
            out[str(claim["parameter_id"])] = claim
    return out


def _registry_map(parameter_registry: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for parameter in parameter_registry.get("parameters", []):
        if isinstance(parameter, dict) and isinstance(parameter.get("parameter_id"), str):
            out[str(parameter["parameter_id"])] = parameter
    return out


def _normalize_candidate_ids(candidate_ids: Sequence[str] | None, registry_map: Mapping[str, Any]) -> List[str]:
    if candidate_ids:
        return sorted({pid.strip() for pid in candidate_ids if isinstance(pid, str) and pid.strip()})
    return sorted(registry_map.keys())


def _validate_dependencies(
    parameter_id: str,
    parameter: Mapping[str, Any],
    registry_map: Mapping[str, Dict[str, Any]],
) -> Tuple[bool, str]:
    dependencies = parameter.get("dependencies", [])
    if dependencies is None:
        return (True, "")
    if not isinstance(dependencies, list):
        return (False, "dependencies must be list")

    for dep in dependencies:
        if not isinstance(dep, str) or not dep.strip():
            return (False, "dependencies contains invalid id")
        dep_entry = registry_map.get(dep)
        if dep_entry is None:
            return (False, f"dependency '{dep}' is missing in registry")
        if dep_entry.get("domain") != "realistic":
            return (False, f"dependency '{dep}' is not realistic")
    return (True, "")


def resolve_search_space(
    *,
    scenario: Mapping[str, Any],
    parameter_registry: Mapping[str, Any],
    parameter_claims: Mapping[str, Any],
    mode: str,
    candidate_ids: Sequence[str] | None,
) -> ResolveResult:
    if mode != "realistic":
        raise ValueError("optimization search space supports only mode=realistic")

    registry_map = _registry_map(parameter_registry)
    claims_map = _claims_map(parameter_claims)

    accepted: List[SearchParameter] = []
    rejected: List[RejectedParameter] = []

    for parameter_id in _normalize_candidate_ids(candidate_ids, registry_map):
        parameter = registry_map.get(parameter_id)
        if parameter is None:
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason="missing in registry"))
            continue

        if parameter_id.startswith("code_literal."):
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason="code literal is not tunable"))
            continue

        if parameter.get("domain") != "realistic":
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason="domain is not realistic"))
            continue

        if not bool(parameter.get("affects_core_probability", False)):
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason="does not affect core probability"))
            continue

        claim = claims_map.get(parameter_id)
        if claim is None:
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason="missing claim"))
            continue

        trust_grade = str(claim.get("trust_grade", ""))
        if trust_grade not in ALLOWED_TRUST:
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason=f"trust grade {trust_grade} is not allowed"))
            continue

        neutral_value = parameter.get("realistic_neutral_value")
        if isinstance(neutral_value, bool) or not isinstance(neutral_value, (int, float)):
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason="realistic_neutral_value is required"))
            continue

        bounds = parameter.get("bounds")
        if not isinstance(bounds, list) or len(bounds) != 2:
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason="bounds must be [min,max]"))
            continue
        low, high = bounds
        if isinstance(low, bool) or isinstance(high, bool) or not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason="bounds values must be numeric"))
            continue
        low_f = float(low)
        high_f = float(high)
        if low_f >= high_f:
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason="bounds require min < max"))
            continue

        dep_ok, dep_reason = _validate_dependencies(parameter_id, parameter, registry_map)
        if not dep_ok:
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason=dep_reason))
            continue

        try:
            baseline_value = _get_path(scenario, parameter_id)
        except KeyError:
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason="missing in baseline scenario"))
            continue
        except TypeError as exc:
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason=str(exc)))
            continue

        if baseline_value < low_f or baseline_value > high_f:
            rejected.append(RejectedParameter(parameter_id=parameter_id, reason="baseline value outside bounds"))
            continue

        accepted.append(
            SearchParameter(
                parameter_id=parameter_id,
                low=low_f,
                high=high_f,
                neutral=float(neutral_value),
                trust_grade=trust_grade,
                dependencies=tuple(dep for dep in parameter.get("dependencies", []) if isinstance(dep, str)),
            )
        )

    if not accepted:
        raise ValueError("resolved search space is empty")

    accepted = sorted(accepted, key=lambda item: item.parameter_id)
    rejected = sorted(rejected, key=lambda item: (item.parameter_id, item.reason))

    return ResolveResult(mode=mode, parameters=tuple(accepted), rejected=tuple(rejected))


def apply_parameter_values(scenario: Mapping[str, Any], values: Mapping[str, float]) -> Dict[str, Any]:
    """Return deep-ish copy of scenario with dotted-path numeric updates."""

    import copy

    out = copy.deepcopy(dict(scenario))
    for parameter_id, value in values.items():
        cursor: Any = out
        parts = parameter_id.split(".")
        for key in parts[:-1]:
            cursor = cursor[key]
        cursor[parts[-1]] = float(value)
    return out
