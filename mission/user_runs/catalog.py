"""Deterministic user-selected mission run catalog.

The catalog gives every target/velocity choice from the Mission Feasibility
Screen a stable run identity and a local review-pack contract. It is a run-store
surface, not a flight-readiness or procurement decision.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import copy
from pathlib import Path
from typing import Any, Dict, List, Mapping

from mission.dag.runner_v1 import RunnerConfig, execute


SCHEMA_VERSION = "user_mission_run_catalog.v1"
SUMMARY_SCHEMA_VERSION = "user_mission_run_summary.v1"
GENERATOR = "scripts/build_user_mission_run_catalog_artifact.py"
PUBLIC_SCOPE = "user_selected_mission_run_catalog"
SOURCE_FEASIBILITY = "artifacts/mission_feasibility_screen.v1.json"
SOURCE_CAPSULE_RISK = "artifacts/capsule_risk_budget.v1.json"
SOURCE_CAPSULE_LAB = "artifacts/capsule_survivability_lab.v1.json"
SOURCE_DAG_SCENARIO = "mission/dag/scenarios/mission_dag_baseline.v1.json"
SOURCE_BASELINE_SCENARIO = "mission/BASELINE_SCENARIO_v1.json"
SOURCE_MISSION_SCHEMA = "mission/MISSION_SCHEMA_v1.json"
SOURCE_CATALOG_SPEC = "mission/USER_MISSION_RUN_CATALOG_SPEC_v1.md"
SOURCE_CATALOG_MODULE = "mission/user_runs/catalog.py"
SOURCE_RUNNER = "scripts/run_user_mission_scenario.py"
SOURCE_PACK_VALIDATOR = "scripts/ci/user_mission_run_pack_validate.py"
DEFAULT_OUTPUT_ROOT = "ops/reports/user-mission-runs"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(value: str | bytes) -> str:
    payload = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _round(value: Any, digits: int = 12) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return float(f"{float(value):.{digits}f}")


def _head_sha(repo_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _selection_payload(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "feasibility_row_id": row["id"],
        "source_capsule_row_id": row["source_capsule_row_id"],
        "target_id": row["target_id"],
        "target_label": row["target_label"],
        "target_detail": row["target_detail"],
        "distance_ly": row["distance_ly"],
        "velocity_id": row["velocity_id"],
        "velocity_label": row["velocity_label"],
        "velocity_detail": row["velocity_detail"],
        "velocity_km_s": row["velocity_km_s"],
        "velocity_fraction_c": row["velocity_fraction_c"],
        "flight_years": row["flight_years"],
        "time_horizon_class": row["time_horizon_class"],
    }


def _run_id(row: Mapping[str, Any], selection_hash: str) -> str:
    return f"umr-{row['target_id']}-{row['velocity_id']}-{selection_hash[:10]}"


def _catalog_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    risk = row.get("capsule_risk_budget_link", {})
    if not isinstance(risk, Mapping):
        risk = {}
    feasibility = row.get("feasibility", {})
    if not isinstance(feasibility, Mapping):
        feasibility = {}
    selection = _selection_payload(row)
    selection_hash = sha256_hex(
        canonical_json(
            {
                "schema_version": SCHEMA_VERSION,
                "selection": selection,
                "risk_row_id": risk.get("row_id"),
                "attack_mode_id": risk.get("attack_mode_id"),
            }
        )
    )
    run_id = _run_id(row, selection_hash)
    survival_p50 = risk.get("survival_p50")
    data_integrity_p50 = risk.get("data_integrity_p50")
    coupled_p50 = None
    if isinstance(survival_p50, (int, float)) and isinstance(data_integrity_p50, (int, float)):
        coupled_p50 = _round(float(survival_p50) * float(data_integrity_p50), 12)

    return {
        "run_id": run_id,
        "selection_hash": selection_hash,
        "selection": selection,
        "source_refs": {
            "feasibility_artifact": SOURCE_FEASIBILITY,
            "feasibility_row_id": row["id"],
            "capsule_risk_budget_artifact": SOURCE_CAPSULE_RISK,
            "capsule_risk_budget_row_id": risk.get("row_id"),
            "capsule_risk_attack_mode_id": risk.get("attack_mode_id"),
            "capsule_lab_artifact": SOURCE_CAPSULE_LAB,
            "capsule_lab_row_id": row["source_capsule_row_id"],
        },
        "probability_snapshot": {
            "p_hit_policy": "not_closed_by_catalog",
            "capsule_survival_p05": risk.get("survival_p05"),
            "capsule_survival_p50": survival_p50,
            "capsule_survival_p95": risk.get("survival_p95"),
            "data_integrity_p50": data_integrity_p50,
            "capsule_data_coupled_p50": coupled_p50,
            "claim_boundary": "Capsule-risk snapshot only; targetability and archive recovery remain separate gaps.",
        },
        "feasibility_status": {
            "status": feasibility.get("status", "review_required"),
            "blockers": list(feasibility.get("blockers", [])) if isinstance(feasibility.get("blockers"), list) else [],
            "non_certification_notice": True,
        },
        "exposure_snapshot": {
            "dust_screen": row.get("dust_screen", {}),
            "gas_screen": row.get("gas_screen", {}),
            "black_hole_screen": row.get("black_hole_screen", {}),
            "radiation_material_hooks": row.get("radiation_material_hooks", {}),
        },
        "cost_energy_proxy": row.get("cost_energy_proxy", {}),
        "external_evidence_gaps": list(row.get("external_evidence_gaps", [])),
        "blocked_claims": list(row.get("blocked_claims", [])),
        "runtime_pack_template": {
            "script": "scripts/run_user_mission_scenario.py",
            "output_root": DEFAULT_OUTPUT_ROOT,
            "args": {
                "--target-id": row["target_id"],
                "--velocity-id": row["velocity_id"],
                "--mode": "dual",
                "--seed": 1,
                "--run-id": run_id,
            },
            "writes_tracked_files": False,
        },
    }


def build_user_mission_run_catalog(repo_root: Path) -> Dict[str, Any]:
    feasibility = _load_json(repo_root / SOURCE_FEASIBILITY)
    run_rows = [_catalog_row(row) for row in feasibility.get("scenario_rows", []) if isinstance(row, Mapping)]
    run_rows.sort(key=lambda item: item["run_id"])
    default_feasibility_id = feasibility.get("default_scenario_id")
    default_run = next(
        (item for item in run_rows if item["selection"]["feasibility_row_id"] == default_feasibility_id),
        run_rows[0] if run_rows else None,
    )
    target_ids = sorted({str(row["selection"]["target_id"]) for row in run_rows})
    velocity_ids = sorted({str(row["selection"]["velocity_id"]) for row in run_rows})
    source_paths = [SOURCE_FEASIBILITY, SOURCE_CAPSULE_RISK, SOURCE_CAPSULE_LAB, SOURCE_DAG_SCENARIO, SOURCE_BASELINE_SCENARIO]
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "public_scope": PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": [
            {"path": path, "sha256": _sha256_file(repo_root / path)}
            for path in source_paths
        ],
        "run_store_policy": {
            "output_root": DEFAULT_OUTPUT_ROOT,
            "tracked_by_default": False,
            "deterministic_run_id_source": "selection_hash",
            "user_owned_run_boundary": "local review packs are generated under ops/reports and are not certification records",
        },
        "target_count": len(target_ids),
        "velocity_count": len(velocity_ids),
        "run_count": len(run_rows),
        "default_run_id": default_run["run_id"] if isinstance(default_run, Mapping) else None,
        "target_ids": target_ids,
        "velocity_ids": velocity_ids,
        "run_rows": run_rows,
        "interpretation_limits": [
            "Catalog rows package reviewed assumptions; they do not run a launch provider, trajectory optimizer, or procurement model.",
            "A generated local review pack is deterministic evidence of the selected assumptions, not evidence of physical qualification.",
            "Targetability, arrival recovery, and archive readability remain explicit external evidence gaps.",
        ],
    }


def validate_user_mission_run_catalog(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if payload.get("generator") != GENERATOR:
        errors.append(f"generator must be {GENERATOR}")
    if payload.get("public_scope") != PUBLIC_SCOPE:
        errors.append(f"public_scope must be {PUBLIC_SCOPE}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("target_count") != 3:
        errors.append("target_count must be 3")
    if payload.get("velocity_count") != 5:
        errors.append("velocity_count must be 5")
    rows = payload.get("run_rows")
    if not isinstance(rows, list) or len(rows) != 15:
        errors.append("run_rows must contain exactly 15 rows")
        rows = []
    if payload.get("run_count") != len(rows):
        errors.append("run_count must equal len(run_rows)")
    source_artifacts = payload.get("source_artifacts")
    if not isinstance(source_artifacts, list) or len(source_artifacts) != 5:
        errors.append("source_artifacts must contain feasibility, risk, capsule, DAG, and baseline artifacts")
    policy = payload.get("run_store_policy")
    if not isinstance(policy, Mapping) or policy.get("tracked_by_default") is not False:
        errors.append("run_store_policy.tracked_by_default must be false")

    run_ids: set[str] = set()
    hashes: set[str] = set()
    default_seen = False
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"run_rows[{index}] must be object")
            continue
        prefix = f"run_rows[{index}]"
        run_id = row.get("run_id")
        if not isinstance(run_id, str) or not run_id.startswith("umr-"):
            errors.append(f"{prefix}.run_id must be stable umr-* string")
        elif run_id in run_ids:
            errors.append(f"{prefix}.run_id duplicated: {run_id}")
        else:
            run_ids.add(run_id)
        selection_hash = row.get("selection_hash")
        if not isinstance(selection_hash, str) or len(selection_hash) != 64:
            errors.append(f"{prefix}.selection_hash must be sha256")
        elif selection_hash in hashes:
            errors.append(f"{prefix}.selection_hash duplicated")
        else:
            hashes.add(selection_hash)
        selection = row.get("selection")
        if not isinstance(selection, Mapping):
            errors.append(f"{prefix}.selection must be object")
            continue
        if selection.get("target_id") == "reference-black-hole" and selection.get("velocity_id") == "conditional-45":
            default_seen = row.get("run_id") == payload.get("default_run_id")
            years = selection.get("flight_years")
            if not isinstance(years, (int, float)) or not 10_000_000 <= float(years) <= 10_700_000:
                errors.append(f"{prefix}.selection.flight_years must keep default black-hole row near 10 Myr")
        for field in ("target_id", "velocity_id", "feasibility_row_id", "source_capsule_row_id"):
            if not isinstance(selection.get(field), str) or not selection.get(field):
                errors.append(f"{prefix}.selection.{field} must be non-empty string")
        prob = row.get("probability_snapshot")
        if not isinstance(prob, Mapping):
            errors.append(f"{prefix}.probability_snapshot must be object")
        else:
            for field in ("capsule_survival_p50", "data_integrity_p50", "capsule_data_coupled_p50"):
                value = prob.get(field)
                if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
                    errors.append(f"{prefix}.probability_snapshot.{field} must be probability")
        status = row.get("feasibility_status")
        if not isinstance(status, Mapping) or status.get("non_certification_notice") is not True:
            errors.append(f"{prefix}.feasibility_status.non_certification_notice must be true")
        if not isinstance(row.get("external_evidence_gaps"), list) or not row["external_evidence_gaps"]:
            errors.append(f"{prefix}.external_evidence_gaps must be non-empty")
        if not isinstance(row.get("blocked_claims"), list) or "flight ready" not in row["blocked_claims"]:
            errors.append(f"{prefix}.blocked_claims must include flight ready")
        template = row.get("runtime_pack_template")
        if not isinstance(template, Mapping) or template.get("script") != "scripts/run_user_mission_scenario.py":
            errors.append(f"{prefix}.runtime_pack_template.script mismatch")
        elif template.get("writes_tracked_files") is not False:
            errors.append(f"{prefix}.runtime_pack_template.writes_tracked_files must be false")
    if not default_seen:
        errors.append("default_run_id must reference reference-black-hole conditional-45")
    return errors


def compile_selected_mission_scenario(repo_root: Path, selected: Mapping[str, Any], *, mode: str, seed: int) -> Dict[str, Any]:
    baseline = _load_json(repo_root / SOURCE_BASELINE_SCENARIO)
    scenario = copy.deepcopy(baseline)
    selection = selected["selection"]
    exposure = selected.get("exposure_snapshot", {})
    dust_screen = exposure.get("dust_screen", {}) if isinstance(exposure, Mapping) else {}
    if not isinstance(dust_screen, Mapping):
        dust_screen = {}

    scenario["mission_mode"] = "realistic" if mode in {"realistic", "dual"} else "speculative"
    scenario["seed"] = f"user-mission-run:{selected['run_id']}:{int(seed)}"
    scenario["bh_parameters"]["distance_from_earth_ly"] = float(selection["distance_ly"])
    if isinstance(dust_screen.get("dust_flux_scale"), (int, float)):
        scenario["environment_model"]["dust_flux_scale"] = float(dust_screen["dust_flux_scale"])
    return scenario


def validate_user_run_summary(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        errors.append(f"schema_version must be {SUMMARY_SCHEMA_VERSION}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("verdict") != "review_required":
        errors.append("verdict must be review_required")
    selected = payload.get("selected_run")
    if not isinstance(selected, Mapping):
        errors.append("selected_run must be object")
        selected = {}
    if not isinstance(payload.get("run_id"), str) or not payload["run_id"]:
        errors.append("run_id must be non-empty string")
    if not isinstance(payload.get("selection_hash"), str) or len(str(payload.get("selection_hash"))) != 64:
        errors.append("selection_hash must be sha256")
    if selected and payload.get("selection_hash") != selected.get("selection_hash"):
        errors.append("selection_hash must match selected_run.selection_hash")
    if not isinstance(payload.get("compiled_mission_scenario_sha256"), str) or len(str(payload.get("compiled_mission_scenario_sha256"))) != 64:
        errors.append("compiled_mission_scenario_sha256 must be sha256")
    dag = payload.get("dag_execution")
    if not isinstance(dag, Mapping):
        errors.append("dag_execution must be object")
    else:
        if dag.get("status") != "PASS":
            errors.append("dag_execution.status must be PASS")
        if not isinstance(dag.get("manifest_hash"), str) or len(str(dag.get("manifest_hash"))) != 64:
            errors.append("dag_execution.manifest_hash must be sha256")
        if not isinstance(dag.get("module_artifact_count"), int) or int(dag.get("module_artifact_count", 0)) < 6:
            errors.append("dag_execution.module_artifact_count must be >= 6")
        if dag.get("hashchain_status") != "PASS":
            errors.append("dag_execution.hashchain_status must be PASS")
    source_manifest = payload.get("source_manifest")
    if not isinstance(source_manifest, list) or len(source_manifest) < 6:
        errors.append("source_manifest must include catalog and source artifacts")
    if not isinstance(payload.get("external_evidence_gaps"), list) or not payload["external_evidence_gaps"]:
        errors.append("external_evidence_gaps must be non-empty")
    if not isinstance(payload.get("blocked_claims"), list) or "flight ready" not in payload["blocked_claims"]:
        errors.append("blocked_claims must include flight ready")
    return errors


def select_run_row(catalog: Mapping[str, Any], *, target_id: str, velocity_id: str) -> Dict[str, Any]:
    for row in catalog.get("run_rows", []):
        if not isinstance(row, Mapping):
            continue
        selection = row.get("selection", {})
        if (
            isinstance(selection, Mapping)
            and selection.get("target_id") == target_id
            and selection.get("velocity_id") == velocity_id
        ):
            return dict(row)
    raise ValueError(f"no user mission run row for target_id={target_id!r}, velocity_id={velocity_id!r}")


def render_run_report(summary: Mapping[str, Any]) -> str:
    run = summary["selected_run"]
    selection = run["selection"]
    prob = run["probability_snapshot"]
    return "\n".join(
        [
            "# User Mission Run Review Pack",
            "",
            f"- Run ID: `{summary['run_id']}`",
            f"- Target: `{selection['target_label']}`",
            f"- Velocity: `{selection['velocity_label']}`",
            f"- Flight years: `{selection['flight_years']}`",
            f"- Capsule survival p50: `{prob['capsule_survival_p50']}`",
            f"- Data integrity p50: `{prob['data_integrity_p50']}`",
            f"- Capsule/data coupled p50: `{prob['capsule_data_coupled_p50']}`",
            f"- Verdict: `{summary['verdict']}`",
            "",
            "## Claim Boundary",
            "",
            "This pack records the selected assumptions and source hashes. It is not a mission-readiness, certification, launch, procurement, or guaranteed archive-recovery record.",
            "",
            "## External Evidence Gaps",
            "",
            *[f"- {gap}" for gap in run["external_evidence_gaps"]],
            "",
            "## Blocked Claims",
            "",
            *[f"- {claim}" for claim in run["blocked_claims"]],
        ]
    )


def build_user_run_pack(
    *,
    repo_root: Path,
    target_id: str,
    velocity_id: str,
    output_dir: Path,
    run_id: str | None = None,
    mode: str = "dual",
    seed: int = 1,
) -> Dict[str, Any]:
    catalog_path = repo_root / "artifacts/user_mission_run_catalog.v1.json"
    catalog = _load_json(catalog_path)
    errors = validate_user_mission_run_catalog(catalog)
    if errors:
        raise ValueError("user mission run catalog invalid: " + "; ".join(errors))
    selected = select_run_row(catalog, target_id=target_id, velocity_id=velocity_id)
    effective_run_id = run_id or str(selected["run_id"])
    compiled_scenario = compile_selected_mission_scenario(repo_root, selected, mode=mode, seed=seed)
    source_manifest = [
        {"path": "artifacts/user_mission_run_catalog.v1.json", "sha256": _sha256_file(catalog_path)},
        *catalog["source_artifacts"],
        {"path": SOURCE_MISSION_SCHEMA, "sha256": _sha256_file(repo_root / SOURCE_MISSION_SCHEMA)},
        {"path": SOURCE_CATALOG_SPEC, "sha256": _sha256_file(repo_root / SOURCE_CATALOG_SPEC)},
        {"path": SOURCE_CATALOG_MODULE, "sha256": _sha256_file(repo_root / SOURCE_CATALOG_MODULE)},
        {"path": SOURCE_RUNNER, "sha256": _sha256_file(repo_root / SOURCE_RUNNER)},
        {"path": SOURCE_PACK_VALIDATOR, "sha256": _sha256_file(repo_root / SOURCE_PACK_VALIDATOR)},
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    compiled_scenario_path = output_dir / "COMPILED_MISSION_SCENARIO.json"
    compiled_scenario_path.write_text(
        json.dumps(compiled_scenario, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    dag_output_dir = output_dir / "mission_dag"
    dag_result = execute(
        RunnerConfig(
            repo_root=repo_root,
            dag_scenario_path=(repo_root / SOURCE_DAG_SCENARIO).resolve(),
            mission_scenario_path=compiled_scenario_path.resolve(),
            mode=mode,
            seed=int(seed),
            output_dir=dag_output_dir.resolve(),
            verify_deterministic=True,
            forced_failures={},
        )
    )
    dag_summary = {
        "status": dag_result["status"],
        "mode": mode,
        "seed": int(seed),
        "execution_modes": dag_result["primary"]["execution_modes"],
        "mode_summaries": dag_result["primary"]["mode_summaries"],
        "manifest_hash": dag_result["primary"]["manifest"]["manifest_hash"],
        "module_artifact_count": dag_result["primary"]["manifest"]["module_artifact_count"],
        "hashchain_status": dag_result["primary"]["hashchain_proof"]["status"],
        "failure_taxonomy_status": dag_result["primary"]["failure_taxonomy_coverage"]["status"],
        "determinism_verdict": dag_result["determinism"]["verdict"],
    }
    summary: Dict[str, Any] = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "run_id": effective_run_id,
        "catalog_run_id": selected["run_id"],
        "selection_hash": selected["selection_hash"],
        "created_from_commit": _head_sha(repo_root),
        "non_certification_notice": True,
        "selected_run": selected,
        "compiled_mission_scenario_ref": "COMPILED_MISSION_SCENARIO.json",
        "compiled_mission_scenario_sha256": _sha256_file(compiled_scenario_path),
        "dag_execution": dag_summary,
        "external_evidence_gaps": selected["external_evidence_gaps"],
        "blocked_claims": selected["blocked_claims"],
        "source_manifest": source_manifest,
        "verdict": "review_required",
        "claim_boundary": "Deterministic local review pack only; external evidence gaps remain open.",
    }
    summary_errors = validate_user_run_summary(summary)
    if summary_errors:
        raise ValueError("user mission run summary invalid: " + "; ".join(summary_errors))
    summary_hash = sha256_hex(canonical_json(summary))
    (output_dir / "USER_RUN_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "DAG_RUN_SUMMARY.json").write_text(
        json.dumps(dag_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "SOURCE_MANIFEST.json").write_text(
        json.dumps({"source_manifest": source_manifest}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "RUN_REPORT.md").write_text(render_run_report(summary) + "\n", encoding="utf-8")
    meta = {
        "run_id": effective_run_id,
        "catalog_run_id": selected["run_id"],
        "summary_sha256": summary_hash,
        "verdict": summary["verdict"],
        "dag_manifest_hash": dag_summary["manifest_hash"],
        "output_files": [
            "COMPILED_MISSION_SCENARIO.json",
            "USER_RUN_SUMMARY.json",
            "DAG_RUN_SUMMARY.json",
            "SOURCE_MANIFEST.json",
            "RUN_REPORT.md",
        ],
    }
    (output_dir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"summary": summary, "meta": meta, "output_dir": str(output_dir)}
