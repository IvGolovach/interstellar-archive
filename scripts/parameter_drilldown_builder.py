"""Domain logic for deterministic parameter drilldown artifact generation."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple

try:
    from .script_io import load_json, write_json
except ImportError:
    from script_io import load_json, write_json


DEFAULT_PARAMETER_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_PARAMETER_CLAIMS = Path("parameters/registry/parameter_claims.v1.json")
DEFAULT_EVIDENCE_SOURCES = Path("parameters/registry/evidence_sources.v1.json")
DEFAULT_UNCERTAINTY_MODEL = Path("mission/UNCERTAINTY_MODEL_v1.json")
DEFAULT_MODULE_REGISTRY = Path("mission/dag/registry/module_registry.v1.json")
DEFAULT_FAILURE_TAXONOMY = Path("mission/dag/registry/failure_taxonomy.v1.json")
DEFAULT_RUNNER_PATH = Path("mission/dag/runner_v1.py")
DEFAULT_STATIC_GRAPH = Path("artifacts/parameter_static_usage_graph.json")
DEFAULT_EVIDENCE_INDEX = Path("artifacts/parameter_evidence_index.json")
DEFAULT_MANIFEST = Path("artifacts/parameter_drilldown_manifest.json")
DEFAULT_P_SUCCESS_DEFENSIBILITY = Path("artifacts/p_success_defensibility.json")
DEFAULT_SENSITIVITY_RESULTS = Path("artifacts/parameter_sensitivity_summary.json")

METRIC_TO_MODULES: Dict[str, Sequence[str]] = {
    "p_hit": ("traj.baseline.v1", "control.baseline.v1"),
    "p_survival": ("shield.baseline.v1", "thermal.baseline.v1", "env.baseline.v1"),
    "p_data_intact": ("data.baseline.v1",),
    "p_success": (
        "traj.baseline.v1",
        "env.baseline.v1",
        "shield.baseline.v1",
        "thermal.baseline.v1",
        "control.baseline.v1",
        "data.baseline.v1",
    ),
}

TRUST_CONFIDENCE = {
    "A": 0.9,
    "B": 0.8,
    "C": 0.65,
    "D": 0.4,
}

INTERNAL_PARAMETER_PREFIXES: Tuple[str, ...] = ("code_literal.",)
PUBLIC_VISIBILITY = "public"
PUBLIC_SURFACE_BROWSER = "browser"
PUBLIC_SCOPE = "public_mission_parameters_only"
UI_SCOPE = "mission_design_environment_only"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_internal_parameter_id(parameter_id: str) -> bool:
    return any(parameter_id.startswith(prefix) for prefix in INTERNAL_PARAMETER_PREFIXES)


def _public_surfaces(parameter: Mapping[str, Any]) -> Set[str]:
    surfaces = parameter.get("public_surfaces")
    if not isinstance(surfaces, list):
        return set()
    return {str(surface) for surface in surfaces if isinstance(surface, str)}


def _has_visibility_metadata(parameter: Mapping[str, Any]) -> bool:
    return "visibility" in parameter or "public_surfaces" in parameter or "audit_scope" in parameter


def _is_public_parameter(parameter: Mapping[str, Any]) -> bool:
    parameter_id = parameter.get("parameter_id")
    if not isinstance(parameter_id, str) or _is_internal_parameter_id(parameter_id):
        return False
    if not _has_visibility_metadata(parameter):
        return True
    return parameter.get("visibility") == PUBLIC_VISIBILITY and PUBLIC_SURFACE_BROWSER in _public_surfaces(parameter)


def _public_parameter_registry(parameter_registry: Mapping[str, Any]) -> Dict[str, Any]:
    parameters = parameter_registry.get("parameters", [])
    if not isinstance(parameters, list):
        return {"parameters": []}
    return {
        **dict(parameter_registry),
        "parameters": [
            dict(parameter)
            for parameter in parameters
            if isinstance(parameter, Mapping) and _is_public_parameter(parameter)
        ],
    }


def _module_driver_map(repo_root: Path, module_registry_path: Path, runner_path: Path) -> Dict[str, Set[str]]:
    module_registry = load_json(repo_root / module_registry_path)
    runner_tree = ast.parse((repo_root / runner_path).read_text(encoding="utf-8"))

    function_drivers: Dict[str, Set[str]] = {}
    for node in runner_tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if not node.name.startswith("run_") or not node.name.endswith("_module"):
            continue

        drivers: Set[str] = set()
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            if not isinstance(child.func, ast.Name) or child.func.id != "_failure":
                continue
            for keyword in child.keywords:
                if keyword.arg != "drivers":
                    continue
                if not isinstance(keyword.value, (ast.List, ast.Tuple)):
                    continue
                for item in keyword.value.elts:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        drivers.add(item.value)
        function_drivers[node.name] = drivers

    parameter_modules: Dict[str, Set[str]] = {}
    for module in module_registry.get("modules", []):
        if not isinstance(module, Mapping):
            continue
        module_id = module.get("module_id")
        entrypoint = module.get("implemented_by", {}).get("python_entrypoint")
        if not isinstance(module_id, str) or not isinstance(entrypoint, str) or ":" not in entrypoint:
            continue
        _, function_name = entrypoint.split(":", 1)
        for parameter_id in function_drivers.get(function_name, set()):
            parameter_modules.setdefault(parameter_id, set()).add(module_id)

    return parameter_modules


def _build_static_usage_graph(
    *,
    parameter_registry: Mapping[str, Any],
    parameter_module_map: Mapping[str, Set[str]],
) -> Dict[str, Dict[str, Any]]:
    graph: Dict[str, Dict[str, Any]] = {}
    for parameter in sorted(parameter_registry.get("parameters", []), key=lambda item: str(item.get("parameter_id", ""))):
        if not isinstance(parameter, Mapping):
            continue
        parameter_id = parameter.get("parameter_id")
        if not isinstance(parameter_id, str):
            continue

        modules: Set[str] = set(parameter_module_map.get(parameter_id, set()))

        used_in = parameter.get("used_in")
        used_in_metrics: List[str] = []
        if isinstance(used_in, list):
            for metric in used_in:
                if isinstance(metric, str) and metric:
                    used_in_metrics.append(metric)
                    modules.update(METRIC_TO_MODULES.get(metric, ()))

        dependencies = parameter.get("dependencies")
        if isinstance(dependencies, list):
            for dep in dependencies:
                if isinstance(dep, str) and dep:
                    modules.add(dep)
                elif isinstance(dep, Mapping):
                    module_id = dep.get("module_id")
                    if isinstance(module_id, str) and module_id:
                        modules.add(module_id)

        graph[parameter_id] = {
            "modules": sorted(modules),
            "paths_to_metrics": sorted({f"success_metrics.{metric}" for metric in used_in_metrics}),
            "affects_core_probability": bool(parameter.get("affects_core_probability", False)),
        }

    return graph


def _normalize_bounds(bounds: Any) -> Dict[str, Any]:
    if isinstance(bounds, list) and len(bounds) == 2:
        low = bounds[0]
        high = bounds[1]
        if isinstance(low, (int, float)) and isinstance(high, (int, float)):
            low_num = float(low)
            high_num = float(high)
            return {
                "minimum": low_num,
                "maximum": high_num,
                "is_fixed": low_num == high_num,
                "has_bounds": True,
            }
    return {
        "minimum": None,
        "maximum": None,
        "is_fixed": False,
        "has_bounds": False,
    }


def _map_uncertainty_model(uncertainty_model: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for item in uncertainty_model.get("uncertainties", []):
        if not isinstance(item, Mapping):
            continue
        parameter_id = item.get("parameter_id")
        if not isinstance(parameter_id, str) or not parameter_id:
            continue
        out[parameter_id] = dict(item)
    return out


def _value_origin_type(classification: Any) -> str:
    mapping = {
        "measured": "measured",
        "assumed": "assumed",
        "design_choice": "assumed",
        "derived": "derived",
        "estimated": "computed",
    }
    return mapping.get(str(classification), "computed")


def _derive_uncertainty(*, parameter: Mapping[str, Any], uncertainty_item: Mapping[str, Any] | None) -> Tuple[str, Dict[str, Any], bool]:
    bounds = parameter.get("bounds")
    if uncertainty_item:
        distribution = uncertainty_item.get("distribution_type")
        params = uncertainty_item.get("distribution_parameters")
        if not isinstance(params, Mapping):
            params = {}
        spec: Dict[str, Any] = {
            "distribution": distribution if isinstance(distribution, str) and distribution else "unspecified",
            "params": dict(params),
        }
        if isinstance(bounds, list) and len(bounds) == 2 and all(isinstance(x, (int, float)) for x in bounds):
            spec["bounds"] = [float(bounds[0]), float(bounds[1])]
        return "distribution", spec, True

    parameter_type = str(parameter.get("type", ""))
    if parameter_type == "distribution":
        spec = {
            "distribution": "unspecified",
            "params": {},
        }
        if isinstance(bounds, list) and len(bounds) == 2 and all(isinstance(x, (int, float)) for x in bounds):
            spec["bounds"] = [float(bounds[0]), float(bounds[1])]
        return "distribution", spec, True

    if isinstance(bounds, list) and len(bounds) == 2 and all(isinstance(x, (int, float)) for x in bounds):
        low = float(bounds[0])
        high = float(bounds[1])
        if low == high:
            return "fixed", {"value": low}, True
        return "interval", {"minimum": low, "maximum": high}, True

    return "model-derived", {"policy": "model-derived", "note": "No explicit bounds in registry."}, False


def _derive_derivation_chain(
    *,
    parameter_id: str,
    parameter: Mapping[str, Any],
    value_origin_type: str,
    modules: Sequence[str],
) -> List[Dict[str, str]]:
    if value_origin_type not in {"derived", "computed"}:
        return []

    refs: List[Dict[str, str]] = []
    code_refs = parameter.get("code_refs")
    if isinstance(code_refs, list):
        for ref in code_refs:
            if isinstance(ref, str) and ref:
                refs.append({"type": "formula", "ref": ref})

    used_in = parameter.get("used_in")
    if isinstance(used_in, list):
        for metric in used_in:
            if isinstance(metric, str) and metric:
                refs.append({"type": "module_output", "ref": f"success_metrics.{metric}"})

    for module_id in modules:
        refs.append({"type": "module_output", "ref": f"module.{module_id}"})

    if not refs:
        refs.append({"type": "module_output", "ref": f"module.derived.{parameter_id}"})

    unique: Dict[Tuple[str, str], Dict[str, str]] = {}
    for item in refs:
        unique[(item["type"], item["ref"])] = item
    return [unique[key] for key in sorted(unique)]


def _build_failure_surface(
    *,
    modules: Sequence[str],
    trust_grade: str,
    module_registry: Mapping[str, Any],
    failure_taxonomy: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    module_type_by_id: Dict[str, str] = {}
    for module in module_registry.get("modules", []):
        if isinstance(module, Mapping):
            module_id = module.get("module_id")
            module_type = module.get("module_type")
            if isinstance(module_id, str) and isinstance(module_type, str):
                module_type_by_id[module_id] = module_type

    module_types = {module_type_by_id.get(module_id) for module_id in modules}
    module_types.discard(None)

    confidence = TRUST_CONFIDENCE.get(trust_grade, 0.4)
    items: List[Dict[str, Any]] = []
    for failure in sorted(failure_taxonomy.get("failure_modes", []), key=lambda entry: str(entry.get("id", ""))):
        if not isinstance(failure, Mapping):
            continue
        failure_id = failure.get("id")
        applies_to = failure.get("applies_to")
        if not isinstance(failure_id, str) or not isinstance(applies_to, list):
            continue
        applies = {item for item in applies_to if isinstance(item, str)}
        if not applies.intersection(module_types):
            continue
        items.append(
            {
                "failure_mode": failure_id,
                "dominant_driver_method": "OAT",
                "confidence": round(confidence, 2),
            }
        )
    return items


def _load_sensitivity_map(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"sensitivity summary is missing: {path}")

    payload = load_json(path)

    summaries = payload.get("summaries")
    if isinstance(summaries, Mapping):
        out: Dict[str, str] = {}
        for parameter_id in sorted(summaries):
            value = summaries.get(parameter_id)
            if isinstance(parameter_id, str) and isinstance(value, str):
                out[parameter_id] = value
        return out

    ranked = payload.get("ranked")
    if not isinstance(ranked, list):
        return {}
    out: Dict[str, str] = {}
    for item in ranked:
        if not isinstance(item, Mapping):
            continue
        parameter_id = item.get("parameter_id")
        influence = item.get("influence_score")
        delta = item.get("raw_delta_p_success")
        if isinstance(parameter_id, str) and isinstance(influence, (int, float)) and isinstance(delta, (int, float)):
            out[parameter_id] = f"OAT influence={float(influence):.6g}, delta_p_success={float(delta):.6g}"
    return out


def _build_evidence_index(
    *,
    parameter_registry: Mapping[str, Any],
    parameter_claims: Mapping[str, Any],
    evidence_sources: Mapping[str, Any],
    uncertainty_model: Mapping[str, Any],
    static_graph: Mapping[str, Mapping[str, Any]],
    module_registry: Mapping[str, Any],
    failure_taxonomy: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    claims_by_id: Dict[str, Dict[str, Any]] = {}
    for claim in parameter_claims.get("claims", []):
        if isinstance(claim, Mapping) and isinstance(claim.get("parameter_id"), str):
            claims_by_id[str(claim["parameter_id"])] = dict(claim)

    sources_by_id: Dict[str, Dict[str, Any]] = {}
    for source in evidence_sources.get("sources", []):
        if isinstance(source, Mapping) and isinstance(source.get("source_id"), str):
            sources_by_id[str(source["source_id"])] = dict(source)

    uncertainty_by_id = _map_uncertainty_model(uncertainty_model)

    index: Dict[str, Dict[str, Any]] = {}
    for parameter in sorted(parameter_registry.get("parameters", []), key=lambda item: str(item.get("parameter_id", ""))):
        if not isinstance(parameter, Mapping):
            continue
        parameter_id = parameter.get("parameter_id")
        if not isinstance(parameter_id, str):
            continue

        claim = claims_by_id.get(parameter_id, {})
        source_ids_raw = claim.get("evidence_source_ids", [])
        source_ids = sorted(str(item) for item in source_ids_raw) if isinstance(source_ids_raw, list) else []
        resolved_sources: List[Dict[str, Any]] = []
        for source_id in source_ids:
            source = sources_by_id.get(source_id)
            if source is None:
                continue
            resolved_sources.append(
                {
                    "source_id": source_id,
                    "type": source.get("type"),
                    "citation": source.get("citation"),
                    "url": source.get("url"),
                    "claim_scope": source.get("claim_scope"),
                    "notes": source.get("notes"),
                }
            )

        static_entry = static_graph.get(parameter_id, {})
        modules = static_entry.get("modules") if isinstance(static_entry.get("modules"), list) else []
        paths_to_metrics = (
            static_entry.get("paths_to_metrics") if isinstance(static_entry.get("paths_to_metrics"), list) else []
        )

        trust_grade = str(claim.get("trust_grade", ""))
        value_origin_type = _value_origin_type(parameter.get("classification"))
        uncertainty_type, uncertainty_spec, has_uncertainty = _derive_uncertainty(
            parameter=parameter,
            uncertainty_item=uncertainty_by_id.get(parameter_id),
        )
        derivation_chain = _derive_derivation_chain(
            parameter_id=parameter_id,
            parameter=parameter,
            value_origin_type=value_origin_type,
            modules=[str(item) for item in modules if isinstance(item, str)],
        )
        failure_surface = _build_failure_surface(
            modules=[str(item) for item in modules if isinstance(item, str)],
            trust_grade=trust_grade,
            module_registry=module_registry,
            failure_taxonomy=failure_taxonomy,
        )

        defensibility_errors: List[str] = []
        if not value_origin_type:
            defensibility_errors.append("missing value_origin_type")
        if not trust_grade:
            defensibility_errors.append("missing trust_grade")
        if not source_ids:
            defensibility_errors.append("missing source_ids")
        if not uncertainty_type:
            defensibility_errors.append("missing uncertainty_type")
        is_stochastic = str(parameter.get("type", "")) == "distribution"
        if bool(parameter.get("affects_core_probability", False)) and is_stochastic and uncertainty_type == "fixed":
            defensibility_errors.append("stochastic core parameter cannot be fixed uncertainty")
        if value_origin_type in {"derived", "computed"} and not derivation_chain:
            defensibility_errors.append("missing derivation_chain for derived/computed value")

        index[parameter_id] = {
            "mode": claim.get("mode"),
            "trust_grade": trust_grade,
            "value_mode": claim.get("value_mode"),
            "units": claim.get("units"),
            "justification": claim.get("justification"),
            "last_reviewed_commit": claim.get("last_reviewed_commit"),
            "domain": parameter.get("domain"),
            "category": parameter.get("category"),
            "classification": parameter.get("classification"),
            "affects_core_probability": bool(parameter.get("affects_core_probability", False)),
            "evidence_source_ids": source_ids,
            "source_ids": source_ids,
            "evidence_sources": resolved_sources,
            "value_origin_type": value_origin_type,
            "uncertainty_type": uncertainty_type,
            "uncertainty_spec": uncertainty_spec,
            "has_uncertainty": has_uncertainty,
            "derivation_chain": derivation_chain,
            "influence_path": sorted(str(item) for item in paths_to_metrics if isinstance(item, str)),
            "failure_surface": failure_surface,
            "defensibility_status": "PASS" if not defensibility_errors else "FAIL",
            "defensibility_errors": defensibility_errors,
        }

    return index


def _build_p_success_defensibility(
    *,
    parameter_registry: Mapping[str, Any],
    evidence_index: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    inputs = ["p_hit", "p_survival", "p_data_intact"]
    input_origins: Dict[str, Dict[str, Any]] = {}

    parameters = [item for item in parameter_registry.get("parameters", []) if isinstance(item, Mapping)]
    for metric in inputs:
        driver_ids: List[str] = []
        source_ids: Set[str] = set()
        origin_types: Set[str] = set()
        deriv_refs: Set[str] = set()

        for parameter in parameters:
            parameter_id = parameter.get("parameter_id")
            used_in = parameter.get("used_in")
            if not isinstance(parameter_id, str) or not isinstance(used_in, list):
                continue
            if metric not in used_in:
                continue
            driver_ids.append(parameter_id)
            evidence_entry = evidence_index.get(parameter_id, {})
            for source_id in evidence_entry.get("source_ids", []):
                if isinstance(source_id, str):
                    source_ids.add(source_id)
            origin_type = evidence_entry.get("value_origin_type")
            if isinstance(origin_type, str) and origin_type:
                origin_types.add(origin_type)
            for chain_item in evidence_entry.get("derivation_chain", []):
                if isinstance(chain_item, Mapping):
                    ref = chain_item.get("ref")
                    if isinstance(ref, str) and ref:
                        deriv_refs.add(ref)

        input_origins[metric] = {
            "origin_type": "computed",
            "driver_parameter_ids": sorted(driver_ids),
            "source_ids": sorted(source_ids),
            "value_origin_types": sorted(origin_types),
            "derivation_chain_refs": sorted(deriv_refs),
        }

    return {
        "schema_version": "p_success_defensibility.v1",
        "formula": "p_hit * p_survival * p_data_intact",
        "inputs": inputs,
        "input_origins": input_origins,
        "uncertainty_propagation": "MonteCarlo",
        "mode_constraints": {
            "realistic": {
                "allow_speculative_parameters": False,
                "allow_trust_grade_D": False,
            },
            "speculative": {
                "allow_speculative_parameters": True,
                "allow_trust_grade_D": True,
            },
        },
    }


def _build_manifest_entries(
    *,
    parameter_registry: Mapping[str, Any],
    static_graph: Mapping[str, Mapping[str, Any]],
    evidence_index: Mapping[str, Mapping[str, Any]],
    sensitivity_map: Mapping[str, str],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    entries: List[Dict[str, Any]] = []
    errors: List[str] = []
    parameters = parameter_registry.get("parameters", [])
    if not isinstance(parameters, list):
        return entries, ["parameter registry must contain list field 'parameters'"]

    for parameter in sorted(parameters, key=lambda item: str(item.get("parameter_id", ""))):
        if not isinstance(parameter, Mapping):
            continue
        parameter_id = parameter.get("parameter_id")
        if not isinstance(parameter_id, str):
            continue

        static_entry = static_graph.get(parameter_id)
        evidence_entry = evidence_index.get(parameter_id)

        status_reasons: List[str] = []
        if static_entry is None:
            status_reasons.append("missing static usage entry")
        if evidence_entry is None:
            status_reasons.append("missing evidence entry")

        modules: List[str] = []
        paths_to_metrics: List[str] = []
        if isinstance(static_entry, Mapping):
            modules_raw = static_entry.get("modules")
            if isinstance(modules_raw, list):
                modules = sorted(str(item) for item in modules_raw)
            paths_raw = static_entry.get("paths_to_metrics")
            if isinstance(paths_raw, list):
                paths_to_metrics = sorted(str(item) for item in paths_raw)

        trust_grade = None
        domain = parameter.get("domain")
        mode = parameter.get("mode")
        units = parameter.get("unit")
        category = parameter.get("category")
        classification = parameter.get("classification")
        value_mode = parameter.get("type")
        evidence_source_ids: List[str] = []
        has_uncertainty = False
        has_source = False
        defensibility_status = "FAIL"
        failure_taxonomy_refs: List[str] = []
        if isinstance(evidence_entry, Mapping):
            trust_grade = evidence_entry.get("trust_grade")
            domain = evidence_entry.get("domain", domain)
            mode = evidence_entry.get("mode", mode)
            units = evidence_entry.get("units", units)
            category = evidence_entry.get("category", category)
            classification = evidence_entry.get("classification", classification)
            value_mode = evidence_entry.get("value_mode", value_mode)
            source_ids_raw = evidence_entry.get("source_ids")
            if isinstance(source_ids_raw, list):
                evidence_source_ids = sorted(str(item) for item in source_ids_raw)
            has_uncertainty = bool(evidence_entry.get("uncertainty_type"))
            has_source = len(evidence_source_ids) > 0
            defensibility_status = str(evidence_entry.get("defensibility_status", "FAIL"))
            failure_surface = evidence_entry.get("failure_surface")
            if isinstance(failure_surface, list):
                failure_taxonomy_refs = sorted(
                    str(item.get("failure_mode"))
                    for item in failure_surface
                    if isinstance(item, Mapping) and isinstance(item.get("failure_mode"), str)
                )

        if not isinstance(units, str) or not units.strip():
            status_reasons.append("units missing")
        if not isinstance(trust_grade, str) or not trust_grade.strip():
            status_reasons.append("trust_grade missing")

        evidence_status = {
            "status": "OK" if not status_reasons else "FAIL",
            "reason": "; ".join(status_reasons) if status_reasons else None,
        }

        entry = {
            "parameter_id": parameter_id,
            "visibility": parameter.get("visibility"),
            "public_surfaces": sorted(_public_surfaces(parameter)),
            "audit_scope": parameter.get("audit_scope"),
            "default_value": parameter.get("default"),
            "bounds": _normalize_bounds(parameter.get("bounds")),
            "units": units,
            "domain": domain,
            "mode": mode,
            "category": category,
            "classification": classification,
            "value_mode": value_mode,
            "trust_grade": trust_grade,
            "affects_core_probability": bool(parameter.get("affects_core_probability", False)),
            "modules_touched_count": len(modules),
            "modules": modules,
            "paths_to_metrics": paths_to_metrics,
            "evidence_source_ids": evidence_source_ids,
            "evidence_status": evidence_status,
            "has_uncertainty": has_uncertainty,
            "has_source": has_source,
            "defensibility_status": defensibility_status,
            "has_dynamic_trace": False,
            "static_usage_ref": f"artifacts/parameter_static_usage_graph.json#{parameter_id}",
            "evidence_ref": f"artifacts/parameter_evidence_index.json#{parameter_id}",
            "sensitivity_summary": sensitivity_map.get(parameter_id),
            "failure_taxonomy_refs": failure_taxonomy_refs,
        }
        entries.append(entry)

        if evidence_status["status"] != "OK":
            errors.append(f"{parameter_id}: {evidence_status['reason']}")
        if defensibility_status != "PASS":
            errors.append(f"{parameter_id}: defensibility_status={defensibility_status}")

    return entries, errors


def build_artifacts(
    *,
    repo_root: Path,
    parameter_registry_path: Path,
    parameter_claims_path: Path,
    evidence_sources_path: Path,
    uncertainty_model_path: Path,
    module_registry_path: Path,
    failure_taxonomy_path: Path,
    runner_path: Path,
    static_graph_path: Path,
    evidence_index_path: Path,
    manifest_path: Path,
    p_success_defensibility_path: Path,
    sensitivity_results_path: Path,
) -> Dict[str, Any]:
    parameter_registry = load_json(repo_root / parameter_registry_path)
    public_parameter_registry = _public_parameter_registry(parameter_registry)
    parameter_claims = load_json(repo_root / parameter_claims_path)
    evidence_sources = load_json(repo_root / evidence_sources_path)
    uncertainty_model = load_json(repo_root / uncertainty_model_path)
    module_registry = load_json(repo_root / module_registry_path)
    failure_taxonomy = load_json(repo_root / failure_taxonomy_path)

    parameter_module_map = _module_driver_map(
        repo_root=repo_root,
        module_registry_path=module_registry_path,
        runner_path=runner_path,
    )
    static_graph = _build_static_usage_graph(
        parameter_registry=public_parameter_registry,
        parameter_module_map=parameter_module_map,
    )
    evidence_index = _build_evidence_index(
        parameter_registry=public_parameter_registry,
        parameter_claims=parameter_claims,
        evidence_sources=evidence_sources,
        uncertainty_model=uncertainty_model,
        static_graph=static_graph,
        module_registry=module_registry,
        failure_taxonomy=failure_taxonomy,
    )
    p_success_defensibility = _build_p_success_defensibility(
        parameter_registry=public_parameter_registry,
        evidence_index=evidence_index,
    )

    static_graph_abs = repo_root / static_graph_path
    evidence_index_abs = repo_root / evidence_index_path
    manifest_abs = repo_root / manifest_path
    p_success_abs = repo_root / p_success_defensibility_path

    write_json(static_graph_abs, static_graph)
    write_json(evidence_index_abs, evidence_index)
    write_json(p_success_abs, p_success_defensibility)

    sensitivity_map = _load_sensitivity_map(repo_root / sensitivity_results_path)
    manifest_entries, integrity_errors = _build_manifest_entries(
        parameter_registry=public_parameter_registry,
        static_graph=static_graph,
        evidence_index=evidence_index,
        sensitivity_map=sensitivity_map,
    )

    parameter_count = len(manifest_entries)
    total_parameter_count = len(parameter_registry.get("parameters", [])) if isinstance(parameter_registry.get("parameters", []), list) else parameter_count
    excluded_internal_parameter_count = max(0, total_parameter_count - parameter_count)
    covered_count = sum(1 for item in manifest_entries if item.get("trust_grade"))
    completeness_ratio = 1.0 if parameter_count == 0 else covered_count / parameter_count

    manifest = {
        "schema_version": "parameter_drilldown_manifest.v1",
        "generator": "scripts/build_parameter_drilldown_artifacts.py",
        "public_scope": PUBLIC_SCOPE,
        "ui_scope": UI_SCOPE,
        "dynamic_trace_semantics": "module_level_attribution",
        "parameter_count": parameter_count,
        "excluded_internal_parameter_count": excluded_internal_parameter_count,
        "internal_parameter_prefixes_excluded": list(INTERNAL_PARAMETER_PREFIXES),
        "global_evidence_completeness_ratio": round(completeness_ratio, 6),
        "parameters": manifest_entries,
        "inputs": [
            {
                "path": str(parameter_registry_path),
                "sha256": _sha256_file(repo_root / parameter_registry_path),
            },
            {
                "path": str(parameter_claims_path),
                "sha256": _sha256_file(repo_root / parameter_claims_path),
            },
            {
                "path": str(evidence_sources_path),
                "sha256": _sha256_file(repo_root / evidence_sources_path),
            },
            {
                "path": str(uncertainty_model_path),
                "sha256": _sha256_file(repo_root / uncertainty_model_path),
            },
            {
                "path": str(module_registry_path),
                "sha256": _sha256_file(repo_root / module_registry_path),
            },
            {
                "path": str(failure_taxonomy_path),
                "sha256": _sha256_file(repo_root / failure_taxonomy_path),
            },
            {
                "path": str(runner_path),
                "sha256": _sha256_file(repo_root / runner_path),
            },
            {
                "path": str(sensitivity_results_path),
                "sha256": _sha256_file(repo_root / sensitivity_results_path),
            },
        ],
        "artifacts": [
            {
                "path": str(static_graph_path),
                "sha256": _sha256_file(static_graph_abs),
            },
            {
                "path": str(evidence_index_path),
                "sha256": _sha256_file(evidence_index_abs),
            },
            {
                "path": str(p_success_defensibility_path),
                "sha256": _sha256_file(p_success_abs),
            },
        ],
    }

    write_json(manifest_abs, manifest)

    return {
        "status": "PASS",
        "parameter_count": parameter_count,
        "excluded_internal_parameter_count": excluded_internal_parameter_count,
        "global_evidence_completeness_ratio": round(completeness_ratio, 6),
        "static_graph_sha256": _sha256_file(static_graph_abs),
        "evidence_index_sha256": _sha256_file(evidence_index_abs),
        "p_success_defensibility_sha256": _sha256_file(p_success_abs),
        "manifest_sha256": _sha256_file(manifest_abs),
        "integrity_errors": integrity_errors,
    }
