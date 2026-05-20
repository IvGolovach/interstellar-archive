"""Deterministic mission-level probability coupling.

The coupling artifact connects user-selected mission rows to capsule/data risk
factors while keeping external target-delivery and archive-recovery factors
explicit and open.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from mission.dag.runner_v1 import RunnerConfig, execute
from mission.user_runs.catalog import compile_selected_mission_scenario


SCHEMA_VERSION = "mission_probability_coupling.v1"
GENERATOR = "scripts/build_mission_probability_coupling_artifact.py"
PUBLIC_SCOPE = "factorized_mission_probability_coupling"
SOURCE_USER_RUNS = "artifacts/user_mission_run_catalog.v1.json"
SOURCE_RISK_BUDGET = "artifacts/capsule_risk_budget.v1.json"
SOURCE_FEASIBILITY = "artifacts/mission_feasibility_screen.v1.json"
SOURCE_P_SUCCESS = "artifacts/p_success_defensibility.json"
SOURCE_OBJECTIVE_SCORE = "artifacts/objective_score_baseline.v1.json"
SOURCE_DAG_SCENARIO = "mission/dag/scenarios/mission_dag_baseline.v1.json"
SOURCE_DAG_MODULE_REGISTRY = "mission/dag/registry/module_registry.v1.json"
SOURCE_DAG_FAILURE_TAXONOMY = "mission/dag/registry/failure_taxonomy.v1.json"
SOURCE_BASELINE_SCENARIO = "mission/BASELINE_SCENARIO_v1.json"

FORMULA = (
    "P_archive_recoverable = P_target_delivery * P_environment_survival * "
    "P_capsule_survival * P_data_integrity * P_recovery_readout"
)
OPEN_STATUS = "not_closed_external_factors_open"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _probability(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = float(value)
        if 0.0 <= numeric <= 1.0:
            return _round(numeric)
    return None


def _risk_lookup(risk_budget: Mapping[str, Any]) -> Dict[tuple[str, str], Mapping[str, Any]]:
    rows = risk_budget.get("risk_budgets", [])
    if not isinstance(rows, list):
        return {}
    out: Dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        row_id = row.get("row_id")
        attack_mode_id = row.get("attack_mode_id")
        if isinstance(row_id, str) and isinstance(attack_mode_id, str):
            out[(row_id, attack_mode_id)] = row
    return out


def _factor(
    *,
    factor_id: str,
    label: str,
    status: str,
    value_p50: float | None,
    evidence_class: str,
    source_ref: str | None,
    gap: str | None,
) -> Dict[str, Any]:
    return {
        "factor_id": factor_id,
        "label": label,
        "status": status,
        "value_p50": value_p50,
        "evidence_class": evidence_class,
        "source_ref": source_ref,
        "external_evidence_gap": gap,
    }


def _risk_row_for(
    run_row: Mapping[str, Any],
    risk_lookup: Mapping[tuple[str, str], Mapping[str, Any]],
) -> Mapping[str, Any]:
    refs = run_row.get("source_refs", {})
    if not isinstance(refs, Mapping):
        refs = {}
    row_id = refs.get("capsule_risk_budget_row_id")
    attack_mode_id = refs.get("capsule_risk_attack_mode_id", "nominal")
    if isinstance(row_id, str) and isinstance(attack_mode_id, str):
        found = risk_lookup.get((row_id, attack_mode_id))
        if isinstance(found, Mapping):
            return found
    return {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _compact_mode_summaries(payload: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for mode, summary in sorted(payload.items()):
        if not isinstance(summary, Mapping):
            continue
        out[str(mode)] = {
            "mode": summary.get("mode"),
            "final_metrics": summary.get("final_metrics", {}),
            "core_probability": summary.get("core_probability"),
            "trust_weighted_score": summary.get("trust_weighted_score"),
            "speculative_parameters_used": summary.get("speculative_parameters_used", []),
        }
    return out


def _dag_snapshot(repo_root: Path, run_row: Mapping[str, Any]) -> Dict[str, Any]:
    compiled_scenario = compile_selected_mission_scenario(repo_root, run_row, mode="dual", seed=1)
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_dir = Path(tmp_dir)
        scenario_path = output_dir / "COMPILED_MISSION_SCENARIO.json"
        _write_json(scenario_path, compiled_scenario)
        result = execute(
            RunnerConfig(
                repo_root=repo_root,
                dag_scenario_path=(repo_root / SOURCE_DAG_SCENARIO).resolve(),
                mission_scenario_path=scenario_path.resolve(),
                mode="dual",
                seed=1,
                output_dir=(output_dir / "mission_dag").resolve(),
                verify_deterministic=False,
                forced_failures={},
            )
        )
    primary = result["primary"]
    taxonomy = primary["failure_taxonomy_coverage"]
    return {
        "status": result["status"],
        "mode": "dual",
        "seed": 1,
        "compiled_mission_scenario_sha256": hashlib.sha256(
            json.dumps(compiled_scenario, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        ).hexdigest(),
        "execution_modes": primary["execution_modes"],
        "manifest_hash": primary["manifest"]["manifest_hash"],
        "module_artifact_count": primary["manifest"]["module_artifact_count"],
        "hashchain_status": primary["hashchain_proof"]["status"],
        "failure_taxonomy_status": taxonomy["status"],
        "used_failure_ids": taxonomy["used_failure_ids"],
        "mode_summaries": _compact_mode_summaries(primary["mode_summaries"]),
        "determinism_policy": "covered_by_artifact_determinism_validator",
    }


def _capsule_data_band(run_row: Mapping[str, Any]) -> Dict[str, float | None]:
    prob = run_row.get("probability_snapshot", {})
    if not isinstance(prob, Mapping):
        prob = {}
    data_p50 = _probability(prob.get("data_integrity_p50"))
    out: Dict[str, float | None] = {}
    for key, survival_key in (
        ("p05", "capsule_survival_p05"),
        ("p50", "capsule_survival_p50"),
        ("p95", "capsule_survival_p95"),
    ):
        survival = _probability(prob.get(survival_key))
        out[key] = _round(survival * data_p50) if survival is not None and data_p50 is not None else None
    return out


def _coupling_row(repo_root: Path, run_row: Mapping[str, Any], risk_row: Mapping[str, Any]) -> Dict[str, Any]:
    selection = run_row.get("selection", {})
    if not isinstance(selection, Mapping):
        selection = {}
    refs = run_row.get("source_refs", {})
    if not isinstance(refs, Mapping):
        refs = {}
    probability_snapshot = run_row.get("probability_snapshot", {})
    if not isinstance(probability_snapshot, Mapping):
        probability_snapshot = {}
    risk_budget = risk_row.get("risk_budget", {})
    if not isinstance(risk_budget, Mapping):
        risk_budget = {}

    capsule_survival_p50 = _probability(probability_snapshot.get("capsule_survival_p50"))
    data_integrity_p50 = _probability(probability_snapshot.get("data_integrity_p50"))
    band = _capsule_data_band(run_row)
    closed_p50 = band["p50"]
    coupling_id = f"mpc-{run_row['run_id'][4:]}"

    gaps = list(run_row.get("external_evidence_gaps", [])) if isinstance(run_row.get("external_evidence_gaps"), list) else []
    risk_gaps = list(risk_row.get("evidence_gap_ids", [])) if isinstance(risk_row.get("evidence_gap_ids"), list) else []
    blocked = list(run_row.get("blocked_claims", [])) if isinstance(run_row.get("blocked_claims"), list) else []
    risk_blocked = list(risk_row.get("blocking_claims", [])) if isinstance(risk_row.get("blocking_claims"), list) else []
    blocked_claims = sorted({*blocked, *risk_blocked, "full mission probability closed", "guaranteed archive recovery"})
    evidence_gaps = sorted({*gaps, *risk_gaps})

    factors = [
        _factor(
            factor_id="target_delivery",
            label="Target delivery and navigation",
            status="external_required",
            value_p50=None,
            evidence_class="not_repo_closed",
            source_ref="mission_feasibility_screen.target_velocity_time",
            gap="launch procurement, navigation, and target acquisition authority",
        ),
        _factor(
            factor_id="environment_path",
            label="Whole-path environment survival",
            status="external_required",
            value_p50=None,
            evidence_class="not_repo_closed",
            source_ref="mission_feasibility_screen.dust_gas_black_hole_screens",
            gap="target-specific line-of-sight dust, gas, radiation, and black-hole environment model",
        ),
        _factor(
            factor_id="capsule_survival",
            label="Capsule survival",
            status="repo_estimated_review_proxy",
            value_p50=capsule_survival_p50,
            evidence_class="capsule_risk_budget_reduced_order",
            source_ref=str(refs.get("capsule_risk_budget_row_id", "")),
            gap=None,
        ),
        _factor(
            factor_id="data_integrity",
            label="Archive data integrity",
            status="repo_estimated_review_proxy",
            value_p50=data_integrity_p50,
            evidence_class="capsule_risk_budget_reduced_order",
            source_ref=str(refs.get("capsule_risk_budget_row_id", "")),
            gap=None,
        ),
        _factor(
            factor_id="recovery_readout",
            label="Arrival recovery and readout",
            status="external_required",
            value_p50=None,
            evidence_class="not_repo_closed",
            source_ref=None,
            gap="arrival discovery, retrieval, power-up, and media readout evidence",
        ),
    ]

    open_factor_count = sum(1 for item in factors if item["status"] == "external_required")
    closed_factor_count = sum(1 for item in factors if item["value_p50"] is not None)

    dag_snapshot = _dag_snapshot(repo_root, run_row)

    return {
        "coupling_id": coupling_id,
        "run_id": run_row["run_id"],
        "selection_hash": run_row["selection_hash"],
        "target_id": selection.get("target_id"),
        "target_label": selection.get("target_label"),
        "velocity_id": selection.get("velocity_id"),
        "velocity_label": selection.get("velocity_label"),
        "flight_years": selection.get("flight_years"),
        "time_horizon_class": selection.get("time_horizon_class"),
        "source_refs": {
            "user_mission_run_catalog": SOURCE_USER_RUNS,
            "capsule_risk_budget": SOURCE_RISK_BUDGET,
            "capsule_risk_budget_row_id": refs.get("capsule_risk_budget_row_id"),
            "capsule_risk_attack_mode_id": refs.get("capsule_risk_attack_mode_id"),
            "mission_feasibility_screen": SOURCE_FEASIBILITY,
            "feasibility_row_id": refs.get("feasibility_row_id"),
            "mission_dag_scenario": SOURCE_DAG_SCENARIO,
        },
        "formula": FORMULA,
        "factor_budget": factors,
        "closed_factor_count": closed_factor_count,
        "open_external_factor_count": open_factor_count,
        "closed_capsule_data_probability": {
            "p05": band["p05"],
            "p50": closed_p50,
            "p95": band["p95"],
            "status": "review_proxy_only",
            "claim_boundary": "Capsule survival times data integrity only; not full mission success.",
        },
        "full_mission_probability": {
            "p05": None,
            "p50": None,
            "p95": None,
            "status": OPEN_STATUS,
            "blocking_open_factors": [
                item["factor_id"]
                for item in factors
                if item["status"] == "external_required"
            ],
        },
        "risk_budget_snapshot": {
            "status": risk_budget.get("status"),
            "loss_probability": risk_budget.get("loss_probability"),
            "margin": risk_budget.get("margin"),
            "top_uncertainty_drivers": risk_row.get("top_uncertainty_drivers", []),
            "failure_mode_contributions": risk_row.get("failure_mode_contributions", []),
        },
        "dag_coupling": {
            "status": "tracked_compact_snapshot",
            "runtime_script": "scripts/run_user_mission_scenario.py",
            "mission_dag_scenario": SOURCE_DAG_SCENARIO,
            "manifest_hash_policy": "compact tracked snapshot plus full local review pack under ops/reports/user-mission-runs",
            "writes_tracked_files": False,
        },
        "dag_snapshot": dag_snapshot,
        "external_evidence_gaps": evidence_gaps,
        "blocked_claims": blocked_claims,
        "verdict": "review_required",
        "non_certification_notice": True,
    }


def build_mission_probability_coupling(repo_root: Path) -> Dict[str, Any]:
    catalog = _load_json(repo_root / SOURCE_USER_RUNS)
    risk_budget = _load_json(repo_root / SOURCE_RISK_BUDGET)
    lookup = _risk_lookup(risk_budget)
    rows = [
        _coupling_row(repo_root, row, _risk_row_for(row, lookup))
        for row in catalog.get("run_rows", [])
        if isinstance(row, Mapping)
    ]
    rows.sort(key=lambda item: item["coupling_id"])
    default_run_id = catalog.get("default_run_id")
    default_row = next((row for row in rows if row.get("run_id") == default_run_id), rows[0] if rows else None)
    source_paths = [
        SOURCE_USER_RUNS,
        SOURCE_RISK_BUDGET,
        SOURCE_FEASIBILITY,
        SOURCE_P_SUCCESS,
        SOURCE_OBJECTIVE_SCORE,
        SOURCE_DAG_SCENARIO,
        SOURCE_DAG_MODULE_REGISTRY,
        SOURCE_DAG_FAILURE_TAXONOMY,
        SOURCE_BASELINE_SCENARIO,
    ]
    open_factor_total = sum(int(row["open_external_factor_count"]) for row in rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "public_scope": PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": [{"path": path, "sha256": _sha256_file(repo_root / path)} for path in source_paths],
        "formula": FORMULA,
        "factor_policy": {
            "full_mission_probability_status": OPEN_STATUS,
            "closed_proxy_policy": "closed_capsule_data_probability is reportable only as a review proxy",
            "external_factor_count_per_row": 3,
            "repo_estimated_factor_count_per_row": 2,
        },
        "coupling_count": len(rows),
        "default_coupling_id": default_row.get("coupling_id") if isinstance(default_row, Mapping) else None,
        "default_run_id": default_run_id,
        "coupling_rows": rows,
        "rollup": {
            "rows_with_full_mission_probability_closed": 0,
            "rows_with_review_proxy": sum(1 for row in rows if row["closed_capsule_data_probability"]["p50"] is not None),
            "open_external_factor_total": open_factor_total,
            "blocked_claims": [
                "full mission probability closed",
                "mission feasible",
                "flight ready",
                "guaranteed arrival or archive recovery",
            ],
        },
        "interpretation_limits": [
            "Full mission probability is intentionally not closed while target delivery and recovery factors lack evidence.",
            "Closed capsule/data probability is a review proxy, not P_archive_recoverable.",
            "DAG coupling is available through local review packs; browser surfaces render tracked artifact values only.",
        ],
    }


def _validate_probability(value: Any, field: str, errors: List[str]) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 <= float(value) <= 1.0:
        errors.append(f"{field} must be a probability")


def validate_mission_probability_coupling(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if payload.get("generator") != GENERATOR:
        errors.append(f"generator must be {GENERATOR}")
    if payload.get("public_scope") != PUBLIC_SCOPE:
        errors.append(f"public_scope must be {PUBLIC_SCOPE}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("formula") != FORMULA:
        errors.append("formula mismatch")
    source_artifacts = payload.get("source_artifacts")
    if not isinstance(source_artifacts, list) or len(source_artifacts) != 9:
        errors.append("source_artifacts must contain nine source refs")
    policy = payload.get("factor_policy")
    if not isinstance(policy, Mapping) or policy.get("full_mission_probability_status") != OPEN_STATUS:
        errors.append("factor_policy.full_mission_probability_status must keep external factors open")
    rows = payload.get("coupling_rows")
    if not isinstance(rows, list) or len(rows) != 15:
        errors.append("coupling_rows must contain exactly 15 rows")
        rows = []
    if payload.get("coupling_count") != len(rows):
        errors.append("coupling_count must equal len(coupling_rows)")

    coupling_ids: set[str] = set()
    default_seen = False
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"coupling_rows[{index}] must be object")
            continue
        prefix = f"coupling_rows[{index}]"
        coupling_id = row.get("coupling_id")
        if not isinstance(coupling_id, str) or not coupling_id.startswith("mpc-"):
            errors.append(f"{prefix}.coupling_id must be mpc-*")
        elif coupling_id in coupling_ids:
            errors.append(f"{prefix}.coupling_id duplicated")
        else:
            coupling_ids.add(coupling_id)
        if not isinstance(row.get("run_id"), str) or not row["run_id"].startswith("umr-"):
            errors.append(f"{prefix}.run_id must be umr-*")
        if not isinstance(row.get("selection_hash"), str) or len(str(row.get("selection_hash"))) != 64:
            errors.append(f"{prefix}.selection_hash must be sha256")
        if row.get("formula") != FORMULA:
            errors.append(f"{prefix}.formula mismatch")
        factors = row.get("factor_budget")
        if not isinstance(factors, list) or len(factors) != 5:
            errors.append(f"{prefix}.factor_budget must contain five factors")
            factors = []
        factor_ids = {item.get("factor_id") for item in factors if isinstance(item, Mapping)}
        expected = {"target_delivery", "environment_path", "capsule_survival", "data_integrity", "recovery_readout"}
        if factor_ids != expected:
            errors.append(f"{prefix}.factor_budget factor ids mismatch")
        if row.get("open_external_factor_count") != 3:
            errors.append(f"{prefix}.open_external_factor_count must be 3")
        if row.get("closed_factor_count") != 2:
            errors.append(f"{prefix}.closed_factor_count must be 2")
        closed = row.get("closed_capsule_data_probability")
        if not isinstance(closed, Mapping):
            errors.append(f"{prefix}.closed_capsule_data_probability must be object")
        else:
            for key in ("p05", "p50", "p95"):
                _validate_probability(closed.get(key), f"{prefix}.closed_capsule_data_probability.{key}", errors)
            p05 = closed.get("p05")
            p50 = closed.get("p50")
            p95 = closed.get("p95")
            if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (p05, p50, p95)):
                if not float(p05) <= float(p50) <= float(p95):
                    errors.append(f"{prefix}.closed_capsule_data_probability quantiles must be ordered")
            if closed.get("status") != "review_proxy_only":
                errors.append(f"{prefix}.closed_capsule_data_probability.status must be review_proxy_only")
            factor_values = {
                str(item.get("factor_id")): item.get("value_p50")
                for item in factors
                if isinstance(item, Mapping)
            }
            survival = factor_values.get("capsule_survival")
            data = factor_values.get("data_integrity")
            if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (survival, data, closed.get("p50"))):
                expected_p50 = _round(float(survival) * float(data))
                if abs(expected_p50 - float(closed["p50"])) > 1e-12:
                    errors.append(f"{prefix}.closed_capsule_data_probability.p50 must equal capsule_survival * data_integrity")
        full = row.get("full_mission_probability")
        if not isinstance(full, Mapping):
            errors.append(f"{prefix}.full_mission_probability must be object")
        else:
            if full.get("status") != OPEN_STATUS:
                errors.append(f"{prefix}.full_mission_probability.status must be {OPEN_STATUS}")
            for key in ("p05", "p50", "p95"):
                if full.get(key) is not None:
                    errors.append(f"{prefix}.full_mission_probability.{key} must remain null")
            blockers = full.get("blocking_open_factors")
            if not isinstance(blockers, list) or len(blockers) != 3:
                errors.append(f"{prefix}.full_mission_probability.blocking_open_factors must contain 3 items")
        dag = row.get("dag_coupling")
        if not isinstance(dag, Mapping) or dag.get("writes_tracked_files") is not False:
            errors.append(f"{prefix}.dag_coupling.writes_tracked_files must be false")
        snapshot = row.get("dag_snapshot")
        if not isinstance(snapshot, Mapping):
            errors.append(f"{prefix}.dag_snapshot must be object")
        else:
            if snapshot.get("status") != "PASS":
                errors.append(f"{prefix}.dag_snapshot.status must be PASS")
            if snapshot.get("hashchain_status") != "PASS":
                errors.append(f"{prefix}.dag_snapshot.hashchain_status must be PASS")
            if snapshot.get("failure_taxonomy_status") != "PASS":
                errors.append(f"{prefix}.dag_snapshot.failure_taxonomy_status must be PASS")
            if not isinstance(snapshot.get("manifest_hash"), str) or len(str(snapshot.get("manifest_hash"))) != 64:
                errors.append(f"{prefix}.dag_snapshot.manifest_hash must be sha256")
            if not isinstance(snapshot.get("compiled_mission_scenario_sha256"), str) or len(str(snapshot.get("compiled_mission_scenario_sha256"))) != 64:
                errors.append(f"{prefix}.dag_snapshot.compiled_mission_scenario_sha256 must be sha256")
            if not isinstance(snapshot.get("module_artifact_count"), int) or int(snapshot.get("module_artifact_count", 0)) < 6:
                errors.append(f"{prefix}.dag_snapshot.module_artifact_count must be >= 6")
            if snapshot.get("execution_modes") != ["realistic", "speculative"]:
                errors.append(f"{prefix}.dag_snapshot.execution_modes must be realistic/speculative")
            summaries = snapshot.get("mode_summaries")
            if not isinstance(summaries, Mapping) or set(summaries.keys()) != {"realistic", "speculative"}:
                errors.append(f"{prefix}.dag_snapshot.mode_summaries must include realistic and speculative")
        if not isinstance(row.get("external_evidence_gaps"), list) or not row["external_evidence_gaps"]:
            errors.append(f"{prefix}.external_evidence_gaps must be non-empty")
        blocked = row.get("blocked_claims")
        if not isinstance(blocked, list) or "full mission probability closed" not in blocked:
            errors.append(f"{prefix}.blocked_claims must block full mission probability closure")
        if row.get("non_certification_notice") is not True:
            errors.append(f"{prefix}.non_certification_notice must be true")
        if row.get("run_id") == payload.get("default_run_id"):
            default_seen = row.get("coupling_id") == payload.get("default_coupling_id")
    if not default_seen:
        errors.append("default_coupling_id must reference default_run_id")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
    else:
        if rollup.get("rows_with_full_mission_probability_closed") != 0:
            errors.append("rollup.rows_with_full_mission_probability_closed must be 0")
        if rollup.get("rows_with_review_proxy") != len(rows):
            errors.append("rollup.rows_with_review_proxy must equal budget row count")
    return errors
