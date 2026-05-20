"""Mission DAG v2 module-boundary artifact helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


SCHEMA_VERSION = "mission_dag_v2_boundary.v1"
GENERATOR = "scripts/build_mission_dag_v2_boundary_artifact.py"
PUBLIC_SCOPE = "mission_dag_v2_module_boundary_review_surface"

REQUIRED_BOUNDARY_REQUIREMENTS = [
    "independent backend id",
    "state trace hash",
    "input/output schema version",
    "failure taxonomy mapping",
    "replayable module fixture",
    "cross-backend comparison report",
]

BLOCKED_CLAIMS = [
    "independent physics backend validated",
    "high-fidelity state trace complete",
    "flight-ready module approved",
    "external backend reproduction completed",
]

INTERPRETATION_LIMITS = [
    "Mission DAG v1 modules remain deterministic wrappers over reduced-order baseline calculations.",
    "A PASS boundary row means the interface contract is explicit, not that physics has been independently validated.",
    "State-trace hashes are required by the v2 boundary, but high-fidelity traces remain external evidence gaps.",
    "No module is flight-ready, externally reproduced, or certified by this artifact.",
]

MODULE_EVIDENCE_GAPS = {
    "TrajectoryModule": [
        "independent geodesic or trajectory backend",
        "orbit-determination covariance trace fixture",
    ],
    "EnvironmentModule": [
        "independent plasma/radiation environment backend",
        "source-backed environment state trace over target approach",
    ],
    "ShieldingModule": [
        "transport or hydrocode backend for selected shield stack",
        "module fixture tied to representative dust-size and impact-angle bins",
    ],
    "ThermalModule": [
        "thermal transport backend for selected material stack",
        "module fixture with heat-load and material-response state trace",
    ],
    "ControlWindowModule": [
        "closed-loop guidance/control backend",
        "actuator authority and power-margin state trace fixture",
    ],
    "DataIntegrityModule": [
        "media/ECC recoverability backend",
        "bit-level post-exposure readability trace fixture",
    ],
}


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


def _scenario_nodes_by_module(scenario: Mapping[str, Any]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for node in scenario.get("modules", []):
        if not isinstance(node, Mapping):
            continue
        module_id = node.get("module_id")
        node_id = node.get("node_id")
        if isinstance(module_id, str) and isinstance(node_id, str):
            out.setdefault(module_id, []).append(node_id)
    return {key: sorted(value) for key, value in sorted(out.items())}


def _taxonomy_ids_by_module(failure_taxonomy: Mapping[str, Any]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for mode in failure_taxonomy.get("failure_modes", []):
        if not isinstance(mode, Mapping) or not isinstance(mode.get("id"), str):
            continue
        for module_type in mode.get("applies_to", []):
            if isinstance(module_type, str):
                out.setdefault(module_type, []).append(str(mode["id"]))
    return {key: sorted(value) for key, value in sorted(out.items())}


def build_module_boundaries(
    *,
    module_registry: Mapping[str, Any],
    scenario: Mapping[str, Any],
    failure_taxonomy: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    scenario_nodes = _scenario_nodes_by_module(scenario)
    taxonomy_ids = _taxonomy_ids_by_module(failure_taxonomy)
    rows: List[Dict[str, Any]] = []

    for module in module_registry.get("modules", []):
        if not isinstance(module, Mapping):
            continue
        implemented_by = module.get("implemented_by", {})
        if not isinstance(implemented_by, Mapping):
            implemented_by = {}
        module_id = str(module.get("module_id", ""))
        module_type = str(module.get("module_type", ""))
        rows.append(
            {
                "module_id": module_id,
                "module_type": module_type,
                "module_version": module.get("module_version"),
                "domain": module.get("domain"),
                "entrypoint": implemented_by.get("python_entrypoint"),
                "input_schema_ref": module.get("inputs_schema_ref"),
                "output_schema_ref": module.get("outputs_schema_ref"),
                "scenario_node_ids": scenario_nodes.get(module_id, []),
                "failure_taxonomy_ids": taxonomy_ids.get(module_type, []),
                "current_v1_support": {
                    "wrapper_over_reduced_order_baseline": True,
                    "module_io_schema_declared": bool(module.get("inputs_schema_ref") and module.get("outputs_schema_ref")),
                    "hashchained_module_artifacts": True,
                    "failure_taxonomy_mapping_declared": bool(taxonomy_ids.get(module_type)),
                    "independent_backend_id_declared": False,
                    "high_fidelity_state_trace_available": False,
                    "cross_backend_comparison_available": False,
                },
                "v2_boundary_requirements": list(REQUIRED_BOUNDARY_REQUIREMENTS),
                "open_external_evidence_gaps": MODULE_EVIDENCE_GAPS.get(module_type, ["independent backend", "state trace fixture"]),
                "blocked_claims": list(BLOCKED_CLAIMS),
            }
        )
    return sorted(rows, key=lambda row: str(row["module_id"]))


def rollup(module_boundaries: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    module_count = len(module_boundaries)
    taxonomy_mapped_count = sum(
        1 for row in module_boundaries if isinstance(row.get("failure_taxonomy_ids"), list) and row["failure_taxonomy_ids"]
    )
    return {
        "module_count": module_count,
        "module_io_schema_contract_available": all(
            bool(row.get("input_schema_ref")) and bool(row.get("output_schema_ref")) for row in module_boundaries
        ),
        "hashchain_contract_available": True,
        "failure_taxonomy_mapping_module_count": taxonomy_mapped_count,
        "state_trace_contract_complete": True,
        "independent_backend_complete": False,
        "high_fidelity_state_traces_available": False,
        "cross_backend_comparison_available": False,
        "flight_ready_module_claimed": False,
        "external_reproduction_completed": False,
    }
