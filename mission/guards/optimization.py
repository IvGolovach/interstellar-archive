"""Optimization guardrails for mission parameter selection."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping


def validate_plan(plan: Mapping[str, Any], registry: Mapping[str, Any], claims: Mapping[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []

    if plan.get("schema_version") != "optimization_plan.v1":
        errors.append("plan.schema_version must be optimization_plan.v1")
    if plan.get("mode") != "realistic":
        errors.append("optimization mode must be realistic")

    tuned = plan.get("tuned_parameters")
    if not isinstance(tuned, list) or not tuned:
        errors.append("tuned_parameters must be non-empty list")
        tuned = []

    parameter_by_id: Dict[str, Dict[str, Any]] = {}
    for parameter in registry.get("parameters", []):
        if isinstance(parameter, dict) and isinstance(parameter.get("parameter_id"), str):
            parameter_by_id[str(parameter["parameter_id"])] = parameter

    trust_by_id: Dict[str, str] = {}
    for claim in claims.get("claims", []):
        if isinstance(claim, dict) and isinstance(claim.get("parameter_id"), str):
            trust_by_id[str(claim["parameter_id"])] = str(claim.get("trust_grade", ""))

    accepted: List[str] = []
    for pid in tuned:
        if not isinstance(pid, str) or not pid.strip():
            errors.append("tuned_parameters contains invalid parameter_id")
            continue
        parameter = parameter_by_id.get(pid)
        if parameter is None:
            errors.append(f"tuned parameter not found in registry: {pid}")
            continue
        domain = parameter.get("domain")
        if domain != "realistic":
            errors.append(f"tuned parameter must be realistic domain: {pid}")
            continue

        trust = trust_by_id.get(pid)
        if trust == "D":
            errors.append(f"D-grade parameter cannot be tuned: {pid}")
            continue

        if not bool(parameter.get("affects_core_probability")):
            errors.append(f"tuned parameter must affect core probability: {pid}")
            continue

        accepted.append(pid)

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "mode": plan.get("mode"),
        "tuned_parameters": tuned,
        "accepted_parameters": accepted,
        "errors": errors,
    }
