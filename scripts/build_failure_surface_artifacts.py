#!/usr/bin/env python3
"""Build deterministic failure-surface baseline artifact for public UI."""

from __future__ import annotations

import argparse
import copy
import re
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_json, write_json
except ImportError:
    from script_io import load_json, render_json, write_json
import sys
from typing import Any, Dict, List, Mapping, Sequence, Tuple

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.dag import contracts
from mission.dag import runner_v1
from mission.baseline import build_output, load_claims_map


DEFAULT_MISSION_SCENARIO = Path("mission/BASELINE_SCENARIO_v1.json")
DEFAULT_DAG_SCENARIO = Path("mission/dag/scenarios/mission_dag_baseline.v1.json")
DEFAULT_MODULE_REGISTRY = Path("mission/dag/registry/module_registry.v1.json")
DEFAULT_FAILURE_TAXONOMY = Path("mission/dag/registry/failure_taxonomy.v1.json")
DEFAULT_SENSITIVITY_SUMMARY = Path("artifacts/parameter_sensitivity_summary.json")
DEFAULT_EVIDENCE_INDEX = Path("artifacts/parameter_evidence_index.json")
DEFAULT_DETERMINISM_STATUS = Path("artifacts/determinism_status.json")
DEFAULT_OUTPUT = Path("artifacts/failure_surface_baseline.v1.json")

STAGE_ORDER = ("S0", "S1", "S2", "S3")
STAGE_NODE_MAP: Dict[str, Sequence[str]] = {
    "S0": ("env",),
    "S1": ("traj", "control"),
    "S2": ("shield", "thermal"),
    "S3": ("data",),
}
ALLOWED_MODES = {"realistic", "speculative"}
INFLUENCE_RE = re.compile(r"influence=([+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", re.IGNORECASE)
FAILURE_MODE_DRIVER_HINTS: Dict[str, Sequence[Tuple[str, str]]] = {
    "DATA_CORRUPTION_RADIATION": (
        (
            "capsule_model.data_media_survival_margin",
            "Stage-specific attribution: reduced-order p_data_intact depends directly on media survivability margin.",
        ),
        (
            "capsule_model.material_degradation_mu_1_per_year",
            "Stage-specific attribution: reduced-order p_data_intact is penalized by the degradation-rate prior over mission horizon.",
        ),
        (
            "environment_model.radiative_flux_w_m2",
            "Stage-specific attribution: radiative loading remains an explicit data-integrity stress term.",
        ),
    ),
}


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _read_commit_sha(determinism_status: Mapping[str, Any]) -> str:
    value = determinism_status.get("last_verified_commit_sha")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unknown"


def _parse_influence(summary: str) -> float:
    match = INFLUENCE_RE.search(summary)
    if not match:
        return 0.0
    try:
        return abs(float(match.group(1)))
    except ValueError:
        return 0.0


def _load_driver_ranking(
    *,
    sensitivity_summary: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> Tuple[List[Dict[str, Any]], float]:
    summaries = sensitivity_summary.get("summaries")
    if not isinstance(summaries, Mapping):
        raise ValueError("artifacts/parameter_sensitivity_summary.json missing object field 'summaries'")

    scored: List[Tuple[float, str, str]] = []
    for parameter_id in sorted(summaries):
        summary = summaries.get(parameter_id)
        if not isinstance(parameter_id, str) or not isinstance(summary, str):
            continue
        influence = _parse_influence(summary)
        scored.append((influence, parameter_id, summary))

    scored.sort(key=lambda item: (-item[0], item[1]))
    top = scored[:3]
    if len(top) < 3:
        raise ValueError("sensitivity summary must provide at least 3 ranked parameters")

    top3: List[Dict[str, Any]] = []
    for influence, parameter_id, summary in top:
        if parameter_id not in evidence_index:
            raise ValueError(f"top driver '{parameter_id}' missing in artifacts/parameter_evidence_index.json")
        top3.append(
            {
                "parameter_id": parameter_id,
                "reason": summary,
                "evidence_ref": f"artifacts/parameter_evidence_index.json#{parameter_id}",
                "influence_score": _round(influence, 12),
            }
        )

    top_influence = top[0][0]
    if top_influence <= 0:
        confidence = 0.5
    else:
        confidence = min(0.99, 0.6 + min(top_influence, 1.0) * 0.35)
    return top3, _round(confidence, 6)


def _failure_mode_driver_ranking(
    *,
    outcome: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> Tuple[List[Dict[str, Any]], float] | None:
    failure_mode = outcome.get("failure_mode")
    if not isinstance(failure_mode, str):
        return None

    hints = FAILURE_MODE_DRIVER_HINTS.get(failure_mode)
    if not hints:
        return None

    top3: List[Dict[str, Any]] = []
    for parameter_id, reason in hints:
        if parameter_id not in evidence_index:
            return None
        top3.append(
            {
                "parameter_id": parameter_id,
                "reason": reason,
                "evidence_ref": f"artifacts/parameter_evidence_index.json#{parameter_id}",
                "influence_score": 0.0,
            }
        )

    return top3, 0.72


def _build_module_events(
    *,
    mission_scenario: Mapping[str, Any],
    mission_output: Mapping[str, Any],
    dag_scenario: Mapping[str, Any],
    module_registry: Mapping[str, Any],
    taxonomy_registry: Mapping[str, Any],
    mode: str,
    seed: int,
) -> List[Dict[str, Any]]:
    module_by_id = {
        str(module["module_id"]): dict(module)
        for module in module_registry.get("modules", [])
        if isinstance(module, Mapping) and isinstance(module.get("module_id"), str)
    }
    taxonomy_by_id = contracts.taxonomy_map(taxonomy_registry)

    order, cycle_nodes = contracts.scenario_topological_order(dag_scenario)
    if cycle_nodes:
        raise ValueError("mission DAG scenario has cycles: " + ", ".join(cycle_nodes))

    nodes_by_id = {
        str(node["node_id"]): dict(node)
        for node in dag_scenario.get("modules", [])
        if isinstance(node, Mapping) and isinstance(node.get("node_id"), str)
    }

    completed: Dict[str, Dict[str, Any]] = {}
    module_events: List[Dict[str, Any]] = []
    for node_id in order:
        node = nodes_by_id[node_id]
        module_id = str(node["module_id"])
        module = module_by_id[module_id]
        module_type = str(module["module_type"])
        dispatcher = runner_v1.MODULE_DISPATCH[module_type]

        upstream_outputs = {dep: completed[dep] for dep in node.get("depends_on", []) if dep in completed}
        ctx = runner_v1.ModuleContext(
            node_id=node_id,
            module_id=module_id,
            module_type=module_type,
            mode=mode,
            seed=seed,
            mission_scenario=mission_scenario,
            mission_output=mission_output,
            upstream_outputs=upstream_outputs,
        )
        outputs, failure = dispatcher(ctx, taxonomy_by_id)

        failure_mode = failure.get("failure_mode")
        failure_stage = failure.get("failure_stage")
        failure_status = str(failure.get("status", "PASS"))
        if failure_status != "PASS":
            if not isinstance(failure_mode, str) or failure_mode not in taxonomy_by_id:
                raise ValueError(f"module '{node_id}' emitted invalid failure_mode={failure_mode!r}")
            if not isinstance(failure_stage, str) or failure_stage not in STAGE_ORDER:
                raise ValueError(f"module '{node_id}' emitted invalid failure_stage={failure_stage!r}")

        event = {
            "node_id": node_id,
            "module_id": module_id,
            "module_type": module_type,
            "failure_status": failure_status,
            "failure_mode": failure_mode if isinstance(failure_mode, str) else "NONE",
            "failure_stage": failure_stage if isinstance(failure_stage, str) else "NONE",
            "dominant_driver_parameter_ids": [
                str(item) for item in failure.get("dominant_driver_parameter_ids", []) if isinstance(item, str)
            ],
            "notes": str(failure.get("notes", "")),
            "outputs_hash": contracts.sha256_hex(contracts.canonical_json(outputs)),
        }
        module_events.append(event)
        completed[node_id] = {
            "module_id": module_id,
            "module_type": module_type,
            "outputs": outputs,
            "failure": failure,
        }

    return module_events


def _event_rank(event: Mapping[str, Any]) -> Tuple[int, str]:
    stage = str(event.get("failure_stage", "NONE"))
    if stage in STAGE_ORDER:
        return (STAGE_ORDER.index(stage), str(event.get("node_id", "")))
    return (len(STAGE_ORDER), str(event.get("node_id", "")))


def _derive_outcome(
    *,
    mission_output: Mapping[str, Any],
    module_events: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    p_success = float(mission_output.get("p_success", 0.0))
    if not (0.0 <= p_success <= 1.0):
        return {
            "outcome_class": "INVALID",
            "p_success": _round(p_success),
            "failure_mode": "NONE",
            "failure_stage": "NONE",
        }

    failed = [item for item in module_events if item.get("failure_status") == "FAIL"]
    warned = [item for item in module_events if item.get("failure_status") == "WARN"]
    if failed:
        primary = sorted(failed, key=_event_rank)[0]
        return {
            "outcome_class": "FAIL",
            "p_success": _round(p_success),
            "failure_mode": str(primary.get("failure_mode", "NONE")),
            "failure_stage": str(primary.get("failure_stage", "NONE")),
        }
    if warned:
        primary = sorted(warned, key=_event_rank)[0]
        return {
            "outcome_class": "UNHEALTHY",
            "p_success": _round(p_success),
            "failure_mode": str(primary.get("failure_mode", "NONE")),
            "failure_stage": str(primary.get("failure_stage", "NONE")),
        }
    if bool(mission_output.get("success", False)):
        return {
            "outcome_class": "SUCCESS",
            "p_success": _round(p_success),
            "failure_mode": "NONE",
            "failure_stage": "NONE",
        }
    p_hit = float(mission_output.get("p_hit", 0.0))
    p_survive = float(mission_output.get("p_survive", 0.0))
    p_data_intact = float(mission_output.get("p_data_intact", 0.0))
    weakest_metric = sorted(
        [
            ("p_hit", p_hit),
            ("p_survive", p_survive),
            ("p_data_intact", p_data_intact),
        ],
        key=lambda item: (item[1], item[0]),
    )[0][0]
    if weakest_metric == "p_hit":
        failure_mode = "MISS_DISTANCE_EXCEEDS_R_INT"
        failure_stage = "S1"
    elif weakest_metric == "p_survive":
        failure_mode = "DUST_PENETRATION_MM_TAIL"
        failure_stage = "S2"
    else:
        failure_mode = "DATA_CORRUPTION_RADIATION"
        failure_stage = "S3"
    return {
        "outcome_class": "FAIL",
        "p_success": _round(p_success),
        "failure_mode": failure_mode,
        "failure_stage": failure_stage,
    }


def _stage_status(stage_events: Sequence[Mapping[str, Any]]) -> Tuple[str, str]:
    if not stage_events:
        return ("N/A", "No module data available for this stage in baseline scenario.")

    failed = [item for item in stage_events if item.get("failure_status") == "FAIL"]
    warned = [item for item in stage_events if item.get("failure_status") == "WARN"]
    if failed:
        summary = ", ".join(
            f"{item['node_id']}:{item['failure_mode']}" for item in sorted(failed, key=lambda value: str(value["node_id"]))
        )
        return ("FAIL", f"Failure observed in stage modules: {summary}.")
    if warned:
        summary = ", ".join(
            f"{item['node_id']}:{item['failure_mode']}" for item in sorted(warned, key=lambda value: str(value["node_id"]))
        )
        return ("FAIL", f"Warning observed in stage modules: {summary}.")
    module_list = ", ".join(str(item["node_id"]) for item in sorted(stage_events, key=lambda value: str(value["node_id"])))
    return ("PASS", f"Stage modules passed: {module_list}.")


def _build_timeline(module_events: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_node = {str(item["node_id"]): item for item in module_events}
    timeline: List[Dict[str, Any]] = []
    for stage in STAGE_ORDER:
        stage_events = [by_node[node_id] for node_id in STAGE_NODE_MAP.get(stage, ()) if node_id in by_node]
        status, summary = _stage_status(stage_events)
        timeline.append(
            {
                "stage": stage,
                "summary": summary,
                "status": status,
            }
        )
    return timeline


def _build_payload(
    *,
    mission_scenario_path: Path,
    mission_scenario: Mapping[str, Any],
    dag_scenario: Mapping[str, Any],
    module_registry: Mapping[str, Any],
    taxonomy_registry: Mapping[str, Any],
    sensitivity_summary: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
    determinism_status: Mapping[str, Any],
    mode: str,
    seed: int,
) -> Dict[str, Any]:
    claims_map = load_claims_map(REPO_ROOT)
    mission_output = build_output(
        copy.deepcopy(dict(mission_scenario)),
        mode=mode,
        claims_map=claims_map,
    )
    module_events = _build_module_events(
        mission_scenario=mission_scenario,
        mission_output=mission_output,
        dag_scenario=dag_scenario,
        module_registry=module_registry,
        taxonomy_registry=taxonomy_registry,
        mode=mode,
        seed=seed,
    )

    outcome = _derive_outcome(mission_output=mission_output, module_events=module_events)
    timeline = _build_timeline(module_events)
    if (
        outcome["outcome_class"] == "FAIL"
        and outcome["failure_stage"] in STAGE_ORDER
        and all(item["status"] == "PASS" for item in timeline)
    ):
        for item in timeline:
            if item["stage"] == outcome["failure_stage"]:
                item["status"] = "FAIL"
                item["summary"] = (
                    "Threshold-derived failure attribution: "
                    f"{outcome['failure_mode']} (success threshold not met)."
                )
                break
    stage_specific = _failure_mode_driver_ranking(
        outcome=outcome,
        evidence_index=evidence_index,
    )
    if stage_specific is None:
        top3, confidence = _load_driver_ranking(
            sensitivity_summary=sensitivity_summary,
            evidence_index=evidence_index,
        )
    else:
        top3, confidence = stage_specific
    top3_public = [
        {
            "parameter_id": item["parameter_id"],
            "reason": item["reason"],
            "evidence_ref": item["evidence_ref"],
        }
        for item in top3
    ]

    signature_basis = {
        "mode": mode,
        "seed": seed,
        "scenario_ref": str(mission_scenario_path),
        "outcome": outcome,
        "timeline": timeline,
        "dominant_drivers": {
            "method": "OAT",
            "confidence": confidence,
            "top3": top3_public,
        },
    }
    determinism_signature = contracts.sha256_hex(contracts.canonical_json(signature_basis))

    payload = {
        "schema_version": "failure_surface.v1",
        "engine": {
            "commit_sha": _read_commit_sha(determinism_status),
            "determinism_signature": determinism_signature,
            "mode": mode,
            "seed": seed,
            "scenario_ref": str(mission_scenario_path),
        },
        "outcome": outcome,
        "timeline": timeline,
        "dominant_drivers": {
            "method": "OAT",
            "confidence": confidence,
            "top3": top3_public,
        },
        "what_changed_vs_baseline": {
            "reference": "baseline_self",
            "p_success_delta": 0.0,
            "failure_mode_changed": False,
            "failure_stage_changed": False,
            "drivers_added": [],
            "drivers_removed": [],
        },
        "module_events": module_events,
    }
    return payload


def build_artifact(
    *,
    repo_root: Path,
    mission_scenario_path: Path,
    dag_scenario_path: Path,
    module_registry_path: Path,
    taxonomy_path: Path,
    sensitivity_summary_path: Path,
    evidence_index_path: Path,
    determinism_status_path: Path,
    output_path: Path,
    mode: str,
    seed: int | None,
) -> Dict[str, Any]:
    if mode not in ALLOWED_MODES:
        raise ValueError(f"unsupported mode: {mode}")

    mission_scenario = load_json(repo_root / mission_scenario_path)
    dag_scenario = load_json(repo_root / dag_scenario_path)
    module_registry = load_json(repo_root / module_registry_path)
    taxonomy_registry = load_json(repo_root / taxonomy_path)
    sensitivity_summary = load_json(repo_root / sensitivity_summary_path)
    evidence_index = load_json(repo_root / evidence_index_path)
    determinism_status = load_json(repo_root / determinism_status_path)

    seed_value = int(seed if seed is not None else dag_scenario.get("seed", 1))

    payload = _build_payload(
        mission_scenario_path=mission_scenario_path,
        mission_scenario=mission_scenario,
        dag_scenario=dag_scenario,
        module_registry=module_registry,
        taxonomy_registry=taxonomy_registry,
        sensitivity_summary=sensitivity_summary,
        evidence_index=evidence_index,
        determinism_status=determinism_status,
        mode=mode,
        seed=seed_value,
    )
    abs_output = repo_root / output_path
    write_json(abs_output, payload)

    digest = contracts.sha256_hex(contracts.canonical_json(payload))
    return {
        "status": "PASS",
        "output": str(output_path),
        "sha256": digest,
        "mode": mode,
        "seed": seed_value,
        "outcome_class": payload["outcome"]["outcome_class"],
        "failure_mode": payload["outcome"]["failure_mode"],
        "failure_stage": payload["outcome"]["failure_stage"],
        "p_success": payload["outcome"]["p_success"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--mission-scenario", default=str(DEFAULT_MISSION_SCENARIO))
    parser.add_argument("--dag-scenario", default=str(DEFAULT_DAG_SCENARIO))
    parser.add_argument("--module-registry", default=str(DEFAULT_MODULE_REGISTRY))
    parser.add_argument("--failure-taxonomy", default=str(DEFAULT_FAILURE_TAXONOMY))
    parser.add_argument("--sensitivity-summary", default=str(DEFAULT_SENSITIVITY_SUMMARY))
    parser.add_argument("--evidence-index", default=str(DEFAULT_EVIDENCE_INDEX))
    parser.add_argument("--determinism-status", default=str(DEFAULT_DETERMINISM_STATUS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), default="realistic")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_artifact(
            repo_root=Path(args.repo_root).resolve(),
            mission_scenario_path=Path(args.mission_scenario),
            dag_scenario_path=Path(args.dag_scenario),
            module_registry_path=Path(args.module_registry),
            taxonomy_path=Path(args.failure_taxonomy),
            sensitivity_summary_path=Path(args.sensitivity_summary),
            evidence_index_path=Path(args.evidence_index),
            determinism_status_path=Path(args.determinism_status),
            output_path=Path(args.output),
            mode=str(args.mode),
            seed=args.seed,
        )
        if args.format == "json":
            print(render_json(result))
        else:
            print("PASS: failure surface baseline artifact")
            print(f"- output: {result['output']}")
            print(f"- sha256: {result['sha256']}")
            print(f"- mode: {result['mode']}")
            print(f"- seed: {result['seed']}")
            print(f"- outcome_class: {result['outcome_class']}")
            print(f"- failure_mode: {result['failure_mode']}")
            print(f"- failure_stage: {result['failure_stage']}")
            print(f"- p_success: {result['p_success']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
