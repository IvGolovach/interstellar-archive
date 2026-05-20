"""Contracts and validation helpers for mission DAG v1."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

MODULE_TYPES = (
    "TrajectoryModule",
    "EnvironmentModule",
    "ShieldingModule",
    "ThermalModule",
    "ControlWindowModule",
    "DataIntegrityModule",
)

VALID_MODES = ("realistic", "speculative", "dual")
VALID_MODULE_MODES = ("realistic", "speculative")
VALID_FAILURE_STATUS = ("PASS", "FAIL", "WARN")
VALID_FAILURE_STAGES = ("S0", "S1", "S2", "S3")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(value: str | bytes) -> str:
    payload = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def taxonomy_map(taxonomy_registry: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for entry in taxonomy_registry.get("failure_modes", []):
        if isinstance(entry, Mapping) and isinstance(entry.get("id"), str):
            out[str(entry["id"])] = dict(entry)
    return out


def validate_failure_taxonomy(taxonomy_registry: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []

    if taxonomy_registry.get("taxonomy_version") != "v1":
        errors.append("failure taxonomy taxonomy_version must be v1")

    failure_modes = taxonomy_registry.get("failure_modes")
    if not isinstance(failure_modes, list) or not failure_modes:
        errors.append("failure taxonomy failure_modes must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, entry in enumerate(failure_modes):
        prefix = f"failure_modes[{index}]"
        if not isinstance(entry, Mapping):
            errors.append(f"{prefix} must be an object")
            continue

        failure_id = entry.get("id")
        if not isinstance(failure_id, str) or not failure_id.strip():
            errors.append(f"{prefix}.id must be non-empty string")
        elif failure_id in seen_ids:
            errors.append(f"{prefix}.id duplicated: {failure_id}")
        else:
            seen_ids.add(failure_id)

        stage = entry.get("stage")
        if stage not in VALID_FAILURE_STAGES:
            errors.append(f"{prefix}.stage must be one of {', '.join(VALID_FAILURE_STAGES)}")

        severity = entry.get("severity")
        if severity not in {"low", "medium", "high", "critical"}:
            errors.append(f"{prefix}.severity must be low|medium|high|critical")

        applies_to = entry.get("applies_to")
        if not isinstance(applies_to, list) or not applies_to:
            errors.append(f"{prefix}.applies_to must be a non-empty list")
        else:
            for module_type in applies_to:
                if module_type not in MODULE_TYPES:
                    errors.append(f"{prefix}.applies_to contains invalid module type: {module_type}")

        hint = entry.get("what_evidence_would_reduce_uncertainty")
        if not isinstance(hint, str) or len(hint.strip()) < 8:
            errors.append(f"{prefix}.what_evidence_would_reduce_uncertainty must be descriptive")

    return errors


def validate_module_registry(module_registry: Mapping[str, Any], repo_root: Path | None = None) -> List[str]:
    errors: List[str] = []

    if module_registry.get("registry_version") != "v1":
        errors.append("module registry registry_version must be v1")

    modules = module_registry.get("modules")
    if not isinstance(modules, list) or not modules:
        errors.append("module registry modules must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, module in enumerate(modules):
        prefix = f"modules[{index}]"
        if not isinstance(module, Mapping):
            errors.append(f"{prefix} must be object")
            continue

        module_id = module.get("module_id")
        if not isinstance(module_id, str) or not module_id.strip():
            errors.append(f"{prefix}.module_id must be non-empty string")
            continue
        if module_id in seen_ids:
            errors.append(f"{prefix}.module_id duplicated: {module_id}")
        else:
            seen_ids.add(module_id)

        module_type = module.get("module_type")
        if module_type not in MODULE_TYPES:
            errors.append(f"{prefix}.module_type invalid: {module_type}")

        if module.get("module_version") != "v1":
            errors.append(f"{prefix}.module_version must be v1")

        if module.get("domain") not in {"realistic", "speculative"}:
            errors.append(f"{prefix}.domain must be realistic|speculative")

        for field in ("description", "inputs_schema_ref", "outputs_schema_ref"):
            value = module.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{field} must be non-empty string")

        implemented = module.get("implemented_by")
        if not isinstance(implemented, Mapping):
            errors.append(f"{prefix}.implemented_by must be object")
            continue

        entrypoint = implemented.get("python_entrypoint")
        if not isinstance(entrypoint, str) or ":" not in entrypoint:
            errors.append(f"{prefix}.implemented_by.python_entrypoint must be 'path.py:function'")
            continue

        if repo_root is not None:
            entry_path = entrypoint.split(":", 1)[0]
            if not (repo_root / entry_path).exists():
                errors.append(f"{prefix}.implemented_by.python_entrypoint file missing: {entry_path}")

    return errors


def _topological_order_from_edges(edges: Mapping[str, Sequence[str]]) -> Tuple[List[str], List[str]]:
    indegree: MutableMapping[str, int] = {node: 0 for node in edges}
    reverse: Dict[str, List[str]] = defaultdict(list)

    for node, deps in edges.items():
        for dep in deps:
            indegree[node] += 1
            reverse[dep].append(node)

    queue = deque(sorted(node for node, degree in indegree.items() if degree == 0))
    order: List[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for nxt in sorted(reverse.get(node, [])):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(order) == len(edges):
        return order, []

    cycle_nodes = sorted(node for node, degree in indegree.items() if degree > 0)
    return order, cycle_nodes


def scenario_topological_order(scenario_dag: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    edges: Dict[str, List[str]] = {}
    for module in scenario_dag.get("modules", []):
        if isinstance(module, Mapping) and isinstance(module.get("node_id"), str):
            edges[str(module["node_id"])] = [
                str(dep)
                for dep in module.get("depends_on", [])
                if isinstance(dep, str)
            ]
    return _topological_order_from_edges(edges)


def validate_scenario_dag(
    scenario_dag: Mapping[str, Any],
    module_registry: Mapping[str, Any],
) -> List[str]:
    errors: List[str] = []

    if scenario_dag.get("scenario_version") != "v1":
        errors.append("scenario DAG scenario_version must be v1")

    mode = scenario_dag.get("mode")
    if mode not in VALID_MODES:
        errors.append("scenario DAG mode must be realistic|speculative|dual")

    seed = scenario_dag.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        errors.append("scenario DAG seed must be integer")

    modules = scenario_dag.get("modules")
    if not isinstance(modules, list) or not modules:
        errors.append("scenario DAG modules must be non-empty list")
        return errors

    registry_ids = {
        str(module["module_id"])
        for module in module_registry.get("modules", [])
        if isinstance(module, Mapping) and isinstance(module.get("module_id"), str)
    }

    node_ids: set[str] = set()
    deps_by_node: Dict[str, List[str]] = {}

    for index, node in enumerate(modules):
        prefix = f"modules[{index}]"
        if not isinstance(node, Mapping):
            errors.append(f"{prefix} must be object")
            continue

        node_id = node.get("node_id")
        module_id = node.get("module_id")
        depends_on = node.get("depends_on")

        if not isinstance(node_id, str) or not node_id.strip():
            errors.append(f"{prefix}.node_id must be non-empty string")
            continue
        if node_id in node_ids:
            errors.append(f"{prefix}.node_id duplicated: {node_id}")
        node_ids.add(node_id)

        if not isinstance(module_id, str) or not module_id.strip():
            errors.append(f"{prefix}.module_id must be non-empty string")
        elif module_id not in registry_ids:
            errors.append(f"{prefix}.module_id not in module registry: {module_id}")

        if not isinstance(depends_on, list):
            errors.append(f"{prefix}.depends_on must be list")
            deps_by_node[node_id] = []
            continue

        dep_list: List[str] = []
        for dep in depends_on:
            if not isinstance(dep, str) or not dep.strip():
                errors.append(f"{prefix}.depends_on contains invalid dependency")
                continue
            dep_list.append(dep)
        deps_by_node[node_id] = dep_list

    for node_id, deps in deps_by_node.items():
        for dep in deps:
            if dep == node_id:
                errors.append(f"node '{node_id}' cannot depend on itself")
            if dep not in node_ids:
                errors.append(f"node '{node_id}' depends on missing node '{dep}'")

    if not errors:
        _order, cycle_nodes = _topological_order_from_edges(deps_by_node)
        if cycle_nodes:
            errors.append("scenario DAG contains cycle across nodes: " + ", ".join(cycle_nodes))

    outputs = scenario_dag.get("outputs")
    if not isinstance(outputs, Mapping):
        errors.append("scenario DAG outputs must be object")
    else:
        final_metrics = outputs.get("final_metrics")
        if not isinstance(final_metrics, list) or not final_metrics:
            errors.append("scenario DAG outputs.final_metrics must be non-empty list")

    return errors


def validate_module_output(
    payload: Mapping[str, Any],
    taxonomy_by_id: Mapping[str, Mapping[str, Any]],
) -> List[str]:
    errors: List[str] = []

    for field in (
        "module_id",
        "module_type",
        "module_version",
        "mode",
        "inputs_hash",
        "outputs_hash",
        "event_clock_domain",
        "wall_clock_recorded",
        "outputs",
        "failure",
    ):
        if field not in payload:
            errors.append(f"missing field: {field}")

    module_type = payload.get("module_type")
    if module_type not in MODULE_TYPES:
        errors.append(f"invalid module_type: {module_type}")

    if payload.get("module_version") != "v1":
        errors.append("module_version must be v1")

    if payload.get("mode") not in VALID_MODULE_MODES:
        errors.append("mode must be realistic|speculative")

    if payload.get("event_clock_domain") != "event":
        errors.append("event_clock_domain must be event")

    if not isinstance(payload.get("wall_clock_recorded"), bool):
        errors.append("wall_clock_recorded must be boolean")

    inputs_hash = payload.get("inputs_hash")
    outputs_hash = payload.get("outputs_hash")
    if not isinstance(inputs_hash, str) or len(inputs_hash) != 64:
        errors.append("inputs_hash must be 64-char sha256 hex")
    if not isinstance(outputs_hash, str) or len(outputs_hash) != 64:
        errors.append("outputs_hash must be 64-char sha256 hex")

    outputs = payload.get("outputs")
    if not isinstance(outputs, Mapping):
        errors.append("outputs must be object")
    else:
        expected_hash = sha256_hex(canonical_json(outputs))
        if outputs_hash != expected_hash:
            errors.append("outputs_hash mismatch against canonical outputs payload")

    failure = payload.get("failure")
    if not isinstance(failure, Mapping):
        errors.append("failure must be object")
        return errors

    status = failure.get("status")
    if status not in VALID_FAILURE_STATUS:
        errors.append("failure.status must be PASS|FAIL|WARN")

    failure_mode = failure.get("failure_mode")
    failure_stage = failure.get("failure_stage")
    drivers = failure.get("dominant_driver_parameter_ids")
    notes = failure.get("notes")

    if not isinstance(drivers, list):
        errors.append("failure.dominant_driver_parameter_ids must be list")
    elif status in {"FAIL", "WARN"} and len(drivers) == 0:
        errors.append("failure.dominant_driver_parameter_ids must be non-empty for non-PASS statuses")

    if not isinstance(notes, str):
        errors.append("failure.notes must be string")

    if status == "PASS":
        if failure_mode is not None:
            errors.append("failure_mode must be null when status=PASS")
        if failure_stage is not None:
            errors.append("failure_stage must be null when status=PASS")
        return errors

    if not isinstance(failure_mode, str) or not failure_mode.strip():
        errors.append("failure_mode must be non-empty string when status!=PASS")
        return errors

    if failure_mode not in taxonomy_by_id:
        errors.append(f"unknown failure_mode taxonomy id: {failure_mode}")
        return errors

    taxonomy_entry = taxonomy_by_id[failure_mode]
    expected_stage = taxonomy_entry.get("stage")
    if failure_stage != expected_stage:
        errors.append(
            f"failure_stage mismatch for {failure_mode}: expected {expected_stage}, got {failure_stage}"
        )

    applies_to = taxonomy_entry.get("applies_to", [])
    if module_type not in applies_to:
        errors.append(f"taxonomy {failure_mode} does not apply to module_type {module_type}")

    return errors


def manifest_hash(files_by_path: Mapping[str, str]) -> str:
    return sha256_hex(canonical_json(dict(sorted(files_by_path.items()))))
