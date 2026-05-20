"""Deterministic mission DAG runner v1."""

from __future__ import annotations

import copy
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Tuple

from mission.baseline import build_output, load_claims_map
from mission.guards.optimization import validate_plan as validate_optimization_plan
from mission.guards.parameter_domain import run_guard as run_parameter_domain_guard
from mission.dag import contracts, hashchain


@dataclass(frozen=True)
class RunnerConfig:
    repo_root: Path
    dag_scenario_path: Path
    mission_scenario_path: Path
    mode: str
    seed: int
    output_dir: Path
    verify_deterministic: bool
    forced_failures: Mapping[str, str] | None = None


@dataclass(frozen=True)
class ModuleContext:
    node_id: str
    module_id: str
    module_type: str
    mode: str
    seed: int
    mission_scenario: Mapping[str, Any]
    mission_output: Mapping[str, Any]
    upstream_outputs: Mapping[str, Mapping[str, Any]]


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _failure(
    *,
    taxonomy_by_id: Mapping[str, Mapping[str, Any]],
    status: str,
    failure_mode: str | None,
    drivers: Sequence[str],
    notes: str,
) -> Dict[str, Any]:
    if status == "PASS":
        return {
            "status": "PASS",
            "failure_mode": None,
            "failure_stage": None,
            "dominant_driver_parameter_ids": list(drivers),
            "notes": notes,
        }

    if failure_mode is None:
        raise ValueError("non-pass failure must provide failure_mode")
    if failure_mode not in taxonomy_by_id:
        raise ValueError(f"unknown failure_mode: {failure_mode}")

    entry = taxonomy_by_id[failure_mode]
    return {
        "status": status,
        "failure_mode": failure_mode,
        "failure_stage": entry["stage"],
        "dominant_driver_parameter_ids": list(drivers),
        "notes": notes,
    }


def _apply_forced_failure(
    *,
    node_id: str,
    module_type: str,
    base_failure: Mapping[str, Any],
    forced_failures: Mapping[str, str],
    taxonomy_by_id: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    forced = forced_failures.get(node_id)
    if not forced:
        return dict(base_failure)

    if forced not in taxonomy_by_id:
        raise ValueError(f"forced failure for node '{node_id}' references unknown taxonomy id: {forced}")

    taxonomy_entry = taxonomy_by_id[forced]
    applies_to = taxonomy_entry.get("applies_to", [])
    if module_type not in applies_to:
        raise ValueError(
            f"forced failure '{forced}' does not apply to module_type '{module_type}'"
        )

    return {
        "status": "FAIL",
        "failure_mode": forced,
        "failure_stage": taxonomy_entry["stage"],
        "dominant_driver_parameter_ids": list(base_failure.get("dominant_driver_parameter_ids", []))
        or ["forced_failure"],
        "notes": f"Forced failure injection for test coverage: {forced}",
    }


def _module_input_hash(
    *,
    node_id: str,
    module_id: str,
    module_type: str,
    mode: str,
    seed: int,
    upstream_outputs: Mapping[str, Mapping[str, Any]],
    mission_output: Mapping[str, Any],
    mission_scenario: Mapping[str, Any],
) -> str:
    upstream_hashes = {
        name: output.get("outputs_hash")
        for name, output in sorted(upstream_outputs.items())
    }
    payload = {
        "node_id": node_id,
        "module_id": module_id,
        "module_type": module_type,
        "mode": mode,
        "seed": seed,
        "upstream_output_hashes": upstream_hashes,
        "mission_output_signature": mission_output.get("deterministic_signature"),
        "mission_schema_version": mission_output.get("mission_schema_version"),
        "mission_engine_version": mission_output.get("mission_engine_version"),
        "mission_scenario_signature": contracts.sha256_hex(contracts.canonical_json(mission_scenario)),
    }
    return contracts.sha256_hex(contracts.canonical_json(payload))


def _build_module_envelope(
    *,
    node_id: str,
    module: Mapping[str, Any],
    mode: str,
    seed: int,
    mission_output: Mapping[str, Any],
    mission_scenario: Mapping[str, Any],
    upstream_outputs: Mapping[str, Mapping[str, Any]],
    outputs: Mapping[str, Any],
    failure: Mapping[str, Any],
) -> Dict[str, Any]:
    outputs_hash = contracts.sha256_hex(contracts.canonical_json(outputs))
    inputs_hash = _module_input_hash(
        node_id=node_id,
        module_id=str(module["module_id"]),
        module_type=str(module["module_type"]),
        mode=mode,
        seed=seed,
        upstream_outputs=upstream_outputs,
        mission_output=mission_output,
        mission_scenario=mission_scenario,
    )
    return {
        "module_id": module["module_id"],
        "module_type": module["module_type"],
        "module_version": "v1",
        "mode": mode,
        "inputs_hash": inputs_hash,
        "outputs_hash": outputs_hash,
        "event_clock_domain": "event",
        "wall_clock_recorded": True,
        "outputs": dict(outputs),
        "failure": dict(failure),
    }


def run_trajectory_module(ctx: ModuleContext, taxonomy_by_id: Mapping[str, Mapping[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    bh = ctx.mission_scenario["bh_parameters"]
    traj = ctx.mission_scenario["trajectory_model"]
    correction = ctx.mission_scenario["correction_window"]

    r_s = float(ctx.mission_output["schwarzschild_radius_m"])
    periapsis = float(bh["periapsis_distance_m"])
    miss_distance = max(0.0, periapsis - r_s)
    sigma_eff = (
        float(traj["nav_position_sigma_m"]) ** 2
        + (periapsis * float(correction["guidance_sigma_rad"])) ** 2
        + (periapsis * float(correction["execution_sigma_fraction"]) * 1e-3) ** 2
    ) ** 0.5

    outputs = {
        "crossing_condition_met": bool(ctx.mission_output["crossing_condition_met"]),
        "schwarzschild_radius_m": _round(r_s),
        "periapsis_distance_m": _round(periapsis),
        "miss_distance_m": _round(miss_distance),
        "effective_sigma_m": _round(sigma_eff),
        "p_hit": _round(float(ctx.mission_output["p_hit"])),
    }

    if not outputs["crossing_condition_met"]:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="FAIL",
            failure_mode="MISS_DISTANCE_EXCEEDS_R_INT",
            drivers=["bh_parameters.periapsis_distance_m", "bh_parameters.mass_kg"],
            notes="Periapsis remains outside Schwarzschild radius in baseline wrapper.",
        )
    elif sigma_eff > float(traj["initial_state_sigma_m"]) * 2.0:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="WARN",
            failure_mode="OD_UNCERTAINTY_COLLAPSE",
            drivers=["trajectory_model.nav_position_sigma_m", "correction_window.guidance_sigma_rad"],
            notes="Navigation uncertainty envelope is close to control leverage boundary.",
        )
    else:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="PASS",
            failure_mode=None,
            drivers=[],
            notes="Trajectory wrapper remained inside baseline uncertainty envelope.",
        )

    return outputs, failure


def run_environment_module(ctx: ModuleContext, taxonomy_by_id: Mapping[str, Mapping[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    bh = ctx.mission_scenario["bh_parameters"]
    env = ctx.mission_scenario["environment_model"]

    flux_ratio = float(env["radiative_flux_w_m2"]) / float(bh["max_radiative_flux_w_m2"])
    plasma_ratio = float(env["plasma_density_proxy_m3"]) / float(bh["max_plasma_density_proxy_m3"])
    dust_ratio = float(env["dust_flux_scale"]) / float(bh["max_dust_flux_scale"])

    outputs = {
        "environment_acceptable": bool(ctx.mission_output["environment_acceptable"]),
        "radiative_flux_ratio": _round(flux_ratio),
        "plasma_density_ratio": _round(plasma_ratio),
        "dust_flux_ratio": _round(dust_ratio),
        "hazard_ratio_max": _round(max(flux_ratio, plasma_ratio, dust_ratio)),
    }

    if not outputs["environment_acceptable"]:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="FAIL",
            failure_mode="PLASMA_ENVIRONMENT_DISQUALIFIED",
            drivers=["environment_model.plasma_density_proxy_m3", "bh_parameters.max_plasma_density_proxy_m3"],
            notes="Environment proxy gate rejected baseline envelope.",
        )
    else:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="PASS",
            failure_mode=None,
            drivers=[],
            notes="Environment proxy remained under configured admissibility thresholds.",
        )

    return outputs, failure


def run_shielding_module(ctx: ModuleContext, taxonomy_by_id: Mapping[str, Mapping[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    capsule = ctx.mission_scenario["capsule_model"]
    env = ctx.mission_scenario["environment_model"]
    bh = ctx.mission_scenario["bh_parameters"]

    dust_ratio = float(env["dust_flux_scale"]) / float(bh["max_dust_flux_scale"])
    shield_density = float(capsule["shield_areal_density_kg_m2"])
    shield_margin = shield_density / (1.0 + dust_ratio)

    outputs = {
        "shield_areal_density_kg_m2": _round(shield_density),
        "dust_flux_ratio": _round(dust_ratio),
        "shield_margin_proxy": _round(shield_margin),
        "p_survive": _round(float(ctx.mission_output["p_survive"])),
    }

    if dust_ratio > 1.2:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="FAIL",
            failure_mode="DUST_PENETRATION_MM_TAIL",
            drivers=["environment_model.dust_flux_scale", "capsule_model.shield_areal_density_kg_m2"],
            notes="Dust-tail proxy exceeds nominal shielded envelope.",
        )
    elif dust_ratio > 0.9:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="WARN",
            failure_mode="DUST_PENETRATION_MM_TAIL",
            drivers=["environment_model.dust_flux_scale", "capsule_model.shield_areal_density_kg_m2"],
            notes="Dust-tail proxy close to shielding boundary.",
        )
    else:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="PASS",
            failure_mode=None,
            drivers=[],
            notes="Shielding proxy remained within configured baseline envelope.",
        )

    return outputs, failure


def run_thermal_module(ctx: ModuleContext, taxonomy_by_id: Mapping[str, Mapping[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    bh = ctx.mission_scenario["bh_parameters"]
    env = ctx.mission_scenario["environment_model"]

    flux = float(env["radiative_flux_w_m2"])
    max_flux = float(bh["max_radiative_flux_w_m2"])
    flux_ratio = flux / max_flux
    margin = max_flux - flux

    outputs = {
        "radiative_flux_w_m2": _round(flux),
        "max_radiative_flux_w_m2": _round(max_flux),
        "thermal_flux_ratio": _round(flux_ratio),
        "thermal_margin_w_m2": _round(margin),
        "p_survive": _round(float(ctx.mission_output["p_survive"])),
    }

    if flux_ratio > 1.0:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="FAIL",
            failure_mode="TPS_FAIL_DELAMINATION",
            drivers=["environment_model.radiative_flux_w_m2", "bh_parameters.max_radiative_flux_w_m2"],
            notes="Thermal flux proxy exceeded configured TPS envelope.",
        )
    else:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="PASS",
            failure_mode=None,
            drivers=[],
            notes="Thermal proxy remained below configured limit.",
        )

    return outputs, failure


def run_control_window_module(ctx: ModuleContext, taxonomy_by_id: Mapping[str, Mapping[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    correction = ctx.mission_scenario["correction_window"]

    start = float(correction["start_year"])
    end = float(correction["end_year"])
    duration = end - start
    max_duration = float(correction["max_duration_years"])
    guidance_sigma = float(correction["guidance_sigma_rad"])
    delta_v = float(correction["delta_v_budget_mps"])

    authority_margin = delta_v / max(1e-6, guidance_sigma * 1e6)
    outputs = {
        "enabled": bool(correction["enabled"]),
        "duration_years": _round(duration, 6),
        "max_duration_years": _round(max_duration, 6),
        "delta_v_budget_mps": _round(delta_v, 6),
        "guidance_sigma_rad": _round(guidance_sigma, 12),
        "control_authority_margin": _round(authority_margin),
    }

    if duration > max_duration or authority_margin < 1.0:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="FAIL",
            failure_mode="CONTROL_AUTHORITY_COLLAPSE",
            drivers=["correction_window.delta_v_budget_mps", "correction_window.guidance_sigma_rad"],
            notes="Correction window cannot guarantee enough control authority in current envelope.",
        )
    elif guidance_sigma > 1.0e-4:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="WARN",
            failure_mode="OD_UNCERTAINTY_COLLAPSE",
            drivers=["correction_window.guidance_sigma_rad", "trajectory_model.nav_position_sigma_m"],
            notes="Guidance uncertainty is high relative to control-window leverage.",
        )
    else:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="PASS",
            failure_mode=None,
            drivers=[],
            notes="Control-window proxy remains within configured bounds.",
        )

    return outputs, failure


def run_data_integrity_module(ctx: ModuleContext, taxonomy_by_id: Mapping[str, Mapping[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    capsule = ctx.mission_scenario["capsule_model"]

    data_intact = float(ctx.mission_output["p_data_intact"])
    media_margin = float(capsule["data_media_survival_margin"])
    degradation_mu = float(capsule["material_degradation_mu_1_per_year"])

    outputs = {
        "p_data_intact": _round(data_intact),
        "data_media_survival_margin": _round(media_margin),
        "material_degradation_mu_1_per_year": _round(degradation_mu),
        "integrity_margin_proxy": _round(data_intact - 0.5),
    }

    if data_intact < 0.5:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="FAIL",
            failure_mode="DATA_CORRUPTION_RADIATION",
            drivers=[
                "capsule_model.data_media_survival_margin",
                "capsule_model.material_degradation_mu_1_per_year",
                "environment_model.radiative_flux_w_m2",
            ],
            notes="Data integrity probability fell below v1 safety threshold.",
        )
    else:
        failure = _failure(
            taxonomy_by_id=taxonomy_by_id,
            status="PASS",
            failure_mode=None,
            drivers=[],
            notes="Data integrity proxy remained above v1 threshold.",
        )

    return outputs, failure


MODULE_DISPATCH = {
    "TrajectoryModule": run_trajectory_module,
    "EnvironmentModule": run_environment_module,
    "ShieldingModule": run_shielding_module,
    "ThermalModule": run_thermal_module,
    "ControlWindowModule": run_control_window_module,
    "DataIntegrityModule": run_data_integrity_module,
}


def _load_claims_map(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    return load_claims_map(repo_root)


def _resolve_execution_modes(requested_mode: str, scenario_mode: str) -> List[str]:
    effective = requested_mode or scenario_mode
    if effective not in contracts.VALID_MODES:
        raise ValueError(f"invalid DAG mode: {effective}")
    if effective == "dual":
        return ["realistic", "speculative"]
    return [effective]


def _run_domain_guard(repo_root: Path, mission_scenario_path: Path) -> Dict[str, Any]:
    return run_parameter_domain_guard(
        repo_root=repo_root,
        parameter_registry_path=Path("parameters/registry/parameter_registry.v1.json"),
        parameter_claims_path=Path("parameters/registry/parameter_claims.v1.json"),
        scenario_path=mission_scenario_path,
        mission_script_path=Path("scripts/mission_baseline_check.py"),
        divergence_threshold=20.0,
    )


def _run_optimization_guard(repo_root: Path) -> Dict[str, Any]:
    plan = json.loads((repo_root / "mission/OPTIMIZATION_PLAN_v1.json").read_text(encoding="utf-8"))
    registry = json.loads((repo_root / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))
    claims = json.loads((repo_root / "parameters/registry/parameter_claims.v1.json").read_text(encoding="utf-8"))
    return validate_optimization_plan(plan, registry, claims)


def _metric_from_output(metric: str, mission_output: Mapping[str, Any]) -> float:
    if metric == "p_survival":
        return float(mission_output["p_survive"])
    return float(mission_output[metric])


def _run_once(
    *,
    repo_root: Path,
    dag_scenario: Mapping[str, Any],
    dag_registry: Mapping[str, Any],
    taxonomy_registry: Mapping[str, Any],
    mission_scenario: Mapping[str, Any],
    mode: str,
    seed: int,
    output_dir: Path,
    forced_failures: Mapping[str, str],
) -> Dict[str, Any]:
    module_by_id = {
        str(module["module_id"]): dict(module)
        for module in dag_registry.get("modules", [])
        if isinstance(module, Mapping) and isinstance(module.get("module_id"), str)
    }
    taxonomy_by_id = contracts.taxonomy_map(taxonomy_registry)

    order, cycle_nodes = contracts.scenario_topological_order(dag_scenario)
    if cycle_nodes:
        raise ValueError("scenario DAG contains cycle: " + ", ".join(cycle_nodes))

    nodes_by_id = {
        str(node["node_id"]): dict(node)
        for node in dag_scenario.get("modules", [])
        if isinstance(node, Mapping)
    }

    claims_map = _load_claims_map(repo_root)
    execution_modes = _resolve_execution_modes(mode, str(dag_scenario["mode"]))

    module_paths: List[Path] = []
    chain_entries: List[Dict[str, Any]] = []
    all_module_payloads: List[Dict[str, Any]] = []
    mode_summaries: Dict[str, Dict[str, Any]] = {}

    for run_mode in execution_modes:
        mission_output = build_output(
            copy.deepcopy(dict(mission_scenario)),
            mode=run_mode,
            claims_map=claims_map,
        )

        mode_dir = output_dir / "modules" / run_mode
        mode_dir.mkdir(parents=True, exist_ok=True)

        completed: Dict[str, Dict[str, Any]] = {}

        for node_id in order:
            node = nodes_by_id[node_id]
            module = module_by_id[str(node["module_id"])]
            module_type = str(module["module_type"])
            dispatcher = MODULE_DISPATCH[module_type]

            upstream_outputs = {
                dep: completed[dep]
                for dep in node.get("depends_on", [])
            }

            ctx = ModuleContext(
                node_id=node_id,
                module_id=str(module["module_id"]),
                module_type=module_type,
                mode=run_mode,
                seed=seed,
                mission_scenario=mission_scenario,
                mission_output=mission_output,
                upstream_outputs=upstream_outputs,
            )

            outputs, failure = dispatcher(ctx, taxonomy_by_id)
            failure = _apply_forced_failure(
                node_id=node_id,
                module_type=module_type,
                base_failure=failure,
                forced_failures=forced_failures,
                taxonomy_by_id=taxonomy_by_id,
            )

            envelope = _build_module_envelope(
                node_id=node_id,
                module=module,
                mode=run_mode,
                seed=seed,
                mission_output=mission_output,
                mission_scenario=mission_scenario,
                upstream_outputs=upstream_outputs,
                outputs=outputs,
                failure=failure,
            )

            validation_errors = contracts.validate_module_output(envelope, taxonomy_by_id)
            if validation_errors:
                raise ValueError(
                    f"module contract validation failed for node '{node_id}': "
                    + "; ".join(validation_errors)
                )

            artifact_path = mode_dir / f"{node_id}.json"
            _write_json(artifact_path, envelope)
            module_paths.append(artifact_path)
            all_module_payloads.append(envelope)

            artifact_rel = str(artifact_path.relative_to(output_dir))
            artifact_hash = hashchain.file_sha256(artifact_path)
            chain_entries.append(
                hashchain.append_entry(
                    chain_entries,
                    mode=run_mode,
                    node_id=node_id,
                    module_id=str(module["module_id"]),
                    artifact_path=artifact_rel,
                    artifact_hash=artifact_hash,
                )
            )

            completed[node_id] = envelope

        final_metrics = {}
        for metric in dag_scenario["outputs"]["final_metrics"]:
            final_metrics[metric] = _round(_metric_from_output(str(metric), mission_output))

        mode_summaries[run_mode] = {
            "mode": run_mode,
            "final_metrics": final_metrics,
            "core_probability": _round(float(mission_output["core_probability"])),
            "trust_weighted_score": _round(float(mission_output["trust_weighted_score"])),
            "speculative_parameters_used": list(mission_output.get("speculative_parameters_used", [])),
            "deterministic_signature": str(mission_output.get("deterministic_signature", "")),
        }

    hashchain_path = output_dir / "hashchain.jsonl"
    hashchain.write_jsonl(hashchain_path, chain_entries)

    manifest_paths = [*module_paths, hashchain_path]
    files = hashchain.build_manifest(manifest_paths, output_dir)
    manifest_payload = {
        "files": files,
        "manifest_hash": contracts.manifest_hash(files),
        "module_artifact_count": len(module_paths),
        "hashchain_entries": len(chain_entries),
    }
    manifest_path = output_dir / "manifest.json"
    _write_json(manifest_path, manifest_payload)

    chain_valid, chain_message = hashchain.verify_chain(chain_entries)

    rehash_errors: List[str] = []
    for entry in chain_entries:
        artifact_rel = str(entry["artifact_path"])
        artifact_path = output_dir / artifact_rel
        expected = str(entry["artifact_hash"])
        actual = hashchain.file_sha256(artifact_path)
        if actual != expected:
            rehash_errors.append(f"artifact hash mismatch for {artifact_rel}")

    hashchain_proof = {
        "status": "PASS" if chain_valid and not rehash_errors else "FAIL",
        "chain_valid": chain_valid,
        "chain_message": chain_message,
        "rehash_errors": rehash_errors,
        "root_hash": chain_entries[-1]["chain_hash"] if chain_entries else "0" * 64,
        "entry_count": len(chain_entries),
    }

    used_failure_ids = sorted(
        {
            str(item["failure"]["failure_mode"])
            for item in all_module_payloads
            if item["failure"]["status"] != "PASS"
        }
    )
    unknown_failure_ids = sorted(fid for fid in used_failure_ids if fid not in taxonomy_by_id)

    failure_coverage = {
        "status": "PASS" if not unknown_failure_ids else "FAIL",
        "used_failure_ids": used_failure_ids,
        "unknown_failure_ids": unknown_failure_ids,
        "total_taxonomy_ids": len(taxonomy_by_id),
        "used_count": len(used_failure_ids),
    }

    overall_status = "PASS"
    if hashchain_proof["status"] != "PASS" or failure_coverage["status"] != "PASS":
        overall_status = "FAIL"

    return {
        "status": overall_status,
        "mode": mode,
        "execution_modes": execution_modes,
        "seed": seed,
        "mode_summaries": mode_summaries,
        "manifest": manifest_payload,
        "hashchain_proof": hashchain_proof,
        "failure_taxonomy_coverage": failure_coverage,
        "module_artifacts": [str(path.relative_to(output_dir)) for path in sorted(module_paths)],
    }


def execute(config: RunnerConfig) -> Dict[str, Any]:
    repo_root = config.repo_root.resolve()
    output_dir = config.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dag_scenario = contracts.load_json(config.dag_scenario_path)
    module_registry = contracts.load_json(repo_root / "mission/dag/registry/module_registry.v1.json")
    taxonomy_registry = contracts.load_json(repo_root / "mission/dag/registry/failure_taxonomy.v1.json")
    mission_scenario = contracts.load_json(config.mission_scenario_path)

    schema_errors: List[str] = []
    schema_errors.extend(contracts.validate_module_registry(module_registry, repo_root=repo_root))
    schema_errors.extend(contracts.validate_failure_taxonomy(taxonomy_registry))
    schema_errors.extend(contracts.validate_scenario_dag(dag_scenario, module_registry))
    if schema_errors:
        raise ValueError("DAG contracts invalid: " + "; ".join(schema_errors))

    domain_guard = _run_domain_guard(repo_root, config.mission_scenario_path)
    if domain_guard.get("status") != "PASS":
        raise ValueError("parameter_domain_guard failed: " + "; ".join(domain_guard.get("errors", [])))

    optimization_guard_result = _run_optimization_guard(repo_root)
    if optimization_guard_result.get("status") != "PASS":
        raise ValueError(
            "optimization_guard failed: " + "; ".join(optimization_guard_result.get("errors", []))
        )

    forced_failures = dict(config.forced_failures or {})

    primary = _run_once(
        repo_root=repo_root,
        dag_scenario=dag_scenario,
        dag_registry=module_registry,
        taxonomy_registry=taxonomy_registry,
        mission_scenario=mission_scenario,
        mode=config.mode,
        seed=config.seed,
        output_dir=output_dir,
        forced_failures=forced_failures,
    )

    determinism = {
        "requested": bool(config.verify_deterministic),
        "same_seed_manifest_hash": None,
        "same_seed_match": None,
        "different_seed_manifest_hash": None,
        "different_seed_differs": None,
        "verdict": "SKIPPED",
    }

    if config.verify_deterministic:
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            run_same = _run_once(
                repo_root=repo_root,
                dag_scenario=dag_scenario,
                dag_registry=module_registry,
                taxonomy_registry=taxonomy_registry,
                mission_scenario=mission_scenario,
                mode=config.mode,
                seed=config.seed,
                output_dir=Path(tmp_a),
                forced_failures=forced_failures,
            )
            run_diff = _run_once(
                repo_root=repo_root,
                dag_scenario=dag_scenario,
                dag_registry=module_registry,
                taxonomy_registry=taxonomy_registry,
                mission_scenario=mission_scenario,
                mode=config.mode,
                seed=config.seed + 1,
                output_dir=Path(tmp_b),
                forced_failures=forced_failures,
            )

        determinism.update(
            {
                "same_seed_manifest_hash": run_same["manifest"]["manifest_hash"],
                "same_seed_match": run_same["manifest"]["manifest_hash"] == primary["manifest"]["manifest_hash"],
                "different_seed_manifest_hash": run_diff["manifest"]["manifest_hash"],
                "different_seed_differs": run_diff["manifest"]["manifest_hash"] != primary["manifest"]["manifest_hash"],
            }
        )
        determinism["verdict"] = (
            "PASS" if determinism["same_seed_match"] and determinism["different_seed_differs"] else "FAIL"
        )

    final_status = "PASS"
    if primary["status"] != "PASS":
        final_status = "FAIL"
    if determinism["requested"] and determinism["verdict"] != "PASS":
        final_status = "FAIL"

    return {
        "status": final_status,
        "domain_guard": domain_guard,
        "optimization_guard": optimization_guard_result,
        "primary": primary,
        "determinism": determinism,
    }
