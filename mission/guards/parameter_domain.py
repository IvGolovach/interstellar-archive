"""Parameter domain separation guards for mission contracts."""

from __future__ import annotations

import ast
import copy
import importlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping


DEFAULT_PARAMETER_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_PARAMETER_CLAIMS = Path("parameters/registry/parameter_claims.v1.json")
DEFAULT_SCENARIO = Path("mission/BASELINE_SCENARIO_v1.json")
DEFAULT_MISSION_SCRIPT = Path("scripts/mission_baseline_check.py")
DEFAULT_BASELINE_CORE = Path("mission/baseline/core.py")

SPEC_KEYS = {
    "trajectory_model.non_physical_capture_bias",
    "environment_model.non_physical_safety_multiplier",
}


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _set_path(data: Dict[str, Any], dotted: str, value: float) -> None:
    cursor: Any = data
    parts = dotted.split(".")
    for key in parts[:-1]:
        cursor = cursor[key]
    cursor[parts[-1]] = value


def _safe_ratio(a: float, b: float) -> float:
    denom = b if abs(b) > 1e-12 else 1e-12
    return float(a / denom)


def _validate_domain_metadata(registry: Mapping[str, Any], claims: Mapping[str, Any], errors: List[str]) -> Dict[str, Dict[str, Any]]:
    parameters = registry.get("parameters", [])
    if not isinstance(parameters, list):
        errors.append("parameter registry parameters must be list")
        return {}

    by_id: Dict[str, Dict[str, Any]] = {}
    dependency_by_id: Dict[str, List[str]] = {}
    for idx, parameter in enumerate(parameters):
        prefix = f"parameters[{idx}]"
        if not isinstance(parameter, dict):
            errors.append(f"{prefix} must be object")
            continue
        pid = parameter.get("parameter_id")
        if not isinstance(pid, str) or not pid.strip():
            errors.append(f"{prefix}.parameter_id missing")
            continue
        by_id[pid] = parameter

        domain = parameter.get("domain")
        if domain not in {"realistic", "speculative"}:
            errors.append(f"{prefix}.domain invalid: {domain}")

        if "non_physical_" in pid and domain != "speculative":
            errors.append(f"{prefix}: non_physical parameter must be speculative domain")

        dependencies = parameter.get("dependencies", [])
        if dependencies is None:
            dependencies = []
        if not isinstance(dependencies, list):
            errors.append(f"{prefix}.dependencies must be list")
            dependencies = []
        dependency_by_id[pid] = [dep for dep in dependencies if isinstance(dep, str) and dep.strip()]

    for pid, parameter in by_id.items():
        domain = parameter.get("domain")
        if domain != "realistic":
            continue
        for dep in dependency_by_id.get(pid, []):
            dep_parameter = by_id.get(dep)
            if dep_parameter is None:
                errors.append(f"parameter '{pid}' declares unknown dependency '{dep}'")
                continue
            if dep_parameter.get("domain") == "speculative":
                errors.append(f"parameter '{pid}' (realistic) depends on speculative parameter '{dep}'")

    claim_entries = claims.get("claims", [])
    if not isinstance(claim_entries, list):
        errors.append("parameter claims claims must be list")
        return by_id

    for idx, claim in enumerate(claim_entries):
        prefix = f"claims[{idx}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} must be object")
            continue
        pid = claim.get("parameter_id")
        if not isinstance(pid, str) or pid not in by_id:
            errors.append(f"{prefix}.parameter_id '{pid}' missing from registry")
            continue
        trust = claim.get("trust_grade")
        domain = by_id[pid].get("domain")
        if trust == "D" and domain != "speculative":
            errors.append(f"{prefix}: trust D requires speculative domain")
        if by_id[pid].get("domain") == "speculative" and claim.get("mode") == "realistic":
            errors.append(f"{prefix}: realistic claim mode cannot target speculative domain")
    return by_id


def _resolve_baseline_core_path(repo_root: Path, mission_script_path: Path) -> Path:
    candidate = repo_root / mission_script_path
    if candidate.name == "mission_baseline_check.py":
        return repo_root / DEFAULT_BASELINE_CORE
    return candidate


def _validate_static_core_contract(core_path: Path, errors: List[str]) -> None:
    tree = ast.parse(core_path.read_text(encoding="utf-8"))
    func_nodes = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    if "_resolve_mode_controls" not in func_nodes:
        errors.append("mission baseline core missing _resolve_mode_controls")
    if "_compute_core_probabilities" not in func_nodes:
        errors.append("mission baseline core missing _compute_core_probabilities")
        return

    core_node = func_nodes["_compute_core_probabilities"]
    bad_literals = set()
    for node in ast.walk(core_node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in {"non_physical_capture_bias", "non_physical_safety_multiplier"}:
                bad_literals.add(node.value)

    if bad_literals:
        errors.append(
            "_compute_core_probabilities contains speculative key access: "
            + ", ".join(sorted(bad_literals))
        )


def _load_baseline_core_module(core_path: Path) -> Any:
    module_name = "mission.baseline.core"
    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"cannot load mission baseline core: {core_path}") from exc


def _runtime_guard(
    scenario: Mapping[str, Any],
    parameter_by_id: Mapping[str, Dict[str, Any]],
    baseline_core_path: Path,
    divergence_threshold: float,
    errors: List[str],
) -> Dict[str, Any]:
    mission = _load_baseline_core_module(baseline_core_path)

    baseline = copy.deepcopy(dict(scenario))
    claims_map = mission.load_claims_map(baseline_core_path.parents[2])

    realistic_baseline = mission.build_output(
        baseline,
        mode="realistic",
        claims_map=claims_map,
    )

    mutated = copy.deepcopy(dict(scenario))
    for pid in SPEC_KEYS:
        entry = parameter_by_id.get(pid, {})
        bounds = entry.get("bounds", [None, None])
        neutral = float(
            entry.get(
                "realistic_neutral_value",
                mission.SPECULATIVE_NEUTRAL_VALUES.get(pid, 0.0),
            )
        )
        high = bounds[1] if isinstance(bounds, list) and len(bounds) == 2 else None
        if isinstance(high, (int, float)):
            target = float(high)
        else:
            target = neutral + 1.0
        if abs(target - neutral) < 1e-12:
            target = neutral + 1.0
        _set_path(mutated, pid, target)

    realistic_mutated = mission.build_output(
        mutated,
        mode="realistic",
        claims_map=claims_map,
    )
    for key in ["p_hit", "p_survive", "p_data_intact", "p_success", "core_probability"]:
        if abs(float(realistic_mutated[key]) - float(realistic_baseline[key])) > 1e-12:
            errors.append(f"realistic mode leaked speculative influence for '{key}'")

    if realistic_mutated.get("speculative_parameters_used"):
        errors.append("realistic mode must not report speculative parameters used")

    speculative_baseline = mission.build_output(
        baseline,
        mode="speculative",
        claims_map=claims_map,
    )
    speculative_mutated = mission.build_output(
        mutated,
        mode="speculative",
        claims_map=claims_map,
    )

    speculative_enabled = bool(speculative_mutated.get("speculative_parameters_used"))
    if not speculative_enabled:
        errors.append("speculative mode must report speculative_parameters_used when knobs deviate from neutral")

    changed = abs(float(speculative_mutated["p_success"]) - float(speculative_baseline["p_success"]))
    if changed <= 1e-12:
        errors.append("speculative mode appears ineffective: p_success unchanged after speculative perturbation")

    divergence_multiplier = _safe_ratio(float(speculative_mutated["p_success"]), float(realistic_baseline["p_success"]))
    if divergence_multiplier > divergence_threshold:
        errors.append(
            "speculative divergence exceeds threshold: "
            f"multiplier={divergence_multiplier:.6g} threshold={divergence_threshold:.6g}"
        )

    return {
        "realistic_result": realistic_baseline,
        "speculative_result": speculative_mutated,
        "divergence_multiplier": divergence_multiplier,
        "speculative_mode_enabled": speculative_enabled,
        "realistic_mode_verified": len([e for e in errors if "realistic mode" in e]) == 0,
    }


def run_guard(
    repo_root: Path,
    parameter_registry_path: Path,
    parameter_claims_path: Path,
    scenario_path: Path,
    mission_script_path: Path,
    divergence_threshold: float,
) -> Dict[str, Any]:
    errors: List[str] = []
    baseline_core_path = _resolve_baseline_core_path(repo_root, mission_script_path)

    registry = _load_json(repo_root / parameter_registry_path)
    claims = _load_json(repo_root / parameter_claims_path)
    scenario = _load_json(repo_root / scenario_path)

    parameter_by_id = _validate_domain_metadata(registry, claims, errors)
    _validate_static_core_contract(baseline_core_path, errors)

    runtime = _runtime_guard(
        scenario=scenario,
        parameter_by_id=parameter_by_id,
        baseline_core_path=baseline_core_path,
        divergence_threshold=divergence_threshold,
        errors=errors,
    )

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "divergence_threshold": divergence_threshold,
        "errors": errors,
        "realistic_mode_verified": runtime["realistic_mode_verified"],
        "speculative_mode_enabled": runtime["speculative_mode_enabled"],
        "divergence_multiplier": runtime["divergence_multiplier"],
        "realistic_result": runtime["realistic_result"],
        "speculative_result": runtime["speculative_result"],
    }
