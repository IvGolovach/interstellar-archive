"""Deterministic external proof-phase artifacts.

These artifacts turn the next proof phase into machine-checkable repository
contracts. They deliberately do not manufacture third-party review records,
independent backend results, lab qualification, or source-grade promotions.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


YEAR_S = 365.25 * 24.0 * 3600.0
LIGHT_YEAR_M = 9_460_730_472_580_800.0
G = 6.67430e-11
C = 299_792_458.0

SOURCE_IMPLEMENTATION = "mission/external_proof/phase.py"
SOURCE_INIT = "mission/external_proof/__init__.py"
SOURCE_ARTIFACT_POLICY = "docs/ARTIFACT_POLICY.md"
SOURCE_GAPS = "docs/research/VALIDATION_AND_QUALIFICATION_GAPS_v1.md"
SOURCE_CAPSULE_DESIGN = "mission/capsule/capsule_design.v1.json"
SOURCE_REVIEW_PACK = "artifacts/external_validation_review_pack.v1.json"
SOURCE_DAG_BOUNDARY = "artifacts/mission_dag_v2_boundary.v1.json"
SOURCE_CAPSULE_RISK = "artifacts/capsule_risk_budget.v1.json"
SOURCE_MISSION_FEASIBILITY = "artifacts/mission_feasibility_screen.v1.json"
SOURCE_MISSION_PROBABILITY = "artifacts/mission_probability_coupling.v1.json"
SOURCE_EVIDENCE_UPGRADE = "artifacts/evidence_upgrade_campaign.v1.json"
SOURCE_PUBLIC_NARRATIVE = "artifacts/public_narrative_hardening.v1.json"
SOURCE_ROADMAP_CLOSURE = "artifacts/roadmap_closure.v1.json"
SOURCE_EXTERNAL_REPRODUCTION_KIT = "artifacts/external_reproduction_kit.v1.json"
SOURCE_EXTERNAL_EVIDENCE_INTAKE = "artifacts/external_evidence_intake.v1.json"
SOURCE_EXTERNAL_VALIDATION_CAMPAIGN = "artifacts/external_validation_campaign.v1.json"

EXTERNAL_LEDGER_SPEC = "mission/EXTERNAL_VALIDATION_EXECUTION_LEDGER_SPEC_v1.md"
PHYSICS_COMPARISON_SPEC = "mission/INDEPENDENT_PHYSICS_BACKEND_COMPARISON_SPEC_v1.md"
CAPSULE_QUALIFICATION_SPEC = "mission/CAPSULE_QUALIFICATION_EVIDENCE_PACK_SPEC_v1.md"
EVIDENCE_CLOSURE_SPEC = "mission/EVIDENCE_UPGRADE_CLOSURE_SPEC_v1.md"
RELEASE_CANDIDATE_SPEC = "mission/RELEASE_CANDIDATE_READINESS_SPEC_v1.md"

EXTERNAL_LEDGER_BUILDER = "scripts/build_external_validation_execution_ledger_artifact.py"
PHYSICS_COMPARISON_BUILDER = "scripts/build_independent_physics_backend_comparison_artifact.py"
CAPSULE_QUALIFICATION_BUILDER = "scripts/build_capsule_qualification_evidence_pack_artifact.py"
EVIDENCE_CLOSURE_BUILDER = "scripts/build_evidence_upgrade_closure_artifact.py"
RELEASE_CANDIDATE_BUILDER = "scripts/build_release_candidate_readiness_artifact.py"

EXTERNAL_LEDGER_VALIDATOR = "scripts/ci/external_validation_execution_ledger_validate.py"
PHYSICS_COMPARISON_VALIDATOR = "scripts/ci/independent_physics_backend_comparison_validate.py"
CAPSULE_QUALIFICATION_VALIDATOR = "scripts/ci/capsule_qualification_evidence_pack_validate.py"
EVIDENCE_CLOSURE_VALIDATOR = "scripts/ci/evidence_upgrade_closure_validate.py"
RELEASE_CANDIDATE_VALIDATOR = "scripts/ci/release_candidate_readiness_validate.py"

EXTERNAL_LEDGER_ARTIFACT = "artifacts/external_validation_execution_ledger.v1.json"
PHYSICS_COMPARISON_ARTIFACT = "artifacts/independent_physics_backend_comparison.v1.json"
CAPSULE_QUALIFICATION_ARTIFACT = "artifacts/capsule_qualification_evidence_pack.v1.json"
EVIDENCE_CLOSURE_ARTIFACT = "artifacts/evidence_upgrade_closure.v1.json"
RELEASE_CANDIDATE_ARTIFACT = "artifacts/release_candidate_readiness.v1.json"

BLOCKED_PROOF_CLAIMS = [
    "external validation completed",
    "third-party validated",
    "independent reproduction completed",
    "independent physics backend validated",
    "cross-backend comparison completed",
    "high-fidelity state trace complete",
    "qualified",
    "certified",
    "flight-ready",
    "source correctness proven",
    "trust grades upgraded automatically",
]


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


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _source_artifacts(repo_root: Path, paths: Sequence[str]) -> List[Dict[str, str]]:
    return [{"path": path, "sha256": _sha256_file(repo_root / path)} for path in paths]


def _source_hash_by_path(payload: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in payload.get("source_artifacts", []):
        if isinstance(item, Mapping) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str):
            out[str(item["path"])] = str(item["sha256"])
    return out


def _validate_sources(
    *,
    repo_root: Path,
    payload: Mapping[str, Any],
    required_paths: Iterable[str],
    errors: List[str],
) -> None:
    expected = set(required_paths)
    by_path = _source_hash_by_path(payload)
    missing = sorted(expected - set(by_path))
    if missing:
        errors.append("source_artifacts missing required paths: " + ", ".join(missing))
    for path in sorted(expected & set(by_path)):
        full = repo_root / path
        if not full.exists():
            errors.append(f"source artifact path does not exist: {path}")
            continue
        if by_path[path] != _sha256_file(full):
            errors.append(f"source_artifacts sha256 mismatch for {path}")


def _determinism_signature(parts: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _relative_error(expected: float, observed: float) -> float:
    denominator = max(abs(expected), 1e-30)
    return abs(float(expected) - float(observed)) / denominator


def _default_feasibility_row(mission_feasibility: Mapping[str, Any]) -> Mapping[str, Any]:
    default_id = mission_feasibility.get("default_scenario_id")
    rows = mission_feasibility.get("scenario_rows", [])
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, Mapping) and row.get("id") == default_id:
                return row
    if isinstance(rows, list):
        for row in rows:
            if (
                isinstance(row, Mapping)
                and row.get("target_id") == "reference-black-hole"
                and row.get("velocity_id") == "conditional-45"
            ):
                return row
    return {}


def _common_source_paths(spec: str, builder: str, validator: str) -> List[str]:
    return [spec, SOURCE_IMPLEMENTATION, SOURCE_INIT, builder, validator, SOURCE_ARTIFACT_POLICY]


def build_external_validation_execution_ledger(repo_root: Path) -> Dict[str, Any]:
    review_pack = _load_json(repo_root / SOURCE_REVIEW_PACK)
    cases = review_pack.get("review_cases", [])
    if not isinstance(cases, list):
        cases = []
    deliverables = review_pack.get("required_external_deliverables", [])
    if not isinstance(deliverables, list):
        deliverables = []

    source_paths = [
        SOURCE_REVIEW_PACK,
        SOURCE_DAG_BOUNDARY,
        SOURCE_EVIDENCE_UPGRADE,
        * _common_source_paths(EXTERNAL_LEDGER_SPEC, EXTERNAL_LEDGER_BUILDER, EXTERNAL_LEDGER_VALIDATOR),
    ]
    execution_cases: List[Dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, Mapping):
            continue
        execution_cases.append(
            {
                "review_case_id": case.get("id"),
                "title": case.get("title"),
                "execution_status": "external_required",
                "external_record_status": "no_external_record_uploaded",
                "source_inputs": case.get("source_inputs", []),
                "external_deliverable_ids": case.get("external_deliverable_ids", []),
                "required_record_schema": {
                    "reviewer_identity": True,
                    "review_date_utc": True,
                    "reviewed_commit_sha": True,
                    "commands_or_tools": True,
                    "raw_outputs_or_report_uri": True,
                    "exceptions_or_disagreements": True,
                    "signature_or_attestation": True,
                },
                "blocked_claims": list(dict.fromkeys(case.get("blocked_claims", []) + BLOCKED_PROOF_CLAIMS))
                if isinstance(case.get("blocked_claims"), list)
                else list(BLOCKED_PROOF_CLAIMS),
            }
        )

    payload: Dict[str, Any] = {
        "schema_version": "external_validation_execution_ledger.v1",
        "generator": EXTERNAL_LEDGER_BUILDER,
        "public_scope": "external_validation_execution_records",
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, source_paths),
        "execution_ledger_status": "repo_native_execution_ledger_ready_external_records_not_uploaded",
        "review_pack_ref": SOURCE_REVIEW_PACK,
        "review_pack_sha256": _sha256_file(repo_root / SOURCE_REVIEW_PACK),
        "required_external_deliverables": deliverables,
        "review_case_count": len(execution_cases),
        "execution_record_count": 0,
        "external_record_count": 0,
        "execution_cases": execution_cases,
        "execution_records": [],
        "acceptance_record_policy": {
            "records_tracked_in_repo_by_default": False,
            "external_records_must_reference_commit_sha": True,
            "external_records_must_preserve_raw_outputs_or_report_uri": True,
            "no_claim_upgrade_without_record": True,
        },
        "rollup": {
            "review_case_count": len(execution_cases),
            "execution_record_count": 0,
            "external_record_count": 0,
            "all_cases_require_external_records": all(
                row["execution_status"] == "external_required" for row in execution_cases
            ),
            "third_party_records_uploaded": False,
            "external_validation_completed": False,
            "independent_reproduction_completed": False,
            "external_red_team_completed": False,
        },
        "blocked_claims": list(BLOCKED_PROOF_CLAIMS),
        "external_evidence_gaps": [
            "signed third-party review records",
            "raw reproduction outputs or immutable report URIs",
            "reviewer exception log",
            "public claim wording audit outside the repository",
        ],
        "interpretation_limits": [
            "This is an execution ledger schema and queue, not a completed review record.",
            "Zero external records are present until a reviewer supplies auditable outputs.",
            "No external validation wording may be unlocked by this artifact alone.",
        ],
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "execution_cases": [
                {
                    "review_case_id": row["review_case_id"],
                    "execution_status": row["execution_status"],
                    "external_record_status": row["external_record_status"],
                }
                for row in execution_cases
            ],
            "rollup": payload["rollup"],
        }
    )
    return payload


def validate_external_validation_execution_ledger(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    required_sources = [
        SOURCE_REVIEW_PACK,
        SOURCE_DAG_BOUNDARY,
        SOURCE_EVIDENCE_UPGRADE,
        *_common_source_paths(EXTERNAL_LEDGER_SPEC, EXTERNAL_LEDGER_BUILDER, EXTERNAL_LEDGER_VALIDATOR),
    ]
    if payload.get("schema_version") != "external_validation_execution_ledger.v1":
        errors.append("schema_version must be external_validation_execution_ledger.v1")
    if payload.get("generator") != EXTERNAL_LEDGER_BUILDER:
        errors.append(f"generator must be {EXTERNAL_LEDGER_BUILDER}")
    if payload.get("public_scope") != "external_validation_execution_records":
        errors.append("public_scope must be external_validation_execution_records")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, required_paths=required_sources, errors=errors)
        if payload.get("review_pack_sha256") != _sha256_file(repo_root / SOURCE_REVIEW_PACK):
            errors.append("review_pack_sha256 mismatch")
    if payload.get("execution_ledger_status") != "repo_native_execution_ledger_ready_external_records_not_uploaded":
        errors.append("execution_ledger_status must keep records not uploaded")
    cases = payload.get("execution_cases")
    if not isinstance(cases, list) or len(cases) != 7:
        errors.append("execution_cases must contain 7 rows")
        cases = []
    if payload.get("review_case_count") != len(cases):
        errors.append("review_case_count must equal len(execution_cases)")
    if payload.get("execution_record_count") != 0:
        errors.append("execution_record_count must be 0")
    if payload.get("external_record_count") != 0:
        errors.append("external_record_count must be 0")
    if payload.get("execution_records") != []:
        errors.append("execution_records must be empty until external records are uploaded")
    for index, row in enumerate(cases):
        if not isinstance(row, Mapping):
            errors.append(f"execution_cases[{index}] must be object")
            continue
        if row.get("execution_status") != "external_required":
            errors.append(f"execution_cases[{index}].execution_status must be external_required")
        if row.get("external_record_status") != "no_external_record_uploaded":
            errors.append(f"execution_cases[{index}].external_record_status must be no_external_record_uploaded")
        if not isinstance(row.get("required_record_schema"), Mapping):
            errors.append(f"execution_cases[{index}].required_record_schema must be object")
        if not isinstance(row.get("blocked_claims"), list) or "external validation completed" not in row["blocked_claims"]:
            errors.append(f"execution_cases[{index}].blocked_claims must block external validation completion")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    for field in (
        "third_party_records_uploaded",
        "external_validation_completed",
        "independent_reproduction_completed",
        "external_red_team_completed",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    if rollup.get("all_cases_require_external_records") is not True:
        errors.append("rollup.all_cases_require_external_records must be true")
    if rollup.get("execution_record_count") != 0:
        errors.append("rollup.execution_record_count must be 0")
    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list):
        errors.append("blocked_claims must be list")
    else:
        for claim in ("external validation completed", "third-party validated", "independent reproduction completed"):
            if claim not in blocked:
                errors.append(f"blocked_claims missing {claim}")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors


def _analytic_check(check_id: str, description: str, expected: float, observed: float, units: str) -> Dict[str, Any]:
    relative = _relative_error(expected, observed)
    return {
        "check_id": check_id,
        "description": description,
        "units": units,
        "analytic_value": _round(expected),
        "artifact_value": _round(observed),
        "absolute_error": _round(abs(expected - observed)),
        "relative_error": _round(relative, 16),
        "status": "match",
    }


def build_independent_physics_backend_comparison(repo_root: Path) -> Dict[str, Any]:
    mission_feasibility = _load_json(repo_root / SOURCE_MISSION_FEASIBILITY)
    capsule_design = _load_json(repo_root / SOURCE_CAPSULE_DESIGN)
    dag_boundary = _load_json(repo_root / SOURCE_DAG_BOUNDARY)
    row = _default_feasibility_row(mission_feasibility)
    source_paths = [
        SOURCE_MISSION_FEASIBILITY,
        SOURCE_CAPSULE_DESIGN,
        SOURCE_DAG_BOUNDARY,
        *_common_source_paths(PHYSICS_COMPARISON_SPEC, PHYSICS_COMPARISON_BUILDER, PHYSICS_COMPARISON_VALIDATOR),
    ]

    velocity_km_s = float(row.get("velocity_km_s", 0.0))
    distance_ly = float(row.get("distance_ly", 0.0))
    velocity_m_s = velocity_km_s * 1000.0
    mass_kg = float(row.get("black_hole_screen", {}).get("mass_kg", 0.0)) if isinstance(row.get("black_hole_screen"), Mapping) else 0.0
    frontal_area = float(capsule_design["survivability_model_inputs"]["frontal_area_m2"]["value"])
    capsule_mass = float(capsule_design["mass_budget"]["configured_capsule_mass_kg"])
    dust = row.get("dust_screen", {}) if isinstance(row.get("dust_screen"), Mapping) else {}
    cost = row.get("cost_energy_proxy", {}) if isinstance(row.get("cost_energy_proxy"), Mapping) else {}
    black_hole = row.get("black_hole_screen", {}) if isinstance(row.get("black_hole_screen"), Mapping) else {}

    checks = [
        _analytic_check(
            "schwarzschild-radius",
            "Analytic Schwarzschild radius from committed black-hole mass.",
            2.0 * G * mass_kg / (C**2),
            float(black_hole.get("schwarzschild_radius_m", 0.0)),
            "m",
        ),
        _analytic_check(
            "ballistic-time-of-flight",
            "Analytic distance / velocity flight time for the default reference black-hole row.",
            distance_ly * LIGHT_YEAR_M / velocity_m_s / YEAR_S,
            float(row.get("flight_years", 0.0)),
            "years",
        ),
        _analytic_check(
            "velocity-fraction-c",
            "Analytic velocity fraction of c for the default row.",
            velocity_m_s / C,
            float(row.get("velocity_fraction_c", 0.0)),
            "fraction",
        ),
        _analytic_check(
            "swept-local-dust-mass",
            "Analytic local dust mass swept by capsule frontal area over the default path.",
            float(dust.get("local_dust_density_kg_m3", 0.0)) * frontal_area * distance_ly * LIGHT_YEAR_M,
            float(dust.get("swept_local_dust_mass_kg", 0.0)),
            "kg",
        ),
        _analytic_check(
            "capsule-kinetic-energy",
            "Analytic capsule kinetic energy at the default velocity using configured capsule mass.",
            0.5 * capsule_mass * (velocity_m_s**2),
            float(cost.get("capsule_kinetic_energy_j", 0.0)),
            "J",
        ),
    ]
    max_relative = max(float(check["relative_error"]) for check in checks)
    dag_rollup = dag_boundary.get("rollup", {}) if isinstance(dag_boundary.get("rollup"), Mapping) else {}
    payload: Dict[str, Any] = {
        "schema_version": "independent_physics_backend_comparison.v1",
        "generator": PHYSICS_COMPARISON_BUILDER,
        "public_scope": "repo_analytic_physics_crosscheck",
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, source_paths),
        "comparison_status": "repo_analytic_crosscheck_ready_external_backend_open",
        "backend_boundary": {
            "repo_analytic_backend_id": "repo_closed_form_physics_crosscheck_v1",
            "external_backend_id": None,
            "external_backend_record_uploaded": False,
            "claim_boundary": "Closed-form repository cross-check only; not an independent high-fidelity physics engine.",
        },
        "default_scenario_ref": row.get("id"),
        "analytic_check_count": len(checks),
        "analytic_checks": checks,
        "dag_boundary_snapshot": {
            "module_count": dag_boundary.get("module_count"),
            "state_trace_contract_complete": dag_rollup.get("state_trace_contract_complete"),
            "independent_backend_complete": dag_rollup.get("independent_backend_complete"),
            "high_fidelity_state_traces_available": dag_rollup.get("high_fidelity_state_traces_available"),
            "cross_backend_comparison_available": dag_rollup.get("cross_backend_comparison_available"),
        },
        "rollup": {
            "analytic_check_count": len(checks),
            "all_repo_analytic_checks_match": all(check["status"] == "match" for check in checks),
            "max_relative_error": _round(max_relative, 16),
            "independent_external_backend_complete": False,
            "cross_backend_comparison_completed": False,
            "high_fidelity_state_trace_complete": False,
            "independent_physics_backend_validated": False,
        },
        "blocked_claims": list(BLOCKED_PROOF_CLAIMS),
        "external_evidence_gaps": [
            "independent backend implementation outside this repository",
            "state trace bundle for each physics module",
            "cross-backend comparison report signed by reviewer",
            "high-fidelity geodesic, dust, radiation, and material transport traces",
        ],
        "interpretation_limits": [
            "Closed-form checks catch gross arithmetic drift but do not validate the physical model.",
            "External backend and high-fidelity state traces remain open proof requirements.",
        ],
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "default_scenario_ref": payload["default_scenario_ref"],
            "analytic_checks": checks,
            "rollup": payload["rollup"],
        }
    )
    return payload


def validate_independent_physics_backend_comparison(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    required_sources = [
        SOURCE_MISSION_FEASIBILITY,
        SOURCE_CAPSULE_DESIGN,
        SOURCE_DAG_BOUNDARY,
        *_common_source_paths(PHYSICS_COMPARISON_SPEC, PHYSICS_COMPARISON_BUILDER, PHYSICS_COMPARISON_VALIDATOR),
    ]
    if payload.get("schema_version") != "independent_physics_backend_comparison.v1":
        errors.append("schema_version must be independent_physics_backend_comparison.v1")
    if payload.get("generator") != PHYSICS_COMPARISON_BUILDER:
        errors.append(f"generator must be {PHYSICS_COMPARISON_BUILDER}")
    if payload.get("comparison_status") != "repo_analytic_crosscheck_ready_external_backend_open":
        errors.append("comparison_status must keep external backend open")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, required_paths=required_sources, errors=errors)
    checks = payload.get("analytic_checks")
    if not isinstance(checks, list) or len(checks) < 4:
        errors.append("analytic_checks must contain at least 4 rows")
        checks = []
    if payload.get("analytic_check_count") != len(checks):
        errors.append("analytic_check_count must equal len(analytic_checks)")
    for index, check in enumerate(checks):
        if not isinstance(check, Mapping):
            errors.append(f"analytic_checks[{index}] must be object")
            continue
        if check.get("status") != "match":
            errors.append(f"analytic_checks[{index}].status must be match")
        if not _is_number(check.get("relative_error")) or float(check["relative_error"]) > 1e-9:
            errors.append(f"analytic_checks[{index}].relative_error must be <= 1e-9")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("all_repo_analytic_checks_match") is not True:
        errors.append("rollup.all_repo_analytic_checks_match must be true")
    if not _is_number(rollup.get("max_relative_error")) or float(rollup.get("max_relative_error", 1.0)) > 1e-9:
        errors.append("rollup.max_relative_error must be <= 1e-9")
    for field in (
        "independent_external_backend_complete",
        "cross_backend_comparison_completed",
        "high_fidelity_state_trace_complete",
        "independent_physics_backend_validated",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list) or "independent physics backend validated" not in blocked:
        errors.append("blocked_claims must block independent physics backend validation")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors


def build_capsule_qualification_evidence_pack(repo_root: Path) -> Dict[str, Any]:
    capsule_design = _load_json(repo_root / SOURCE_CAPSULE_DESIGN)
    capsule_risk = _load_json(repo_root / SOURCE_CAPSULE_RISK)
    source_paths = [
        SOURCE_CAPSULE_DESIGN,
        SOURCE_CAPSULE_RISK,
        SOURCE_GAPS,
        *_common_source_paths(CAPSULE_QUALIFICATION_SPEC, CAPSULE_QUALIFICATION_BUILDER, CAPSULE_QUALIFICATION_VALIDATOR),
    ]
    materials = capsule_design.get("materials", [])
    if not isinstance(materials, list):
        materials = []
    material_by_id = {item.get("material_id"): item for item in materials if isinstance(item, Mapping)}
    layers = capsule_design.get("layers", [])
    if not isinstance(layers, list):
        layers = []
    material_stack = []
    for layer in layers:
        if not isinstance(layer, Mapping):
            continue
        material = material_by_id.get(layer.get("material_id"), {})
        material_stack.append(
            {
                "layer_id": layer.get("layer_id"),
                "radial_order": layer.get("radial_order"),
                "material_id": layer.get("material_id"),
                "material_name": material.get("name") if isinstance(material, Mapping) else None,
                "material_class": material.get("class") if isinstance(material, Mapping) else None,
                "role": layer.get("role"),
                "mass_kg": layer.get("mass_kg"),
                "thickness_m": layer.get("thickness_m"),
                "stand_off_gap_m": layer.get("stand_off_gap_m"),
                "bounds": layer.get("bounds", {}),
                "evidence_status": "design_allocation_not_lab_qualified",
            }
        )
    mass_budget = capsule_design.get("mass_budget", {}) if isinstance(capsule_design.get("mass_budget"), Mapping) else {}
    configured_mass = float(mass_budget.get("configured_capsule_mass_kg", 0.0))
    component_mass = float(mass_budget.get("component_mass_kg", sum(float(layer.get("mass_kg", 0.0)) for layer in material_stack)))
    declared_margin = float(mass_budget.get("declared_margin_kg", 0.0))
    qualification_roadmap = capsule_risk.get("qualification_roadmap", [])
    if not isinstance(qualification_roadmap, list):
        qualification_roadmap = []
    tests = []
    for item in qualification_roadmap:
        if not isinstance(item, Mapping):
            continue
        tests.append(
            {
                "test_id": item.get("id"),
                "track": item.get("track"),
                "status": "external_required",
                "acceptance_criteria": item.get("acceptance_criteria"),
                "closes_failure_modes": item.get("closes_failure_modes", []),
                "required_record_schema": {
                    "test_facility_or_reviewer": True,
                    "test_date_utc": True,
                    "article_or_coupon_configuration": True,
                    "raw_outputs_or_report_uri": True,
                    "pass_fail_or_exception": True,
                },
            }
        )

    payload: Dict[str, Any] = {
        "schema_version": "capsule_qualification_evidence_pack.v1",
        "generator": CAPSULE_QUALIFICATION_BUILDER,
        "public_scope": "capsule_material_stack_qualification_matrix",
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, source_paths),
        "capsule_design": {
            "schema_version": capsule_design.get("schema_version"),
            "design_id": capsule_design.get("design_id"),
            "description": capsule_design.get("description"),
            "governance": capsule_design.get("governance", {}),
        },
        "material_count": len(materials),
        "materials": materials,
        "layer_count": len(material_stack),
        "material_stack": material_stack,
        "mass_closure": {
            "configured_capsule_mass_kg": _round(configured_mass),
            "component_mass_kg": _round(component_mass),
            "declared_margin_kg": _round(declared_margin),
            "absolute_delta_kg": _round(abs(configured_mass - component_mass)),
            "within_declared_margin": abs(configured_mass - component_mass) <= declared_margin,
            "closure_rule": mass_budget.get("closure_rule"),
        },
        "survivability_model_inputs": capsule_design.get("survivability_model_inputs", {}),
        "survivability_uncertainty_bounds": capsule_design.get("survivability_uncertainty_bounds", {}),
        "failure_modes": capsule_risk.get("failure_modes", []),
        "qualification_test_count": len(tests),
        "qualification_tests": tests,
        "lab_record_count": 0,
        "lab_records": [],
        "rollup": {
            "material_count": len(materials),
            "layer_count": len(material_stack),
            "qualification_test_count": len(tests),
            "lab_record_count": 0,
            "mass_budget_closed": abs(configured_mass - component_mass) <= declared_margin,
            "all_tests_external_required": all(test["status"] == "external_required" for test in tests),
            "qualification_complete": False,
            "flight_ready_claimed": False,
            "certified_hardware_survivability": False,
        },
        "blocked_claims": list(BLOCKED_PROOF_CLAIMS),
        "external_evidence_gaps": [
            "stack-level ballistic limit tests",
            "radiation and plasma transport qualification",
            "accelerated archive-media aging tests",
            "bit recovery and ECC readout tests",
            "independent review of targetability and operations assumptions",
        ],
        "interpretation_limits": [
            "The material stack is a design allocation, not tested hardware.",
            "Mass closure is arithmetic only and does not imply qualification.",
            "All qualification tests remain external_required until raw records are attached.",
        ],
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "material_stack": [
                {
                    "layer_id": row["layer_id"],
                    "mass_kg": row.get("mass_kg"),
                    "thickness_m": row.get("thickness_m"),
                }
                for row in material_stack
            ],
            "qualification_tests": [test["test_id"] for test in tests],
            "rollup": payload["rollup"],
        }
    )
    return payload


def validate_capsule_qualification_evidence_pack(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    required_sources = [
        SOURCE_CAPSULE_DESIGN,
        SOURCE_CAPSULE_RISK,
        SOURCE_GAPS,
        *_common_source_paths(CAPSULE_QUALIFICATION_SPEC, CAPSULE_QUALIFICATION_BUILDER, CAPSULE_QUALIFICATION_VALIDATOR),
    ]
    if payload.get("schema_version") != "capsule_qualification_evidence_pack.v1":
        errors.append("schema_version must be capsule_qualification_evidence_pack.v1")
    if payload.get("generator") != CAPSULE_QUALIFICATION_BUILDER:
        errors.append(f"generator must be {CAPSULE_QUALIFICATION_BUILDER}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, required_paths=required_sources, errors=errors)
    design = payload.get("capsule_design")
    if not isinstance(design, Mapping) or design.get("design_id") != "interstellar_archive_capsule_v1":
        errors.append("capsule_design.design_id must be interstellar_archive_capsule_v1")
    mass = payload.get("mass_closure")
    if not isinstance(mass, Mapping):
        errors.append("mass_closure must be object")
        mass = {}
    if mass.get("within_declared_margin") is not True:
        errors.append("mass_closure.within_declared_margin must be true")
    if mass.get("configured_capsule_mass_kg") != 206.0:
        errors.append("mass_closure.configured_capsule_mass_kg must be 206.0")
    if mass.get("component_mass_kg") != 206.0:
        errors.append("mass_closure.component_mass_kg must be 206.0")
    materials = payload.get("materials")
    if not isinstance(materials, list) or len(materials) < 6:
        errors.append("materials must contain at least 6 entries")
        materials = []
    stack = payload.get("material_stack")
    if not isinstance(stack, list) or len(stack) < 6:
        errors.append("material_stack must contain at least 6 entries")
        stack = []
    if payload.get("material_count") != len(materials):
        errors.append("material_count must equal len(materials)")
    if payload.get("layer_count") != len(stack):
        errors.append("layer_count must equal len(material_stack)")
    tests = payload.get("qualification_tests")
    if not isinstance(tests, list) or len(tests) < 6:
        errors.append("qualification_tests must contain at least 6 entries")
        tests = []
    if payload.get("qualification_test_count") != len(tests):
        errors.append("qualification_test_count must equal len(qualification_tests)")
    for index, test in enumerate(tests):
        if not isinstance(test, Mapping):
            errors.append(f"qualification_tests[{index}] must be object")
            continue
        if test.get("status") != "external_required":
            errors.append(f"qualification_tests[{index}].status must be external_required")
        if not isinstance(test.get("required_record_schema"), Mapping):
            errors.append(f"qualification_tests[{index}].required_record_schema must be object")
    if payload.get("lab_record_count") != 0:
        errors.append("lab_record_count must be 0")
    if payload.get("lab_records") != []:
        errors.append("lab_records must be empty until lab evidence is attached")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("mass_budget_closed") is not True:
        errors.append("rollup.mass_budget_closed must be true")
    if rollup.get("all_tests_external_required") is not True:
        errors.append("rollup.all_tests_external_required must be true")
    for field in ("qualification_complete", "flight_ready_claimed", "certified_hardware_survivability"):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list) or "qualified" not in blocked:
        errors.append("blocked_claims must include qualified")
    if isinstance(blocked, list) and "flight-ready" not in blocked:
        errors.append("blocked_claims must include flight-ready")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors


def _evidence_closure_status(row: Mapping[str, Any]) -> str:
    if row.get("target_trust_grade") == "keep_speculative_isolated" or row.get("mode") == "speculative":
        return "speculative_quarantined"
    return "external_required"


def build_evidence_upgrade_closure(repo_root: Path) -> Dict[str, Any]:
    evidence_upgrade = _load_json(repo_root / SOURCE_EVIDENCE_UPGRADE)
    source_paths = [
        SOURCE_EVIDENCE_UPGRADE,
        SOURCE_REVIEW_PACK,
        *_common_source_paths(EVIDENCE_CLOSURE_SPEC, EVIDENCE_CLOSURE_BUILDER, EVIDENCE_CLOSURE_VALIDATOR),
    ]
    top_priorities = evidence_upgrade.get("top_priorities", [])
    if not isinstance(top_priorities, list):
        top_priorities = []
    rows: List[Dict[str, Any]] = []
    for item in top_priorities[:15]:
        if not isinstance(item, Mapping):
            continue
        status = _evidence_closure_status(item)
        rows.append(
            {
                "campaign_id": item.get("campaign_id"),
                "parameter_id": item.get("parameter_id"),
                "current_trust_grade": item.get("current_trust_grade"),
                "target_trust_grade": item.get("target_trust_grade"),
                "mode": item.get("mode"),
                "priority_score": item.get("priority_score"),
                "gap_types": item.get("gap_types", []),
                "source_quality_gaps": item.get("source_quality_gaps", []),
                "recommended_actions": item.get("recommended_actions", []),
                "acceptance_criteria": item.get("acceptance_criteria", []),
                "closure_status": status,
                "closure_decision": (
                    "kept out of realistic proof surfaces until source-backed physics replaces speculative control"
                    if status == "speculative_quarantined"
                    else "external evidence required before trust-grade or source-correctness claims can change"
                ),
                "trust_grade_promoted": False,
                "source_correctness_claimed": False,
                "external_source_upgrade_record_uploaded": False,
                "blocked_claims": item.get("blocked_claims", []),
            }
        )

    speculative_count = sum(1 for row in rows if row["closure_status"] == "speculative_quarantined")
    external_required_count = sum(1 for row in rows if row["closure_status"] == "external_required")
    payload: Dict[str, Any] = {
        "schema_version": "evidence_upgrade_closure.v1",
        "generator": EVIDENCE_CLOSURE_BUILDER,
        "public_scope": "evidence_upgrade_first_closure_cycle",
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, source_paths),
        "campaign_ref": SOURCE_EVIDENCE_UPGRADE,
        "closure_status": "first_cycle_recorded_external_source_upgrades_open",
        "closure_cycle_count": len(rows),
        "closure_rows": rows,
        "rollup": {
            "closure_cycle_count": len(rows),
            "speculative_quarantine_count": speculative_count,
            "external_required_count": external_required_count,
            "external_source_upgrade_count": 0,
            "trust_grade_promotion_count": 0,
            "source_correctness_claimed": False,
            "trust_grades_upgraded_automatically": False,
            "realistic_D_grade_public_rows_closed": 0,
        },
        "blocked_claims": [
            "trust grades upgraded automatically",
            "source correctness proven",
            "automatic trust promotion",
            "assumption treated as measured evidence",
            "certified or flight-ready evidence closure",
        ],
        "external_evidence_gaps": evidence_upgrade.get("external_evidence_gaps", []),
        "interpretation_limits": [
            "This artifact records the first closure cycle; it does not add new sources.",
            "Trust grades remain unchanged until evidence registries, derivation notes, and validators prove an upgrade.",
            "Speculative controls are quarantined rather than promoted.",
        ],
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "closure_rows": [
                {
                    "parameter_id": row["parameter_id"],
                    "closure_status": row["closure_status"],
                    "trust_grade_promoted": row["trust_grade_promoted"],
                }
                for row in rows
            ],
            "rollup": payload["rollup"],
        }
    )
    return payload


def validate_evidence_upgrade_closure(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    required_sources = [
        SOURCE_EVIDENCE_UPGRADE,
        SOURCE_REVIEW_PACK,
        *_common_source_paths(EVIDENCE_CLOSURE_SPEC, EVIDENCE_CLOSURE_BUILDER, EVIDENCE_CLOSURE_VALIDATOR),
    ]
    if payload.get("schema_version") != "evidence_upgrade_closure.v1":
        errors.append("schema_version must be evidence_upgrade_closure.v1")
    if payload.get("generator") != EVIDENCE_CLOSURE_BUILDER:
        errors.append(f"generator must be {EVIDENCE_CLOSURE_BUILDER}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, required_paths=required_sources, errors=errors)
    rows = payload.get("closure_rows")
    if not isinstance(rows, list) or len(rows) != 15:
        errors.append("closure_rows must contain 15 rows")
        rows = []
    if payload.get("closure_cycle_count") != len(rows):
        errors.append("closure_cycle_count must equal len(closure_rows)")
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"closure_rows[{index}] must be object")
            continue
        if row.get("closure_status") not in {"external_required", "speculative_quarantined"}:
            errors.append(f"closure_rows[{index}].closure_status invalid")
        if row.get("trust_grade_promoted") is not False:
            errors.append(f"closure_rows[{index}].trust_grade_promoted must be false")
        if row.get("source_correctness_claimed") is not False:
            errors.append(f"closure_rows[{index}].source_correctness_claimed must be false")
        if row.get("external_source_upgrade_record_uploaded") is not False:
            errors.append(f"closure_rows[{index}].external_source_upgrade_record_uploaded must be false")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("closure_cycle_count") != len(rows):
        errors.append("rollup.closure_cycle_count mismatch")
    for field in ("external_source_upgrade_count", "trust_grade_promotion_count", "realistic_D_grade_public_rows_closed"):
        if rollup.get(field) != 0:
            errors.append(f"rollup.{field} must be 0")
    for field in ("source_correctness_claimed", "trust_grades_upgraded_automatically"):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list) or "trust grades upgraded automatically" not in blocked:
        errors.append("blocked_claims must block automatic trust upgrades")
    if isinstance(blocked, list) and "source correctness proven" not in blocked:
        errors.append("blocked_claims must block source correctness proof")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors


def _release_component_rollup(name: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    rollup = payload.get("rollup", {}) if isinstance(payload.get("rollup"), Mapping) else {}
    return {
        "schema_version": payload.get("schema_version"),
        "artifact_ref": {
            "external_validation_execution_ledger.v1": EXTERNAL_LEDGER_ARTIFACT,
            "independent_physics_backend_comparison.v1": PHYSICS_COMPARISON_ARTIFACT,
            "capsule_qualification_evidence_pack.v1": CAPSULE_QUALIFICATION_ARTIFACT,
            "evidence_upgrade_closure.v1": EVIDENCE_CLOSURE_ARTIFACT,
            "external_reproduction_kit.v1": SOURCE_EXTERNAL_REPRODUCTION_KIT,
            "external_evidence_intake.v1": SOURCE_EXTERNAL_EVIDENCE_INTAKE,
            "external_validation_campaign.v1": SOURCE_EXTERNAL_VALIDATION_CAMPAIGN,
        }.get(str(payload.get("schema_version")), name),
        "non_certification_notice": payload.get("non_certification_notice"),
        "rollup": rollup,
    }


def build_release_candidate_readiness(repo_root: Path) -> Dict[str, Any]:
    external_ledger = _load_json(repo_root / EXTERNAL_LEDGER_ARTIFACT)
    physics_comparison = _load_json(repo_root / PHYSICS_COMPARISON_ARTIFACT)
    capsule_qualification = _load_json(repo_root / CAPSULE_QUALIFICATION_ARTIFACT)
    evidence_closure = _load_json(repo_root / EVIDENCE_CLOSURE_ARTIFACT)
    external_reproduction_kit = _load_json(repo_root / SOURCE_EXTERNAL_REPRODUCTION_KIT)
    external_evidence_intake = _load_json(repo_root / SOURCE_EXTERNAL_EVIDENCE_INTAKE)
    external_validation_campaign = _load_json(repo_root / SOURCE_EXTERNAL_VALIDATION_CAMPAIGN)
    public_narrative = _load_json(repo_root / SOURCE_PUBLIC_NARRATIVE)
    roadmap_closure = _load_json(repo_root / SOURCE_ROADMAP_CLOSURE)
    review_pack = _load_json(repo_root / SOURCE_REVIEW_PACK)
    source_paths = [
        EXTERNAL_LEDGER_ARTIFACT,
        PHYSICS_COMPARISON_ARTIFACT,
        CAPSULE_QUALIFICATION_ARTIFACT,
        EVIDENCE_CLOSURE_ARTIFACT,
        SOURCE_EXTERNAL_REPRODUCTION_KIT,
        SOURCE_EXTERNAL_EVIDENCE_INTAKE,
        SOURCE_EXTERNAL_VALIDATION_CAMPAIGN,
        SOURCE_PUBLIC_NARRATIVE,
        SOURCE_ROADMAP_CLOSURE,
        SOURCE_REVIEW_PACK,
        *_common_source_paths(RELEASE_CANDIDATE_SPEC, RELEASE_CANDIDATE_BUILDER, RELEASE_CANDIDATE_VALIDATOR),
    ]
    component_rollups = {
        "external_validation_execution_ledger": _release_component_rollup(
            EXTERNAL_LEDGER_ARTIFACT,
            external_ledger,
        ),
        "independent_physics_backend_comparison": _release_component_rollup(
            PHYSICS_COMPARISON_ARTIFACT,
            physics_comparison,
        ),
        "capsule_qualification_evidence_pack": _release_component_rollup(
            CAPSULE_QUALIFICATION_ARTIFACT,
            capsule_qualification,
        ),
        "evidence_upgrade_closure": _release_component_rollup(
            EVIDENCE_CLOSURE_ARTIFACT,
            evidence_closure,
        ),
        "external_reproduction_kit": _release_component_rollup(
            SOURCE_EXTERNAL_REPRODUCTION_KIT,
            external_reproduction_kit,
        ),
        "external_evidence_intake": _release_component_rollup(
            SOURCE_EXTERNAL_EVIDENCE_INTAKE,
            external_evidence_intake,
        ),
        "external_validation_campaign": _release_component_rollup(
            SOURCE_EXTERNAL_VALIDATION_CAMPAIGN,
            external_validation_campaign,
        ),
        "public_narrative_hardening": {
            "schema_version": public_narrative.get("schema_version"),
            "artifact_ref": SOURCE_PUBLIC_NARRATIVE,
            "rollup": public_narrative.get("rollup", {}),
        },
        "roadmap_closure": {
            "schema_version": roadmap_closure.get("schema_version"),
            "artifact_ref": SOURCE_ROADMAP_CLOSURE,
            "closure_metrics": roadmap_closure.get("closure_metrics", {}),
        },
        "external_validation_review_pack": {
            "schema_version": review_pack.get("schema_version"),
            "artifact_ref": SOURCE_REVIEW_PACK,
            "review_pack_status": review_pack.get("review_pack_status"),
            "rollup": review_pack.get("rollup", {}),
        },
    }
    payload: Dict[str, Any] = {
        "schema_version": "release_candidate_readiness.v1",
        "generator": RELEASE_CANDIDATE_BUILDER,
        "public_scope": "repo_publication_readiness_external_evidence_boundary",
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, source_paths),
        "release_candidate_status": "repo_publication_candidate_external_evidence_open",
        "component_rollups": component_rollups,
        "repository_gates": [
            {
                "gate_id": "repo_artifacts_deterministic",
                "status": "ready",
                "evidence": "All component artifacts are deterministic JSON generated by tracked builders.",
            },
            {
                "gate_id": "public_claim_boundary",
                "status": "ready",
                "evidence": SOURCE_PUBLIC_NARRATIVE,
            },
            {
                "gate_id": "external_validation_records",
                "status": "external_required",
                "evidence": SOURCE_EXTERNAL_EVIDENCE_INTAKE,
            },
            {
                "gate_id": "external_validation_campaign_execution",
                "status": "external_required",
                "evidence": SOURCE_EXTERNAL_VALIDATION_CAMPAIGN,
            },
            {
                "gate_id": "external_reproduction_pack",
                "status": "ready",
                "evidence": SOURCE_EXTERNAL_REPRODUCTION_KIT,
            },
            {
                "gate_id": "capsule_qualification_records",
                "status": "external_required",
                "evidence": CAPSULE_QUALIFICATION_ARTIFACT,
            },
            {
                "gate_id": "independent_backend_records",
                "status": "external_required",
                "evidence": PHYSICS_COMPARISON_ARTIFACT,
            },
        ],
        "rollup": {
            "repo_publication_candidate_ready": True,
            "certification_go": False,
            "flight_readiness_go": False,
            "external_validation_completed": False,
            "qualification_complete": False,
            "independent_backend_validated": False,
            "trust_grade_promotions_completed": False,
            "public_claim_boundary_ready": True,
        },
        "blocked_claims": list(BLOCKED_PROOF_CLAIMS),
        "external_evidence_gaps": [
            "third-party validation records",
            "first accepted external evidence intake record",
            "six-workstream external validation campaign execution",
            "independent physics backend report",
            "capsule qualification and lab test records",
            "evidence source upgrade records",
            "certification, launch, legal, and operations approvals",
        ],
        "interpretation_limits": [
            "Ready here means repository publication candidate, not mission approval.",
            "Certification, flight readiness, external validation, and source correctness remain blocked.",
            "This artifact is a release-readiness index over tracked evidence boundaries.",
        ],
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "component_schemas": {
                key: value.get("schema_version")
                for key, value in component_rollups.items()
                if isinstance(value, Mapping)
            },
            "rollup": payload["rollup"],
        }
    )
    return payload


def validate_release_candidate_readiness(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    required_sources = [
        EXTERNAL_LEDGER_ARTIFACT,
        PHYSICS_COMPARISON_ARTIFACT,
        CAPSULE_QUALIFICATION_ARTIFACT,
        EVIDENCE_CLOSURE_ARTIFACT,
        SOURCE_EXTERNAL_REPRODUCTION_KIT,
        SOURCE_EXTERNAL_EVIDENCE_INTAKE,
        SOURCE_EXTERNAL_VALIDATION_CAMPAIGN,
        SOURCE_PUBLIC_NARRATIVE,
        SOURCE_ROADMAP_CLOSURE,
        SOURCE_REVIEW_PACK,
        *_common_source_paths(RELEASE_CANDIDATE_SPEC, RELEASE_CANDIDATE_BUILDER, RELEASE_CANDIDATE_VALIDATOR),
    ]
    if payload.get("schema_version") != "release_candidate_readiness.v1":
        errors.append("schema_version must be release_candidate_readiness.v1")
    if payload.get("generator") != RELEASE_CANDIDATE_BUILDER:
        errors.append(f"generator must be {RELEASE_CANDIDATE_BUILDER}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("release_candidate_status") != "repo_publication_candidate_external_evidence_open":
        errors.append("release_candidate_status must keep external evidence open")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, required_paths=required_sources, errors=errors)
    components = payload.get("component_rollups")
    if not isinstance(components, Mapping):
        errors.append("component_rollups must be object")
        components = {}
    for key in (
        "external_validation_execution_ledger",
        "independent_physics_backend_comparison",
        "capsule_qualification_evidence_pack",
        "evidence_upgrade_closure",
        "external_reproduction_kit",
        "external_evidence_intake",
        "external_validation_campaign",
    ):
        if key not in components:
            errors.append(f"component_rollups missing {key}")
    gates = payload.get("repository_gates")
    if not isinstance(gates, list) or len(gates) < 5:
        errors.append("repository_gates must contain at least 5 gates")
    else:
        external_gate_count = sum(1 for gate in gates if isinstance(gate, Mapping) and gate.get("status") == "external_required")
        if external_gate_count < 3:
            errors.append("repository_gates must keep external proof gates external_required")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("repo_publication_candidate_ready") is not True:
        errors.append("rollup.repo_publication_candidate_ready must be true")
    for field in (
        "certification_go",
        "flight_readiness_go",
        "external_validation_completed",
        "qualification_complete",
        "independent_backend_validated",
        "trust_grade_promotions_completed",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list) or "certified" not in blocked:
        errors.append("blocked_claims must block certified")
    if isinstance(blocked, list) and "flight-ready" not in blocked:
        errors.append("blocked_claims must block flight-ready")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors
