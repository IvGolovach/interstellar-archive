#!/usr/bin/env python3
"""Build a consolidated browser-facing dataset from tracked deterministic artifacts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Mapping

try:
    from .script_io import load_json, render_json, write_json
except ImportError:
    from script_io import load_json, render_json, write_json


DEFAULT_DETERMINISM_STATUS = Path("artifacts/determinism_status.json")
DEFAULT_FAILURE_SURFACE = Path("artifacts/failure_surface_baseline.v1.json")
DEFAULT_MANIFEST = Path("artifacts/parameter_drilldown_manifest.json")
DEFAULT_STATIC_GRAPH = Path("artifacts/parameter_static_usage_graph.json")
DEFAULT_EVIDENCE_INDEX = Path("artifacts/parameter_evidence_index.json")
DEFAULT_P_SUCCESS_DEFENSIBILITY = Path("artifacts/p_success_defensibility.json")
DEFAULT_OBJECTIVE_SCORE = Path("artifacts/objective_score_baseline.v1.json")
DEFAULT_OPTIMIZATION_SEARCH_SPACE = Path("artifacts/optimization_search_space.v1.json")
DEFAULT_OPTIMIZATION_FRONTIER = Path("artifacts/optimization_frontier_realistic.v1.json")
DEFAULT_OPTIMIZATION_V2 = Path("artifacts/optimization_v2_frontier.v1.json")
DEFAULT_CAPSULE_SURVIVABILITY = Path("artifacts/capsule_survivability_lab.v1.json")
DEFAULT_CAPSULE_RISK_BUDGET = Path("artifacts/capsule_risk_budget.v1.json")
DEFAULT_MISSION_FEASIBILITY = Path("artifacts/mission_feasibility_screen.v1.json")
DEFAULT_USER_MISSION_RUN_CATALOG = Path("artifacts/user_mission_run_catalog.v1.json")
DEFAULT_RUNTIME_SCENARIO_GENERATION = Path("artifacts/runtime_scenario_generation.v1.json")
DEFAULT_COST_PROCUREMENT_ARCHITECTURE = Path("artifacts/cost_procurement_architecture_feasibility.v1.json")
DEFAULT_EXTERNAL_VALIDATION_REVIEW_PACK = Path("artifacts/external_validation_review_pack.v1.json")
DEFAULT_PUBLIC_NARRATIVE_HARDENING = Path("artifacts/public_narrative_hardening.v1.json")
DEFAULT_EXTERNAL_VALIDATION_EXECUTION_LEDGER = Path("artifacts/external_validation_execution_ledger.v1.json")
DEFAULT_INDEPENDENT_PHYSICS_BACKEND_COMPARISON = Path("artifacts/independent_physics_backend_comparison.v1.json")
DEFAULT_CAPSULE_QUALIFICATION_EVIDENCE_PACK = Path("artifacts/capsule_qualification_evidence_pack.v1.json")
DEFAULT_EVIDENCE_UPGRADE_CLOSURE = Path("artifacts/evidence_upgrade_closure.v1.json")
DEFAULT_EXTERNAL_REPRODUCTION_KIT = Path("artifacts/external_reproduction_kit.v1.json")
DEFAULT_EXTERNAL_EVIDENCE_INTAKE = Path("artifacts/external_evidence_intake.v1.json")
DEFAULT_EXTERNAL_VALIDATION_CAMPAIGN = Path("artifacts/external_validation_campaign.v1.json")
DEFAULT_RELEASE_CANDIDATE_READINESS = Path("artifacts/release_candidate_readiness.v1.json")
DEFAULT_MISSION_PROBABILITY_COUPLING = Path("artifacts/mission_probability_coupling.v1.json")
DEFAULT_UNCERTAINTY_INTERACTIONS = Path("artifacts/uncertainty_interactions.v1.json")
DEFAULT_EVIDENCE_UPGRADE_CAMPAIGN = Path("artifacts/evidence_upgrade_campaign.v1.json")
DEFAULT_MISSION_DAG_V2_BOUNDARY = Path("artifacts/mission_dag_v2_boundary.v1.json")
DEFAULT_ROADMAP_CLOSURE = Path("artifacts/roadmap_closure.v1.json")
DEFAULT_PARAMETER_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_OUTPUT = Path("artifacts/browser_dataset.v1.json")

PUBLIC_DATASET_PATHS = {
    "determinismStatus": str(DEFAULT_DETERMINISM_STATUS),
    "failureSurfaceBaseline": str(DEFAULT_FAILURE_SURFACE),
    "parameterDrilldownManifest": str(DEFAULT_MANIFEST),
    "parameterStaticUsageGraph": str(DEFAULT_STATIC_GRAPH),
    "parameterEvidenceIndex": str(DEFAULT_EVIDENCE_INDEX),
    "pSuccessDefensibility": str(DEFAULT_P_SUCCESS_DEFENSIBILITY),
    "objectiveContract": "mission/objectives/objective_contract.v1.json",
    "objectiveScoreBaseline": str(DEFAULT_OBJECTIVE_SCORE),
    "optimizationSearchSpace": str(DEFAULT_OPTIMIZATION_SEARCH_SPACE),
    "optimizationFrontier": str(DEFAULT_OPTIMIZATION_FRONTIER),
    "optimizationV2": str(DEFAULT_OPTIMIZATION_V2),
    "capsuleSurvivabilityLab": str(DEFAULT_CAPSULE_SURVIVABILITY),
    "capsuleRiskBudget": str(DEFAULT_CAPSULE_RISK_BUDGET),
    "missionFeasibilityScreen": str(DEFAULT_MISSION_FEASIBILITY),
    "userMissionRunCatalog": str(DEFAULT_USER_MISSION_RUN_CATALOG),
    "runtimeScenarioGeneration": str(DEFAULT_RUNTIME_SCENARIO_GENERATION),
    "costProcurementArchitectureFeasibility": str(DEFAULT_COST_PROCUREMENT_ARCHITECTURE),
    "externalValidationReviewPack": str(DEFAULT_EXTERNAL_VALIDATION_REVIEW_PACK),
    "publicNarrativeHardening": str(DEFAULT_PUBLIC_NARRATIVE_HARDENING),
    "externalValidationExecutionLedger": str(DEFAULT_EXTERNAL_VALIDATION_EXECUTION_LEDGER),
    "independentPhysicsBackendComparison": str(DEFAULT_INDEPENDENT_PHYSICS_BACKEND_COMPARISON),
    "capsuleQualificationEvidencePack": str(DEFAULT_CAPSULE_QUALIFICATION_EVIDENCE_PACK),
    "evidenceUpgradeClosure": str(DEFAULT_EVIDENCE_UPGRADE_CLOSURE),
    "externalReproductionKit": str(DEFAULT_EXTERNAL_REPRODUCTION_KIT),
    "externalEvidenceIntake": str(DEFAULT_EXTERNAL_EVIDENCE_INTAKE),
    "externalValidationCampaign": str(DEFAULT_EXTERNAL_VALIDATION_CAMPAIGN),
    "releaseCandidateReadiness": str(DEFAULT_RELEASE_CANDIDATE_READINESS),
    "missionProbabilityCoupling": str(DEFAULT_MISSION_PROBABILITY_COUPLING),
    "uncertaintyInteractions": str(DEFAULT_UNCERTAINTY_INTERACTIONS),
    "evidenceUpgradeCampaign": str(DEFAULT_EVIDENCE_UPGRADE_CAMPAIGN),
    "missionDagV2Boundary": str(DEFAULT_MISSION_DAG_V2_BOUNDARY),
    "roadmapClosure": str(DEFAULT_ROADMAP_CLOSURE),
}

INTERNAL_PARAMETER_PREFIXES = ("code_literal.",)
PUBLIC_VISIBILITY = "public"
PUBLIC_SURFACE_BROWSER = "browser"
PUBLIC_SURFACE_OPTIMIZATION = "optimization"
MANIFEST_PUBLIC_SCOPE = "public_mission_parameters_only"
MANIFEST_UI_SCOPE = "mission_design_environment_only"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_object(value: Any) -> bool:
    return isinstance(value, Mapping)


def _is_internal_parameter_id(parameter_id: str) -> bool:
    return any(parameter_id.startswith(prefix) for prefix in INTERNAL_PARAMETER_PREFIXES)


def _public_surfaces(parameter: Mapping[str, Any]) -> set[str]:
    surfaces = parameter.get("public_surfaces")
    if not isinstance(surfaces, list):
        return set()
    return {str(surface) for surface in surfaces if isinstance(surface, str)}


def _has_visibility_metadata(parameter: Mapping[str, Any]) -> bool:
    return "visibility" in parameter or "public_surfaces" in parameter or "audit_scope" in parameter


def _allows_public_surface(parameter: Mapping[str, Any], surface: str) -> bool:
    parameter_id = parameter.get("parameter_id")
    if isinstance(parameter_id, str) and _is_internal_parameter_id(parameter_id):
        return False
    if not _has_visibility_metadata(parameter):
        return True
    return parameter.get("visibility") == PUBLIC_VISIBILITY and surface in _public_surfaces(parameter)


def _registry_by_id(repo_root: Path | None) -> Dict[str, Mapping[str, Any]]:
    if repo_root is None:
        return {}
    registry_path = repo_root / DEFAULT_PARAMETER_REGISTRY
    if not registry_path.exists():
        return {}
    registry = load_json(registry_path)
    return {
        str(item["parameter_id"]): item
        for item in registry.get("parameters", [])
        if isinstance(item, Mapping) and isinstance(item.get("parameter_id"), str)
    }


def _capsule_risk_budget_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    risk_budgets = payload.get("risk_budgets", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "source_artifact_ref": payload.get("source_artifact_ref"),
        "source_artifact_sha256": payload.get("source_artifact_sha256"),
        "sample_count": payload.get("sample_count"),
        "seed": payload.get("seed"),
        "sampling_method": payload.get("sampling_method"),
        "default_row_id": payload.get("default_row_id"),
        "risk_budget_count": payload.get("risk_budget_count", len(risk_budgets) if isinstance(risk_budgets, list) else 0),
        "source_policy": payload.get("source_policy"),
        "failure_modes": payload.get("failure_modes", []),
        "qualification_roadmap": payload.get("qualification_roadmap", []),
        "attack_modes": payload.get("attack_modes"),
        "uncertainty_dimensions": payload.get("uncertainty_dimensions", []),
    }


def _roadmap_closure_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    items = payload.get("roadmap_items", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "roadmap_item_count": payload.get("roadmap_item_count"),
        "closure_metrics": payload.get("closure_metrics", {}),
        "roadmap_items": items if isinstance(items, list) else [],
        "model_summaries": payload.get("model_summaries", {}),
        "qualification_tracks": payload.get("qualification_tracks", {}),
        "runtime_runs": payload.get("runtime_runs", {}),
        "review_pack": payload.get("review_pack", {}),
        "public_narrative": payload.get("public_narrative", {}),
    }


def _mission_feasibility_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = payload.get("scenario_rows", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "target_count": payload.get("target_count"),
        "velocity_count": payload.get("velocity_count"),
        "scenario_count": payload.get("scenario_count"),
        "default_scenario_id": payload.get("default_scenario_id"),
        "default_black_hole_flight_years": payload.get("default_black_hole_flight_years"),
        "capsule_risk_budget_match_count": payload.get("capsule_risk_budget_match_count"),
        "constants": payload.get("constants", {}),
        "scenario_rows": rows if isinstance(rows, list) else [],
        "interpretation_limits": payload.get("interpretation_limits", []),
    }


def _user_mission_run_catalog_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = payload.get("run_rows", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "run_store_policy": payload.get("run_store_policy", {}),
        "target_count": payload.get("target_count"),
        "velocity_count": payload.get("velocity_count"),
        "run_count": payload.get("run_count"),
        "default_run_id": payload.get("default_run_id"),
        "target_ids": payload.get("target_ids", []),
        "velocity_ids": payload.get("velocity_ids", []),
        "run_rows": rows if isinstance(rows, list) else [],
        "interpretation_limits": payload.get("interpretation_limits", []),
    }


def _runtime_scenario_generation_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = payload.get("generation_rows", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "selection_axes": payload.get("selection_axes", {}),
        "scenario_generation_contract": payload.get("scenario_generation_contract", {}),
        "run_pack_contract": payload.get("run_pack_contract", {}),
        "generation_row_count": payload.get("generation_row_count"),
        "generation_rows": rows if isinstance(rows, list) else [],
        "rollup": payload.get("rollup", {}),
        "blocked_claims": payload.get("blocked_claims", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
    }


def _cost_procurement_architecture_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = payload.get("architecture_rows", [])
    if not isinstance(rows, list):
        rows = []
    rows = [row for row in rows if isinstance(row, Mapping)]
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "roadmap_item": payload.get("roadmap_item", {}),
        "claim_boundaries": payload.get("claim_boundaries", {}),
        "mass_budget": payload.get("mass_budget", {}),
        "cost_model": payload.get("cost_model", {}),
        "procurement_gates": payload.get("procurement_gates", []),
        "architecture_row_count": payload.get("architecture_row_count"),
        "architecture_rows": rows,
        "architecture_options": payload.get("architecture_options", []),
        "optimization_cost_axis": payload.get("optimization_cost_axis", {}),
        "rollup": payload.get("rollup", {}),
        "blocked_claims": payload.get("blocked_claims", []),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
    }


def _mission_probability_coupling_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = payload.get("coupling_rows", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "formula": payload.get("formula"),
        "factor_policy": payload.get("factor_policy", {}),
        "coupling_count": payload.get("coupling_count"),
        "default_coupling_id": payload.get("default_coupling_id"),
        "default_run_id": payload.get("default_run_id"),
        "coupling_rows": rows if isinstance(rows, list) else [],
        "rollup": payload.get("rollup", {}),
        "interpretation_limits": payload.get("interpretation_limits", []),
    }


def _uncertainty_interactions_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    main_effects = payload.get("main_effects", [])
    pair_interactions = payload.get("pair_interactions", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "mode": payload.get("mode"),
        "method": payload.get("method", {}),
        "baseline": payload.get("baseline", {}),
        "uncertainty_entry_count": payload.get("uncertainty_entry_count"),
        "interaction_pair_count": payload.get("interaction_pair_count"),
        "main_effects": main_effects if isinstance(main_effects, list) else [],
        "pair_interactions": pair_interactions if isinstance(pair_interactions, list) else [],
        "rollup": payload.get("rollup", {}),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "blocked_claims": payload.get("blocked_claims", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
    }


def _evidence_upgrade_campaign_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    public_rows = payload.get("public_campaign_rows", [])
    if not isinstance(public_rows, list):
        public_rows = []
    public_rows = [row for row in public_rows if isinstance(row, Mapping)]
    top_public_rows = sorted(
        public_rows,
        key=lambda row: (-float(row.get("priority_score", 0.0)), str(row.get("parameter_id", ""))),
    )[:15]
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "campaign_policy": payload.get("campaign_policy", {}),
        "claim_count": payload.get("claim_count"),
        "public_campaign_count": payload.get("public_campaign_count"),
        "internal_audit_count": payload.get("internal_audit_count"),
        "trust_distribution": payload.get("trust_distribution", {}),
        "public_trust_distribution": payload.get("public_trust_distribution", {}),
        "source_type_distribution": payload.get("source_type_distribution", {}),
        "top_priority_count": payload.get("top_priority_count"),
        "public_top_priorities": top_public_rows,
        "internal_audit_rollup": payload.get("internal_audit_rollup", {}),
        "rollup": payload.get("rollup", {}),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "blocked_claims": payload.get("blocked_claims", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
    }


def _optimization_v2_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    candidates = payload.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    candidates = [candidate for candidate in candidates if isinstance(candidate, Mapping)]
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "mode": payload.get("mode"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "axis_contract": payload.get("axis_contract", {}),
        "candidate_count": payload.get("candidate_count"),
        "frontier_candidate_count": payload.get("frontier_candidate_count"),
        "candidates": candidates,
        "pareto_frontier_candidate_ids": payload.get("pareto_frontier_candidate_ids", []),
        "rollup": payload.get("rollup", {}),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "blocked_claims": payload.get("blocked_claims", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def _mission_dag_v2_boundary_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = payload.get("module_boundaries", [])
    if not isinstance(rows, list):
        rows = []
    rows = [row for row in rows if isinstance(row, Mapping)]
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "module_count": payload.get("module_count"),
        "registry_version": payload.get("registry_version"),
        "scenario_ref": payload.get("scenario_ref"),
        "failure_taxonomy_ref": payload.get("failure_taxonomy_ref"),
        "module_boundaries": rows,
        "rollup": payload.get("rollup", {}),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "blocked_claims": payload.get("blocked_claims", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def _external_validation_review_pack_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    cases = payload.get("review_cases", [])
    deliverables = payload.get("required_external_deliverables", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "review_pack_status": payload.get("review_pack_status"),
        "roadmap_item": payload.get("roadmap_item", {}),
        "required_external_deliverables": deliverables if isinstance(deliverables, list) else [],
        "review_case_count": payload.get("review_case_count"),
        "review_cases": cases if isinstance(cases, list) else [],
        "dag_review_surface": payload.get("dag_review_surface", {}),
        "evidence_review_surface": payload.get("evidence_review_surface", {}),
        "runtime_review_surface": payload.get("runtime_review_surface", {}),
        "cost_procurement_review_surface": payload.get("cost_procurement_review_surface", {}),
        "rollup": payload.get("rollup", {}),
        "blocked_claims": payload.get("blocked_claims", []),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def _public_narrative_hardening_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rules = payload.get("claim_rules", [])
    surfaces = payload.get("public_surfaces", [])
    matrix = payload.get("source_claim_matrix", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "roadmap_item_ref": payload.get("roadmap_item_ref"),
        "review_status": payload.get("review_status"),
        "claim_rule_count": payload.get("claim_rule_count"),
        "blocked_claim_count": payload.get("blocked_claim_count"),
        "required_qualifier_count": payload.get("required_qualifier_count"),
        "public_surface_count": payload.get("public_surface_count"),
        "public_surfaces": surfaces if isinstance(surfaces, list) else [],
        "claim_rules": rules if isinstance(rules, list) else [],
        "forbidden_public_claims": payload.get("forbidden_public_claims", []),
        "required_public_concepts": payload.get("required_public_concepts", []),
        "allowed_phrasing": payload.get("allowed_phrasing", []),
        "replacement_guidance": payload.get("replacement_guidance", []),
        "source_claim_matrix": matrix if isinstance(matrix, list) else [],
        "source_rollups": payload.get("source_rollups", {}),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "browser_boundary": payload.get("browser_boundary", {}),
        "rollup": payload.get("rollup", {}),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def _external_validation_execution_ledger_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    cases = payload.get("execution_cases", [])
    deliverables = payload.get("required_external_deliverables", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "execution_ledger_status": payload.get("execution_ledger_status"),
        "review_pack_ref": payload.get("review_pack_ref"),
        "required_external_deliverables": deliverables if isinstance(deliverables, list) else [],
        "review_case_count": payload.get("review_case_count"),
        "execution_record_count": payload.get("execution_record_count"),
        "external_record_count": payload.get("external_record_count"),
        "execution_cases": cases if isinstance(cases, list) else [],
        "acceptance_record_policy": payload.get("acceptance_record_policy", {}),
        "rollup": payload.get("rollup", {}),
        "blocked_claims": payload.get("blocked_claims", []),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def _independent_physics_backend_comparison_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    checks = payload.get("analytic_checks", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "comparison_status": payload.get("comparison_status"),
        "backend_boundary": payload.get("backend_boundary", {}),
        "default_scenario_ref": payload.get("default_scenario_ref"),
        "analytic_check_count": payload.get("analytic_check_count"),
        "analytic_checks": checks if isinstance(checks, list) else [],
        "dag_boundary_snapshot": payload.get("dag_boundary_snapshot", {}),
        "rollup": payload.get("rollup", {}),
        "blocked_claims": payload.get("blocked_claims", []),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def _capsule_qualification_evidence_pack_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    tests = payload.get("qualification_tests", [])
    stack = payload.get("material_stack", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "capsule_design": payload.get("capsule_design", {}),
        "material_count": payload.get("material_count"),
        "layer_count": payload.get("layer_count"),
        "material_stack": stack if isinstance(stack, list) else [],
        "mass_closure": payload.get("mass_closure", {}),
        "survivability_model_inputs": payload.get("survivability_model_inputs", {}),
        "failure_modes": payload.get("failure_modes", []),
        "qualification_test_count": payload.get("qualification_test_count"),
        "qualification_tests": tests if isinstance(tests, list) else [],
        "lab_record_count": payload.get("lab_record_count"),
        "rollup": payload.get("rollup", {}),
        "blocked_claims": payload.get("blocked_claims", []),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def _evidence_upgrade_closure_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = payload.get("closure_rows", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "campaign_ref": payload.get("campaign_ref"),
        "closure_status": payload.get("closure_status"),
        "closure_cycle_count": payload.get("closure_cycle_count"),
        "closure_rows": rows if isinstance(rows, list) else [],
        "rollup": payload.get("rollup", {}),
        "blocked_claims": payload.get("blocked_claims", []),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def _external_reproduction_kit_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    cases = payload.get("review_cases", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "kit_status": payload.get("kit_status"),
        "review_case_count": payload.get("review_case_count"),
        "review_cases": cases if isinstance(cases, list) else [],
        "primary_tracks": payload.get("primary_tracks", []),
        "pack_contract": payload.get("pack_contract", {}),
        "readiness_snapshot": payload.get("readiness_snapshot", {}),
        "rollup": payload.get("rollup", {}),
        "blocked_claims": payload.get("blocked_claims", []),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def _external_evidence_intake_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "intake_status": payload.get("intake_status"),
        "record_schema_ref": payload.get("record_schema_ref"),
        "external_records_dir": payload.get("external_records_dir"),
        "record_count": payload.get("record_count"),
        "accepted_record_count": payload.get("accepted_record_count"),
        "rejected_record_count": payload.get("rejected_record_count"),
        "accepted_records": payload.get("accepted_records", []),
        "rejected_records": payload.get("rejected_records", []),
        "record_templates": payload.get("record_templates", []),
        "validation_policy": payload.get("validation_policy", {}),
        "rollup": payload.get("rollup", {}),
        "blocked_claims": payload.get("blocked_claims", []),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def _external_validation_campaign_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "campaign_status": payload.get("campaign_status"),
        "campaign_policy": payload.get("campaign_policy", {}),
        "workstream_count": payload.get("workstream_count"),
        "workstreams": payload.get("workstreams", []),
        "independent_backend_execution_plan": payload.get("independent_backend_execution_plan", {}),
        "line_of_sight_environment_model": payload.get("line_of_sight_environment_model", {}),
        "capsule_qualification_program": payload.get("capsule_qualification_program", {}),
        "proof_promotion_review": payload.get("proof_promotion_review", {}),
        "public_evidence_dossier": payload.get("public_evidence_dossier", {}),
        "rollup": payload.get("rollup", {}),
        "blocked_claims": payload.get("blocked_claims", []),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def _release_candidate_readiness_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    gates = payload.get("repository_gates", [])
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "public_scope": payload.get("public_scope"),
        "non_certification_notice": payload.get("non_certification_notice"),
        "release_candidate_status": payload.get("release_candidate_status"),
        "component_rollups": payload.get("component_rollups", {}),
        "repository_gates": gates if isinstance(gates, list) else [],
        "rollup": payload.get("rollup", {}),
        "blocked_claims": payload.get("blocked_claims", []),
        "external_evidence_gaps": payload.get("external_evidence_gaps", []),
        "interpretation_limits": payload.get("interpretation_limits", []),
        "determinism_signature": payload.get("determinism_signature"),
    }


def validate_browser_dataset(
    *,
    payload: Mapping[str, Any],
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    registry_lookup = _registry_by_id(repo_root)

    if payload.get("schema_version") != "browser_dataset.v1":
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r}")
    if payload.get("public_scope") != "tracked_generated_only":
        errors.append(f"public_scope mismatch: {payload.get('public_scope')!r}")

    source_paths = payload.get("source_paths")
    if not isinstance(source_paths, Mapping):
        errors.append("source_paths must be an object")
        source_paths = {}

    for key, expected in sorted(PUBLIC_DATASET_PATHS.items()):
        actual = source_paths.get(key)
        if actual != expected:
            errors.append(f"source_paths.{key} mismatch: expected {expected!r}, got {actual!r}")

    source_artifacts = payload.get("source_artifacts")
    if not isinstance(source_artifacts, list) or not source_artifacts:
        errors.append("source_artifacts must be a non-empty list")
    elif repo_root is not None:
        expected_hashes = {
            expected: _sha256_file(repo_root / expected)
            for expected in [
                PUBLIC_DATASET_PATHS["determinismStatus"],
                PUBLIC_DATASET_PATHS["failureSurfaceBaseline"],
                PUBLIC_DATASET_PATHS["parameterDrilldownManifest"],
                PUBLIC_DATASET_PATHS["parameterStaticUsageGraph"],
                PUBLIC_DATASET_PATHS["parameterEvidenceIndex"],
                PUBLIC_DATASET_PATHS["pSuccessDefensibility"],
                PUBLIC_DATASET_PATHS["objectiveScoreBaseline"],
                PUBLIC_DATASET_PATHS["optimizationSearchSpace"],
                PUBLIC_DATASET_PATHS["optimizationFrontier"],
                PUBLIC_DATASET_PATHS["optimizationV2"],
                PUBLIC_DATASET_PATHS["capsuleSurvivabilityLab"],
                PUBLIC_DATASET_PATHS["capsuleRiskBudget"],
                PUBLIC_DATASET_PATHS["missionFeasibilityScreen"],
                PUBLIC_DATASET_PATHS["userMissionRunCatalog"],
                PUBLIC_DATASET_PATHS["runtimeScenarioGeneration"],
                PUBLIC_DATASET_PATHS["costProcurementArchitectureFeasibility"],
                PUBLIC_DATASET_PATHS["externalValidationReviewPack"],
                PUBLIC_DATASET_PATHS["publicNarrativeHardening"],
                PUBLIC_DATASET_PATHS["externalValidationExecutionLedger"],
                PUBLIC_DATASET_PATHS["independentPhysicsBackendComparison"],
                PUBLIC_DATASET_PATHS["capsuleQualificationEvidencePack"],
                PUBLIC_DATASET_PATHS["evidenceUpgradeClosure"],
                PUBLIC_DATASET_PATHS["externalReproductionKit"],
                PUBLIC_DATASET_PATHS["externalEvidenceIntake"],
                PUBLIC_DATASET_PATHS["externalValidationCampaign"],
                PUBLIC_DATASET_PATHS["releaseCandidateReadiness"],
                PUBLIC_DATASET_PATHS["missionProbabilityCoupling"],
                PUBLIC_DATASET_PATHS["uncertaintyInteractions"],
                PUBLIC_DATASET_PATHS["evidenceUpgradeCampaign"],
                PUBLIC_DATASET_PATHS["missionDagV2Boundary"],
                PUBLIC_DATASET_PATHS["roadmapClosure"],
            ]
        }
        seen_paths: set[str] = set()
        for item in source_artifacts:
            if not isinstance(item, Mapping):
                errors.append("source_artifacts entries must be objects")
                continue
            path = item.get("path")
            sha256 = item.get("sha256")
            if not isinstance(path, str) or not path:
                errors.append("source_artifacts entry missing path")
                continue
            seen_paths.add(path)
            if path not in expected_hashes:
                errors.append(f"source_artifacts contains unexpected path: {path}")
                continue
            if sha256 != expected_hashes[path]:
                errors.append(f"source_artifacts sha mismatch for {path}: {sha256!r}")
        missing_paths = sorted(set(expected_hashes) - seen_paths)
        for path in missing_paths:
            errors.append(f"source_artifacts missing path: {path}")

    manifest = payload.get("manifest")
    if not _is_object(manifest):
        errors.append("manifest must be an object")
        manifest = {}
    manifest_parameters = manifest.get("parameters", [])
    if manifest.get("schema_version") != "parameter_drilldown_manifest.v1":
        errors.append(f"manifest.schema_version mismatch: {manifest.get('schema_version')!r}")
    if manifest.get("public_scope") != MANIFEST_PUBLIC_SCOPE:
        errors.append(f"manifest.public_scope mismatch: {manifest.get('public_scope')!r}")
    if manifest.get("ui_scope") != MANIFEST_UI_SCOPE:
        errors.append(f"manifest.ui_scope mismatch: {manifest.get('ui_scope')!r}")
    if not isinstance(manifest_parameters, list) or not manifest_parameters:
        errors.append("manifest.parameters must be a non-empty list")
        manifest_parameters = []
    if manifest.get("parameter_count") != len(manifest_parameters):
        errors.append(
            f"manifest.parameter_count mismatch: {manifest.get('parameter_count')!r} != {len(manifest_parameters)}"
        )

    static_usage_graph = payload.get("static_usage_graph")
    if not _is_object(static_usage_graph):
        errors.append("static_usage_graph must be an object")
        static_usage_graph = {}
    evidence_index = payload.get("evidence_index")
    if not _is_object(evidence_index):
        errors.append("evidence_index must be an object")
        evidence_index = {}

    parameter_ids = {
        str(entry.get("parameter_id"))
        for entry in manifest_parameters
        if isinstance(entry, Mapping) and isinstance(entry.get("parameter_id"), str)
    }
    if len(parameter_ids) != len(manifest_parameters):
        errors.append("manifest.parameters contains invalid or duplicate parameter_id entries")
    for index, entry in enumerate(manifest_parameters):
        if not isinstance(entry, Mapping):
            continue
        parameter_id = entry.get("parameter_id")
        if not isinstance(parameter_id, str):
            continue
        if _has_visibility_metadata(entry) and not _allows_public_surface(entry, PUBLIC_SURFACE_BROWSER):
            errors.append(
                f"manifest.parameters[{index}] visibility metadata must allow public browser surface"
            )
    for parameter_id in sorted(parameter_ids):
        registry_entry = registry_lookup.get(parameter_id)
        if isinstance(registry_entry, Mapping) and not _allows_public_surface(registry_entry, PUBLIC_SURFACE_BROWSER):
            errors.append(f"manifest.parameters contains registry non-browser-public parameter: {parameter_id}")
        elif _is_internal_parameter_id(parameter_id):
            errors.append(f"manifest.parameters contains internal parameter_id: {parameter_id}")
    for parameter_id in sorted(parameter_ids):
        if parameter_id not in static_usage_graph:
            errors.append(f"static_usage_graph missing parameter: {parameter_id}")
        if parameter_id not in evidence_index:
            errors.append(f"evidence_index missing parameter: {parameter_id}")

    static_usage_ids = {
        parameter_id
        for parameter_id in static_usage_graph.keys()
        if isinstance(parameter_id, str)
    }
    evidence_ids = {
        parameter_id
        for parameter_id in evidence_index.keys()
        if isinstance(parameter_id, str)
    }
    unexpected_static = sorted(static_usage_ids - parameter_ids)
    unexpected_evidence = sorted(evidence_ids - parameter_ids)
    for parameter_id in unexpected_static:
        errors.append(f"static_usage_graph contains non-public parameter: {parameter_id}")
    for parameter_id in unexpected_evidence:
        errors.append(f"evidence_index contains non-public parameter: {parameter_id}")

    p_success = payload.get("p_success_defensibility")
    if not _is_object(p_success):
        errors.append("p_success_defensibility must be an object")
        p_success = {}
    if p_success.get("schema_version") != "p_success_defensibility.v1":
        errors.append(f"p_success_defensibility.schema_version mismatch: {p_success.get('schema_version')!r}")

    determinism_status = payload.get("determinism_status")
    if not _is_object(determinism_status):
        errors.append("determinism_status must be an object")
    elif not determinism_status.get("golden_checksum"):
        errors.append("determinism_status.golden_checksum must be present")

    failure_surface = payload.get("failure_surface_baseline")
    if not _is_object(failure_surface):
        errors.append("failure_surface_baseline must be an object")
        failure_surface = {}
    if failure_surface.get("schema_version") != "failure_surface.v1":
        errors.append(
            f"failure_surface_baseline.schema_version mismatch: {failure_surface.get('schema_version')!r}"
        )
    timeline = failure_surface.get("timeline")
    if not isinstance(timeline, list) or len(timeline) != 4:
        errors.append("failure_surface_baseline.timeline must contain exactly 4 entries")
    dominant_drivers = failure_surface.get("dominant_drivers")
    if not _is_object(dominant_drivers):
        errors.append("failure_surface_baseline.dominant_drivers must be an object")
        dominant_drivers = {}
    top3 = dominant_drivers.get("top3")
    if not isinstance(top3, list) or len(top3) != 3:
        errors.append("failure_surface_baseline.dominant_drivers.top3 must contain exactly 3 entries")
        top3 = []
    for driver in top3:
        if not isinstance(driver, Mapping):
            errors.append("failure_surface_baseline.dominant_drivers.top3 entries must be objects")
            continue
        parameter_id = driver.get("parameter_id")
        evidence_ref = driver.get("evidence_ref")
        if parameter_id not in parameter_ids:
            errors.append(f"failure_surface_baseline driver missing from manifest: {parameter_id!r}")
        expected_ref = f"{PUBLIC_DATASET_PATHS['parameterEvidenceIndex']}#{parameter_id}"
        if evidence_ref != expected_ref:
            errors.append(
                f"failure_surface_baseline evidence_ref mismatch for {parameter_id!r}: {evidence_ref!r}"
            )

    objective_contract = payload.get("objective_contract")
    if not _is_object(objective_contract):
        errors.append("objective_contract must be an object")
        objective_contract = {}
    if objective_contract.get("schema_version") != "objective_contract.v1":
        errors.append(f"objective_contract.schema_version mismatch: {objective_contract.get('schema_version')!r}")

    objective_score = payload.get("objective_score_baseline")
    if not _is_object(objective_score):
        errors.append("objective_score_baseline must be an object")
        objective_score = {}
    if objective_score.get("schema_version") != "objective_score.v1":
        errors.append(
            f"objective_score_baseline.schema_version mismatch: {objective_score.get('schema_version')!r}"
        )
    if objective_score.get("contract_ref") != PUBLIC_DATASET_PATHS["objectiveContract"]:
        errors.append(
            "objective_score_baseline.contract_ref must match source_paths.objectiveContract"
        )
    contract_snapshot = objective_score.get("contract_snapshot")
    if contract_snapshot != objective_contract:
        errors.append("objective_contract must equal objective_score_baseline.contract_snapshot")
    defensibility = objective_score.get("defensibility")
    if not isinstance(defensibility, Mapping) or defensibility.get("p_success_ref") != PUBLIC_DATASET_PATHS[
        "pSuccessDefensibility"
    ]:
        errors.append(
            "objective_score_baseline.defensibility.p_success_ref must match source_paths.pSuccessDefensibility"
        )

    optimization_search_space = payload.get("optimization_search_space")
    if not _is_object(optimization_search_space):
        errors.append("optimization_search_space must be an object")
        optimization_search_space = {}
    if optimization_search_space.get("schema_version") != "optimization_search_space.v1":
        errors.append(
            f"optimization_search_space.schema_version mismatch: {optimization_search_space.get('schema_version')!r}"
        )
    if optimization_search_space.get("objective_contract_ref") != PUBLIC_DATASET_PATHS["objectiveContract"]:
        errors.append(
            "optimization_search_space.objective_contract_ref must match source_paths.objectiveContract"
        )
    considered_parameters = optimization_search_space.get("parameters_considered")
    if not isinstance(considered_parameters, list):
        errors.append("optimization_search_space.parameters_considered must be a list")
        considered_parameters = []
    excluded_parameters = optimization_search_space.get("excluded_parameters")
    if not isinstance(excluded_parameters, list):
        errors.append("optimization_search_space.excluded_parameters must be a list")
        excluded_parameters = []
    excluded_internal_parameter_count = optimization_search_space.get("excluded_internal_parameter_count")
    if not isinstance(excluded_internal_parameter_count, int) or excluded_internal_parameter_count < 0:
        errors.append("optimization_search_space.excluded_internal_parameter_count must be int >= 0")
    internal_prefixes = optimization_search_space.get("internal_parameter_prefixes_excluded")
    if not isinstance(internal_prefixes, list) or "code_literal." not in internal_prefixes:
        errors.append(
            "optimization_search_space.internal_parameter_prefixes_excluded must include code_literal."
        )
    for index, item in enumerate(considered_parameters):
        if not isinstance(item, Mapping):
            continue
        parameter_id = str(item.get("parameter_id", ""))
        registry_entry = registry_lookup.get(parameter_id)
        if _has_visibility_metadata(item) and not _allows_public_surface(item, PUBLIC_SURFACE_OPTIMIZATION):
            errors.append(
                f"optimization_search_space.parameters_considered[{index}] visibility metadata must allow public optimization surface"
            )
        if isinstance(registry_entry, Mapping) and not _allows_public_surface(registry_entry, PUBLIC_SURFACE_OPTIMIZATION):
            errors.append(
                f"optimization_search_space.parameters_considered[{index}] registry visibility must allow public optimization surface"
            )
        elif _is_internal_parameter_id(parameter_id):
            errors.append(
                f"optimization_search_space.parameters_considered[{index}] must not contain internal parameter"
            )
    for index, item in enumerate(excluded_parameters):
        if not isinstance(item, Mapping):
            continue
        parameter_id = str(item.get("parameter_id", ""))
        registry_entry = registry_lookup.get(parameter_id)
        if _has_visibility_metadata(item) and not _allows_public_surface(item, PUBLIC_SURFACE_OPTIMIZATION):
            errors.append(
                f"optimization_search_space.excluded_parameters[{index}] visibility metadata must allow public optimization surface"
            )
        if isinstance(registry_entry, Mapping) and not _allows_public_surface(registry_entry, PUBLIC_SURFACE_OPTIMIZATION):
            errors.append(
                f"optimization_search_space.excluded_parameters[{index}] registry visibility must allow public optimization surface"
            )
        elif _is_internal_parameter_id(parameter_id):
            errors.append(
                f"optimization_search_space.excluded_parameters[{index}] must not contain internal parameter"
            )

    optimization_frontier = payload.get("optimization_frontier")
    if not _is_object(optimization_frontier):
        errors.append("optimization_frontier must be an object")
        optimization_frontier = {}
    if optimization_frontier.get("schema_version") != "optimization_frontier.v1":
        errors.append(
            f"optimization_frontier.schema_version mismatch: {optimization_frontier.get('schema_version')!r}"
        )
    if optimization_frontier.get("objective_contract_ref") != PUBLIC_DATASET_PATHS["objectiveContract"]:
        errors.append("optimization_frontier.objective_contract_ref must match source_paths.objectiveContract")
    points = optimization_frontier.get("points")
    if not isinstance(points, list) or not points:
        errors.append("optimization_frontier.points must be a non-empty list")
        points = []
    if optimization_frontier.get("evaluation_count") != len(points):
        errors.append(
            f"optimization_frontier.evaluation_count mismatch: {optimization_frontier.get('evaluation_count')!r} != {len(points)}"
        )

    optimization_v2 = payload.get("optimization_v2")
    if not _is_object(optimization_v2):
        errors.append("optimization_v2 must be an object")
        optimization_v2 = {}
    if optimization_v2.get("schema_version") != "optimization_v2_frontier.v1":
        errors.append("optimization_v2.schema_version mismatch")
    if optimization_v2.get("mode") != "realistic":
        errors.append("optimization_v2.mode must be realistic")
    if optimization_v2.get("non_certification_notice") is not True:
        errors.append("optimization_v2.non_certification_notice must be true")
    axis_contract = optimization_v2.get("axis_contract")
    if not isinstance(axis_contract, Mapping):
        errors.append("optimization_v2.axis_contract must be object")
        axis_contract = {}
    axes = axis_contract.get("axes")
    expected_axes = ["p_success", "risk_envelope", "qualification_gap", "cost_proxy"]
    expected_axis_contract = {
        "p_success": ("maximize", "computed"),
        "risk_envelope": ("minimize", "computed"),
        "qualification_gap": ("minimize", "screening_proxy"),
        "cost_proxy": ("minimize", "screening_proxy"),
    }
    if not isinstance(axes, list):
        errors.append("optimization_v2.axis_contract.axes must be list")
        axes = []
    axis_ids = [axis.get("id") for axis in axes if isinstance(axis, Mapping)]
    if axis_ids != expected_axes:
        errors.append("optimization_v2.axis_contract axes mismatch")
    for axis in axes:
        if not isinstance(axis, Mapping):
            errors.append("optimization_v2.axis_contract axis must be object")
            continue
        axis_id = axis.get("id")
        expected = expected_axis_contract.get(str(axis_id))
        if expected is None:
            continue
        expected_direction, expected_status = expected
        if axis.get("direction") != expected_direction:
            errors.append(f"optimization_v2.axis_contract.{axis_id}.direction mismatch")
        if axis.get("status") != expected_status:
            errors.append(f"optimization_v2.axis_contract.{axis_id}.status mismatch")
    rollup = optimization_v2.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("optimization_v2.rollup must be object")
        rollup = {}
    if rollup.get("axis_ids") != ["p_success", "risk_envelope", "qualification_gap", "cost_proxy"]:
        errors.append("optimization_v2.rollup.axis_ids mismatch")
    if rollup.get("aggregation_policy") != "pareto_first_no_hidden_weighted_sum":
        errors.append("optimization_v2.rollup.aggregation_policy mismatch")
    for field in (
        "global_optimum_claimed",
        "hidden_weighted_sum_used",
        "calibrated_cost_model_available",
        "qualification_complete",
    ):
        if rollup.get(field) is not False:
            errors.append(f"optimization_v2.rollup.{field} must be false")
    candidates = optimization_v2.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append("optimization_v2.candidates must be non-empty")
        candidates = []
    if optimization_v2.get("candidate_count") != len(candidates):
        errors.append("optimization_v2.candidate_count mismatch")
    pareto_ids = optimization_v2.get("pareto_frontier_candidate_ids")
    if not isinstance(pareto_ids, list) or not pareto_ids:
        errors.append("optimization_v2.pareto_frontier_candidate_ids must be non-empty")
        pareto_ids = []
    if optimization_v2.get("frontier_candidate_count") != len(pareto_ids):
        errors.append("optimization_v2.frontier_candidate_count mismatch")
    source_candidate_ids = {
        str(point.get("candidate_id"))
        for point in points
        if isinstance(point, Mapping) and isinstance(point.get("candidate_id"), str)
    }
    candidate_ids = []
    pareto_member_ids = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping):
            errors.append(f"optimization_v2.candidates[{index}] must be object")
            continue
        candidate_id = candidate.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id.startswith("optv2-pt-"):
            errors.append(f"optimization_v2.candidates[{index}].candidate_id must start with optv2-pt-")
            candidate_id = f"invalid-{index}"
        else:
            candidate_ids.append(candidate_id)
        source_candidate_id = candidate.get("source_candidate_id")
        if not isinstance(source_candidate_id, str) or source_candidate_id not in source_candidate_ids:
            errors.append(f"optimization_v2.candidates[{index}].source_candidate_id must map to source frontier")
        scores = candidate.get("scores")
        if not isinstance(scores, Mapping):
            errors.append(f"optimization_v2.candidates[{index}].scores must be object")
            continue
        vector = scores.get("objective_vector")
        if not isinstance(vector, list) or len(vector) != 4:
            errors.append(f"optimization_v2.candidates[{index}].objective_vector must contain four axes")
        for axis in ("p_success", "risk_envelope", "qualification_gap", "cost_proxy"):
            value = scores.get(axis)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 <= float(value) <= 1.0:
                errors.append(f"optimization_v2.candidates[{index}].scores.{axis} must be probability-like")
        if isinstance(vector, list) and len(vector) == 4:
            for axis_index, axis in enumerate(("p_success", "risk_envelope", "qualification_gap", "cost_proxy")):
                scalar = scores.get(axis)
                if isinstance(scalar, (int, float)) and not isinstance(scalar, bool):
                    if not isinstance(vector[axis_index], (int, float)) or isinstance(vector[axis_index], bool):
                        errors.append(f"optimization_v2.candidates[{index}].objective_vector[{axis_index}] must be numeric")
                    elif abs(float(vector[axis_index]) - float(scalar)) > 1e-12:
                        errors.append(f"optimization_v2.candidates[{index}].objective_vector[{axis_index}] must equal {axis}")
        if scores.get("rank_key") != "pareto":
            errors.append(f"optimization_v2.candidates[{index}].scores.rank_key must be pareto")
        explain = candidate.get("axis_explainability")
        if not isinstance(explain, Mapping):
            errors.append(f"optimization_v2.candidates[{index}].axis_explainability must be object")
        drivers = candidate.get("dominant_drivers")
        if not isinstance(drivers, Mapping):
            errors.append(f"optimization_v2.candidates[{index}].dominant_drivers must be object")
        else:
            driver_ids = drivers.get("parameter_ids")
            if not isinstance(driver_ids, list):
                errors.append(f"optimization_v2.candidates[{index}].dominant_drivers.parameter_ids must be list")
            else:
                for parameter_id in driver_ids:
                    if not isinstance(parameter_id, str):
                        errors.append(f"optimization_v2.candidates[{index}].dominant_drivers.parameter_ids must be string list")
                    elif _is_internal_parameter_id(parameter_id):
                        errors.append(f"optimization_v2.candidates[{index}] leaks internal dominant driver: {parameter_id}")
            omitted = drivers.get("excluded_internal_parameter_count")
            if not isinstance(omitted, int) or omitted < 0:
                errors.append(f"optimization_v2.candidates[{index}].dominant_drivers.excluded_internal_parameter_count must be int >= 0")
        if candidate.get("pareto_frontier_member") is True:
            pareto_member_ids.append(candidate_id)
        elif candidate.get("pareto_frontier_member") is not False:
            errors.append(f"optimization_v2.candidates[{index}].pareto_frontier_member must be boolean")
    if len(candidate_ids) != len(set(candidate_ids)):
        errors.append("optimization_v2 candidate ids must be unique")
    if any(candidate_id not in set(candidate_ids) for candidate_id in pareto_ids):
        errors.append("optimization_v2 pareto ids must reference candidates")
    if pareto_ids and pareto_member_ids != pareto_ids:
        errors.append("optimization_v2 pareto member flags must match pareto_frontier_candidate_ids")
    blocked = optimization_v2.get("blocked_claims")
    if not isinstance(blocked, list) or "global optimum proven" not in blocked:
        errors.append("optimization_v2.blocked_claims must block global optimum proof")
    if isinstance(blocked, list) and "procurement-grade cost estimate" not in blocked:
        errors.append("optimization_v2.blocked_claims must block procurement-grade cost estimates")
    if isinstance(blocked, list) and "qualification complete" not in blocked:
        errors.append("optimization_v2.blocked_claims must block qualification completion")
    if isinstance(blocked, list) and "flight-ready design selected" not in blocked:
        errors.append("optimization_v2.blocked_claims must block flight-ready design selection")

    capsule_survivability = payload.get("capsule_survivability_lab")
    if not _is_object(capsule_survivability):
        errors.append("capsule_survivability_lab must be an object")
        capsule_survivability = {}
    if capsule_survivability.get("schema_version") != "capsule_survivability_lab.v1":
        errors.append(
            "capsule_survivability_lab.schema_version mismatch: "
            f"{capsule_survivability.get('schema_version')!r}"
        )
    if capsule_survivability.get("non_certification_notice") is not True:
        errors.append("capsule_survivability_lab.non_certification_notice must be true")
    capsule_rows = capsule_survivability.get("rows")
    if not isinstance(capsule_rows, list) or len(capsule_rows) < 100:
        errors.append("capsule_survivability_lab.rows must contain at least 100 entries")

    capsule_risk_budget = payload.get("capsule_risk_budget")
    if not _is_object(capsule_risk_budget):
        errors.append("capsule_risk_budget must be an object")
        capsule_risk_budget = {}
    if capsule_risk_budget.get("schema_version") != "capsule_risk_budget.v1":
        errors.append(
            "capsule_risk_budget.schema_version mismatch: "
            f"{capsule_risk_budget.get('schema_version')!r}"
        )
    if capsule_risk_budget.get("non_certification_notice") is not True:
        errors.append("capsule_risk_budget.non_certification_notice must be true")
    if capsule_risk_budget.get("source_artifact_ref") != PUBLIC_DATASET_PATHS["capsuleSurvivabilityLab"]:
        errors.append("capsule_risk_budget.source_artifact_ref must match source_paths.capsuleSurvivabilityLab")
    if capsule_risk_budget.get("sample_count", 0) < 1000:
        errors.append("capsule_risk_budget.sample_count must be at least 1000")
    attack_modes = capsule_risk_budget.get("attack_modes")
    if isinstance(attack_modes, Mapping):
        attack_mode_entries = attack_modes.get("modes")
    else:
        attack_mode_entries = attack_modes
    if not isinstance(attack_mode_entries, list) or len(attack_mode_entries) < 4:
        errors.append("capsule_risk_budget.attack_modes must contain at least 4 entries")
    risk_budget_count = capsule_risk_budget.get("risk_budget_count")
    if not isinstance(risk_budget_count, int) or risk_budget_count < 100:
        errors.append("capsule_risk_budget.risk_budget_count must be at least 100")
    source_policy = capsule_risk_budget.get("source_policy")
    if not _is_object(source_policy):
        errors.append("capsule_risk_budget.source_policy must be an object")
    failure_modes = capsule_risk_budget.get("failure_modes")
    if not isinstance(failure_modes, list) or len(failure_modes) < 8:
        errors.append("capsule_risk_budget.failure_modes must contain at least 8 entries")
    qualification_roadmap = capsule_risk_budget.get("qualification_roadmap")
    if not isinstance(qualification_roadmap, list) or len(qualification_roadmap) < 5:
        errors.append("capsule_risk_budget.qualification_roadmap must contain at least 5 entries")

    roadmap_closure = payload.get("roadmap_closure")
    if not _is_object(roadmap_closure):
        errors.append("roadmap_closure must be an object")
        roadmap_closure = {}
    if roadmap_closure.get("schema_version") != "roadmap_closure.v1":
        errors.append(f"roadmap_closure.schema_version mismatch: {roadmap_closure.get('schema_version')!r}")
    if roadmap_closure.get("non_certification_notice") is not True:
        errors.append("roadmap_closure.non_certification_notice must be true")
    if roadmap_closure.get("roadmap_item_count") != 15:
        errors.append("roadmap_closure.roadmap_item_count must be 15")
    closure_items = roadmap_closure.get("roadmap_items")
    if not isinstance(closure_items, list) or len(closure_items) != 15:
        errors.append("roadmap_closure.roadmap_items must contain exactly 15 entries")
    else:
        for index, item in enumerate(closure_items):
            if not isinstance(item, Mapping):
                errors.append(f"roadmap_closure.roadmap_items[{index}] must be an object")
                continue
            if item.get("status") != "repo_native_closure_implemented_external_evidence_open":
                errors.append(
                    "roadmap_closure.roadmap_items"
                    f"[{index}].status must be repo_native_closure_implemented_external_evidence_open"
                )
            if item.get("non_certification_notice") is not True:
                errors.append(f"roadmap_closure.roadmap_items[{index}].non_certification_notice must be true")
            gaps = item.get("external_evidence_gaps")
            if not isinstance(gaps, list) or not gaps:
                errors.append(f"roadmap_closure.roadmap_items[{index}].external_evidence_gaps must be non-empty")
    closure_metrics = roadmap_closure.get("closure_metrics", {})
    if not isinstance(closure_metrics, Mapping) or closure_metrics.get("repo_native_closure_count") != 15:
        errors.append("roadmap_closure.closure_metrics.repo_native_closure_count must be 15")

    mission_feasibility = payload.get("mission_feasibility_screen")
    if not _is_object(mission_feasibility):
        errors.append("mission_feasibility_screen must be an object")
        mission_feasibility = {}
    if mission_feasibility.get("schema_version") != "mission_feasibility_screen.v1":
        errors.append("mission_feasibility_screen.schema_version mismatch")
    if mission_feasibility.get("non_certification_notice") is not True:
        errors.append("mission_feasibility_screen.non_certification_notice must be true")
    if mission_feasibility.get("scenario_count") != 15:
        errors.append("mission_feasibility_screen.scenario_count must be 15")
    if mission_feasibility.get("capsule_risk_budget_match_count") != 15:
        errors.append("mission_feasibility_screen must link all 15 rows to risk budget rows")
    scenario_rows = mission_feasibility.get("scenario_rows")
    if not isinstance(scenario_rows, list) or len(scenario_rows) != 15:
        errors.append("mission_feasibility_screen.scenario_rows must contain 15 rows")

    user_run_catalog = payload.get("user_mission_run_catalog")
    if not _is_object(user_run_catalog):
        errors.append("user_mission_run_catalog must be an object")
        user_run_catalog = {}
    if user_run_catalog.get("schema_version") != "user_mission_run_catalog.v1":
        errors.append("user_mission_run_catalog.schema_version mismatch")
    if user_run_catalog.get("non_certification_notice") is not True:
        errors.append("user_mission_run_catalog.non_certification_notice must be true")
    if user_run_catalog.get("run_count") != 15:
        errors.append("user_mission_run_catalog.run_count must be 15")
    if user_run_catalog.get("target_count") != 3 or user_run_catalog.get("velocity_count") != 5:
        errors.append("user_mission_run_catalog target/velocity counts must be 3 x 5")
    run_rows = user_run_catalog.get("run_rows")
    if not isinstance(run_rows, list) or len(run_rows) != 15:
        errors.append("user_mission_run_catalog.run_rows must contain 15 rows")
    else:
        default_seen = False
        for index, row in enumerate(run_rows):
            if not isinstance(row, Mapping):
                errors.append(f"user_mission_run_catalog.run_rows[{index}] must be object")
                continue
            if not isinstance(row.get("run_id"), str) or not str(row.get("run_id")).startswith("umr-"):
                errors.append(f"user_mission_run_catalog.run_rows[{index}].run_id must start with umr-")
            if not isinstance(row.get("selection_hash"), str) or len(str(row.get("selection_hash"))) != 64:
                errors.append(f"user_mission_run_catalog.run_rows[{index}].selection_hash must be sha256")
            selection = row.get("selection")
            if not isinstance(selection, Mapping):
                errors.append(f"user_mission_run_catalog.run_rows[{index}].selection must be object")
                continue
            if selection.get("target_id") == "reference-black-hole" and selection.get("velocity_id") == "conditional-45":
                default_seen = row.get("run_id") == user_run_catalog.get("default_run_id")
            if not isinstance(row.get("blocked_claims"), list) or "flight ready" not in row["blocked_claims"]:
                errors.append(f"user_mission_run_catalog.run_rows[{index}].blocked_claims must include flight ready")
        if not default_seen:
            errors.append("user_mission_run_catalog.default_run_id must reference default feasibility row")

    runtime_generation = payload.get("runtime_scenario_generation")
    if not _is_object(runtime_generation):
        errors.append("runtime_scenario_generation must be an object")
        runtime_generation = {}
    if runtime_generation.get("schema_version") != "runtime_scenario_generation.v1":
        errors.append("runtime_scenario_generation.schema_version mismatch")
    if runtime_generation.get("non_certification_notice") is not True:
        errors.append("runtime_scenario_generation.non_certification_notice must be true")
    axes = runtime_generation.get("selection_axes")
    if not isinstance(axes, Mapping):
        errors.append("runtime_scenario_generation.selection_axes must be object")
        axes = {}
    if axes.get("target_count") != 3 or axes.get("velocity_count") != 5:
        errors.append("runtime_scenario_generation target/velocity counts must be 3 x 5")
    if axes.get("supported_modes") != ["realistic", "speculative", "dual"]:
        errors.append("runtime_scenario_generation supported modes mismatch")
    pack = runtime_generation.get("run_pack_contract")
    if not isinstance(pack, Mapping):
        errors.append("runtime_scenario_generation.run_pack_contract must be object")
        pack = {}
    if pack.get("tracked_by_default") is not False or pack.get("writes_tracked_files") is not False:
        errors.append("runtime_scenario_generation run packs must not write tracked files by default")
    if "USER_RUN_SUMMARY.json" not in (pack.get("output_files") or []):
        errors.append("runtime_scenario_generation.run_pack_contract must include USER_RUN_SUMMARY.json")
    generation_rows = runtime_generation.get("generation_rows")
    if not isinstance(generation_rows, list) or len(generation_rows) != 15:
        errors.append("runtime_scenario_generation.generation_rows must contain 15 rows")
        generation_rows = []
    default_runtime_row = next(
        (
            row
            for row in generation_rows
            if isinstance(row, Mapping) and row.get("run_id") == axes.get("default_run_id")
        ),
        None,
    )
    if not isinstance(default_runtime_row, Mapping):
        errors.append("runtime_scenario_generation default row missing")
    elif default_runtime_row.get("target_id") != "reference-black-hole" or default_runtime_row.get("velocity_id") != "conditional-45":
        errors.append("runtime_scenario_generation default row must be reference-black-hole conditional-45")
    for index, row in enumerate(generation_rows):
        if not isinstance(row, Mapping):
            errors.append(f"runtime_scenario_generation.generation_rows[{index}] must be object")
            continue
        command = row.get("command_preview")
        if not isinstance(command, str) or "scripts/run_user_mission_scenario.py" not in command:
            errors.append(f"runtime_scenario_generation row {row.get('run_id')} command_preview must call runner")
        elif "--verify-deterministic" not in command:
            errors.append(f"runtime_scenario_generation row {row.get('run_id')} must require deterministic verification")
        ownership = row.get("ownership_boundary")
        if not isinstance(ownership, Mapping) or ownership.get("remote_execution") is not False:
            errors.append(f"runtime_scenario_generation row {row.get('run_id')} must keep remote execution false")
        if not isinstance(ownership, Mapping) or ownership.get("persistent_reviewed_archive") is not False:
            errors.append(f"runtime_scenario_generation row {row.get('run_id')} must keep persistent archive false")
        row_pack = row.get("run_pack_contract")
        if not isinstance(row_pack, Mapping):
            errors.append(f"runtime_scenario_generation row {row.get('run_id')} run_pack_contract must be object")
            row_pack = {}
        if row_pack.get("writes_tracked_files") is not False:
            errors.append(f"runtime_scenario_generation row {row.get('run_id')} must not write tracked files")
    rollup = runtime_generation.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("runtime_scenario_generation.rollup must be object")
    else:
        if rollup.get("rows_writing_tracked_files") != 0:
            errors.append("runtime_scenario_generation.rollup.rows_writing_tracked_files must be 0")
        if rollup.get("remote_execution_claimed") is not False:
            errors.append("runtime_scenario_generation.rollup.remote_execution_claimed must be false")
        if rollup.get("persistent_reviewed_archive_claimed") is not False:
            errors.append("runtime_scenario_generation.rollup.persistent_reviewed_archive_claimed must be false")
    blocked = runtime_generation.get("blocked_claims")
    if not isinstance(blocked, list) or "persistent reviewed run archive" not in blocked:
        errors.append("runtime_scenario_generation.blocked_claims must block persistent archive claims")

    cost_architecture = payload.get("cost_procurement_architecture_feasibility")
    if not _is_object(cost_architecture):
        errors.append("cost_procurement_architecture_feasibility must be an object")
        cost_architecture = {}
    if cost_architecture.get("schema_version") != "cost_procurement_architecture_feasibility.v1":
        errors.append("cost_procurement_architecture_feasibility.schema_version mismatch")
    if cost_architecture.get("non_certification_notice") is not True:
        errors.append("cost_procurement_architecture_feasibility.non_certification_notice must be true")
    if cost_architecture.get("architecture_row_count") != 15:
        errors.append("cost_procurement_architecture_feasibility.architecture_row_count must be 15")
    cost_rows = cost_architecture.get("architecture_rows")
    if not isinstance(cost_rows, list) or len(cost_rows) != 15:
        errors.append("cost_procurement_architecture_feasibility.architecture_rows must contain 15 rows")
        cost_rows = []
    for index, row in enumerate(cost_rows):
        if not isinstance(row, Mapping):
            errors.append(f"cost_procurement_architecture_feasibility.architecture_rows[{index}] must be object")
            continue
        if row.get("procurement_status") != "external_required":
            errors.append(
                f"cost_procurement_architecture_feasibility.architecture_rows[{index}].procurement_status must be external_required"
            )
        score = row.get("cost_proxy_score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0.0 <= float(score) <= 1.0:
            errors.append(
                f"cost_procurement_architecture_feasibility.architecture_rows[{index}].cost_proxy_score must be in [0,1]"
            )
    cost_rollup = cost_architecture.get("rollup")
    if not isinstance(cost_rollup, Mapping):
        errors.append("cost_procurement_architecture_feasibility.rollup must be object")
        cost_rollup = {}
    for field in (
        "procurement_grade_estimate_available",
        "launch_vehicle_selected",
        "architecture_selected_for_flight",
        "calibrated_cost_model_available",
        "qualification_complete",
    ):
        if cost_rollup.get(field) is not False:
            errors.append(f"cost_procurement_architecture_feasibility.rollup.{field} must be false")
    if cost_rollup.get("vendor_quote_count") != 0:
        errors.append("cost_procurement_architecture_feasibility.rollup.vendor_quote_count must be 0")
    cost_axis = cost_architecture.get("optimization_cost_axis")
    if not isinstance(cost_axis, Mapping):
        errors.append("cost_procurement_architecture_feasibility.optimization_cost_axis must be object")
        cost_axis = {}
    if cost_axis.get("axis_id") != "cost_proxy" or cost_axis.get("status") != "screening_proxy":
        errors.append("cost_procurement_architecture_feasibility.optimization_cost_axis must expose cost_proxy screening axis")
    cost_blocked = cost_architecture.get("blocked_claims")
    if not isinstance(cost_blocked, list) or "procurement-grade cost estimate" not in cost_blocked:
        errors.append("cost_procurement_architecture_feasibility.blocked_claims must block procurement-grade estimate")
    if isinstance(cost_blocked, list) and "flight-ready architecture selected" not in cost_blocked:
        errors.append("cost_procurement_architecture_feasibility.blocked_claims must block flight-ready architecture")

    external_review = payload.get("external_validation_review_pack")
    if not _is_object(external_review):
        errors.append("external_validation_review_pack must be an object")
        external_review = {}
    if external_review.get("schema_version") != "external_validation_review_pack.v1":
        errors.append("external_validation_review_pack.schema_version mismatch")
    if external_review.get("non_certification_notice") is not True:
        errors.append("external_validation_review_pack.non_certification_notice must be true")
    if external_review.get("review_pack_status") != "repo_native_review_pack_ready_external_review_not_completed":
        errors.append("external_validation_review_pack.review_pack_status must keep external review incomplete")
    if external_review.get("review_case_count") != 7:
        errors.append("external_validation_review_pack.review_case_count must be 7")
    review_cases = external_review.get("review_cases")
    if not isinstance(review_cases, list) or len(review_cases) != 7:
        errors.append("external_validation_review_pack.review_cases must contain 7 rows")
        review_cases = []
    for index, row in enumerate(review_cases):
        if not isinstance(row, Mapping):
            errors.append(f"external_validation_review_pack.review_cases[{index}] must be object")
            continue
        if row.get("status") != "external_required":
            errors.append(f"external_validation_review_pack.review_cases[{index}].status must be external_required")
        if row.get("independent_result_available") is not False:
            errors.append(
                f"external_validation_review_pack.review_cases[{index}].independent_result_available must be false"
            )
    deliverables = external_review.get("required_external_deliverables")
    if not isinstance(deliverables, list) or len(deliverables) != 6:
        errors.append("external_validation_review_pack.required_external_deliverables must contain 6 rows")
    review_rollup = external_review.get("rollup")
    if not isinstance(review_rollup, Mapping):
        errors.append("external_validation_review_pack.rollup must be object")
        review_rollup = {}
    for field in (
        "third_party_review_completed",
        "independent_reproduction_completed",
        "independent_benchmark_completed",
        "high_fidelity_state_trace_complete",
        "external_red_team_completed",
        "external_validation_claimed",
    ):
        if review_rollup.get(field) is not False:
            errors.append(f"external_validation_review_pack.rollup.{field} must be false")
    if review_rollup.get("all_cases_require_external_review") is not True:
        errors.append("external_validation_review_pack.rollup.all_cases_require_external_review must be true")
    review_blocked = external_review.get("blocked_claims")
    if not isinstance(review_blocked, list) or "third-party validated" not in review_blocked:
        errors.append("external_validation_review_pack.blocked_claims must block third-party validation")
    if isinstance(review_blocked, list) and "independent reproduction completed" not in review_blocked:
        errors.append("external_validation_review_pack.blocked_claims must block independent reproduction")

    narrative = payload.get("public_narrative_hardening")
    if not _is_object(narrative):
        errors.append("public_narrative_hardening must be an object")
        narrative = {}
    if narrative.get("schema_version") != "public_narrative_hardening.v1":
        errors.append("public_narrative_hardening.schema_version mismatch")
    if narrative.get("non_certification_notice") is not True:
        errors.append("public_narrative_hardening.non_certification_notice must be true")
    if narrative.get("roadmap_item_ref") != "roadmap-15":
        errors.append("public_narrative_hardening.roadmap_item_ref must be roadmap-15")
    if narrative.get("claim_rule_count") != 10:
        errors.append("public_narrative_hardening.claim_rule_count must be 10")
    if not isinstance(narrative.get("public_surfaces"), list) or len(narrative.get("public_surfaces", [])) < 8:
        errors.append("public_narrative_hardening.public_surfaces must contain at least 8 rows")
    if not isinstance(narrative.get("claim_rules"), list) or len(narrative.get("claim_rules", [])) != 10:
        errors.append("public_narrative_hardening.claim_rules must contain 10 rows")
    forbidden = narrative.get("forbidden_public_claims")
    if not isinstance(forbidden, list) or "certified" not in forbidden:
        errors.append("public_narrative_hardening.forbidden_public_claims must include certified")
    if isinstance(forbidden, list) and "external validation completed" not in forbidden:
        errors.append("public_narrative_hardening.forbidden_public_claims must block external validation completion")
    if isinstance(forbidden, list) and "procurement-grade cost estimate" not in forbidden:
        errors.append("public_narrative_hardening.forbidden_public_claims must block procurement-grade cost estimates")
    required = narrative.get("required_public_concepts")
    if not isinstance(required, list) or "non-certifying" not in required:
        errors.append("public_narrative_hardening.required_public_concepts must include non-certifying")
    if isinstance(required, list) and "deterministic artifact" not in required:
        errors.append("public_narrative_hardening.required_public_concepts must include deterministic artifact")
    browser = narrative.get("browser_boundary")
    if not isinstance(browser, Mapping):
        errors.append("public_narrative_hardening.browser_boundary must be object")
        browser = {}
    if browser.get("artifact_only_rendering") is not True:
        errors.append("public_narrative_hardening.browser_boundary.artifact_only_rendering must be true")
    for field in (
        "client_side_claim_recomputation_allowed",
        "blocked_claim_suppression_allowed",
        "external_gap_softening_allowed",
    ):
        if browser.get(field) is not False:
            errors.append(f"public_narrative_hardening.browser_boundary.{field} must be false")
    narrative_rollup = narrative.get("rollup")
    if not isinstance(narrative_rollup, Mapping):
        errors.append("public_narrative_hardening.rollup must be object")
        narrative_rollup = {}
    if narrative_rollup.get("unsafe_public_overclaim_count") != 0:
        errors.append("public_narrative_hardening.rollup.unsafe_public_overclaim_count must be 0")
    if narrative_rollup.get("all_required_concepts_present") is not True:
        errors.append("public_narrative_hardening.rollup.all_required_concepts_present must be true")
    for field in (
        "external_wording_audit_completed",
        "audience_testing_completed",
        "legal_review_completed",
        "public_claim_approval_completed",
        "external_validation_claimed",
    ):
        if narrative_rollup.get(field) is not False:
            errors.append(f"public_narrative_hardening.rollup.{field} must be false")

    external_ledger = payload.get("external_validation_execution_ledger")
    if not _is_object(external_ledger):
        errors.append("external_validation_execution_ledger must be an object")
        external_ledger = {}
    if external_ledger.get("schema_version") != "external_validation_execution_ledger.v1":
        errors.append("external_validation_execution_ledger.schema_version mismatch")
    if external_ledger.get("non_certification_notice") is not True:
        errors.append("external_validation_execution_ledger.non_certification_notice must be true")
    if (
        external_ledger.get("execution_ledger_status")
        != "repo_native_execution_ledger_ready_external_records_not_uploaded"
    ):
        errors.append("external_validation_execution_ledger status must keep external records absent")
    if external_ledger.get("review_case_count") != 7:
        errors.append("external_validation_execution_ledger.review_case_count must be 7")
    if external_ledger.get("execution_record_count") != 0:
        errors.append("external_validation_execution_ledger.execution_record_count must be 0")
    if external_ledger.get("external_record_count") != 0:
        errors.append("external_validation_execution_ledger.external_record_count must be 0")
    ledger_cases = external_ledger.get("execution_cases")
    if not isinstance(ledger_cases, list) or len(ledger_cases) != 7:
        errors.append("external_validation_execution_ledger.execution_cases must contain 7 rows")
    else:
        for index, row in enumerate(ledger_cases):
            if not isinstance(row, Mapping):
                errors.append(f"external_validation_execution_ledger.execution_cases[{index}] must be object")
                continue
            if row.get("execution_status") != "external_required":
                errors.append(
                    f"external_validation_execution_ledger.execution_cases[{index}].execution_status must be external_required"
                )
            if row.get("external_record_status") != "no_external_record_uploaded":
                errors.append(
                    "external_validation_execution_ledger.execution_cases"
                    f"[{index}].external_record_status must be no_external_record_uploaded"
                )
    ledger_rollup = external_ledger.get("rollup")
    if not isinstance(ledger_rollup, Mapping):
        errors.append("external_validation_execution_ledger.rollup must be object")
        ledger_rollup = {}
    for field in (
        "third_party_records_uploaded",
        "external_validation_completed",
        "independent_reproduction_completed",
        "external_red_team_completed",
    ):
        if ledger_rollup.get(field) is not False:
            errors.append(f"external_validation_execution_ledger.rollup.{field} must be false")

    physics_comparison = payload.get("independent_physics_backend_comparison")
    if not _is_object(physics_comparison):
        errors.append("independent_physics_backend_comparison must be an object")
        physics_comparison = {}
    if physics_comparison.get("schema_version") != "independent_physics_backend_comparison.v1":
        errors.append("independent_physics_backend_comparison.schema_version mismatch")
    if physics_comparison.get("non_certification_notice") is not True:
        errors.append("independent_physics_backend_comparison.non_certification_notice must be true")
    if physics_comparison.get("comparison_status") != "repo_analytic_crosscheck_ready_external_backend_open":
        errors.append("independent_physics_backend_comparison must keep external backend open")
    checks = physics_comparison.get("analytic_checks")
    if not isinstance(checks, list) or len(checks) < 4:
        errors.append("independent_physics_backend_comparison.analytic_checks must contain at least 4 rows")
        checks = []
    if physics_comparison.get("analytic_check_count") != len(checks):
        errors.append("independent_physics_backend_comparison.analytic_check_count mismatch")
    for index, check in enumerate(checks):
        if not isinstance(check, Mapping):
            errors.append(f"independent_physics_backend_comparison.analytic_checks[{index}] must be object")
            continue
        if check.get("status") != "match":
            errors.append(f"independent_physics_backend_comparison.analytic_checks[{index}].status must be match")
    physics_rollup = physics_comparison.get("rollup")
    if not isinstance(physics_rollup, Mapping):
        errors.append("independent_physics_backend_comparison.rollup must be object")
        physics_rollup = {}
    for field in (
        "independent_external_backend_complete",
        "cross_backend_comparison_completed",
        "high_fidelity_state_trace_complete",
        "independent_physics_backend_validated",
    ):
        if physics_rollup.get(field) is not False:
            errors.append(f"independent_physics_backend_comparison.rollup.{field} must be false")

    capsule_qualification = payload.get("capsule_qualification_evidence_pack")
    if not _is_object(capsule_qualification):
        errors.append("capsule_qualification_evidence_pack must be an object")
        capsule_qualification = {}
    if capsule_qualification.get("schema_version") != "capsule_qualification_evidence_pack.v1":
        errors.append("capsule_qualification_evidence_pack.schema_version mismatch")
    if capsule_qualification.get("non_certification_notice") is not True:
        errors.append("capsule_qualification_evidence_pack.non_certification_notice must be true")
    mass_closure = capsule_qualification.get("mass_closure")
    if not isinstance(mass_closure, Mapping):
        errors.append("capsule_qualification_evidence_pack.mass_closure must be object")
        mass_closure = {}
    if mass_closure.get("configured_capsule_mass_kg") != 206.0:
        errors.append("capsule_qualification_evidence_pack.mass_closure configured mass must be 206.0")
    if mass_closure.get("within_declared_margin") is not True:
        errors.append("capsule_qualification_evidence_pack.mass_closure must remain closed arithmetically")
    if capsule_qualification.get("qualification_test_count") != 6:
        errors.append("capsule_qualification_evidence_pack.qualification_test_count must be 6")
    if capsule_qualification.get("lab_record_count") != 0:
        errors.append("capsule_qualification_evidence_pack.lab_record_count must be 0")
    qualification_rollup = capsule_qualification.get("rollup")
    if not isinstance(qualification_rollup, Mapping):
        errors.append("capsule_qualification_evidence_pack.rollup must be object")
        qualification_rollup = {}
    for field in ("qualification_complete", "flight_ready_claimed", "certified_hardware_survivability"):
        if qualification_rollup.get(field) is not False:
            errors.append(f"capsule_qualification_evidence_pack.rollup.{field} must be false")

    evidence_closure = payload.get("evidence_upgrade_closure")
    if not _is_object(evidence_closure):
        errors.append("evidence_upgrade_closure must be an object")
        evidence_closure = {}
    if evidence_closure.get("schema_version") != "evidence_upgrade_closure.v1":
        errors.append("evidence_upgrade_closure.schema_version mismatch")
    if evidence_closure.get("non_certification_notice") is not True:
        errors.append("evidence_upgrade_closure.non_certification_notice must be true")
    if evidence_closure.get("closure_cycle_count") != 15:
        errors.append("evidence_upgrade_closure.closure_cycle_count must be 15")
    closure_rollup = evidence_closure.get("rollup")
    if not isinstance(closure_rollup, Mapping):
        errors.append("evidence_upgrade_closure.rollup must be object")
        closure_rollup = {}
    for field in ("external_source_upgrade_count", "trust_grade_promotion_count", "realistic_D_grade_public_rows_closed"):
        if closure_rollup.get(field) != 0:
            errors.append(f"evidence_upgrade_closure.rollup.{field} must be 0")
    for field in ("source_correctness_claimed", "trust_grades_upgraded_automatically"):
        if closure_rollup.get(field) is not False:
            errors.append(f"evidence_upgrade_closure.rollup.{field} must be false")

    reproduction_kit = payload.get("external_reproduction_kit")
    if not _is_object(reproduction_kit):
        errors.append("external_reproduction_kit must be an object")
        reproduction_kit = {}
    if reproduction_kit.get("schema_version") != "external_reproduction_kit.v1":
        errors.append("external_reproduction_kit.schema_version mismatch")
    if reproduction_kit.get("non_certification_notice") is not True:
        errors.append("external_reproduction_kit.non_certification_notice must be true")
    if reproduction_kit.get("kit_status") != "repo_native_reproduction_kit_ready_external_execution_open":
        errors.append("external_reproduction_kit must keep external execution open")
    if reproduction_kit.get("review_case_count") != 7:
        errors.append("external_reproduction_kit.review_case_count must be 7")
    kit_rollup = reproduction_kit.get("rollup")
    if not isinstance(kit_rollup, Mapping):
        errors.append("external_reproduction_kit.rollup must be object")
        kit_rollup = {}
    for field in ("external_reproduction_kit_ready", "export_cli_available", "record_schema_available"):
        if kit_rollup.get(field) is not True:
            errors.append(f"external_reproduction_kit.rollup.{field} must be true")
    for field in (
        "external_execution_completed",
        "first_real_external_record_present",
        "fake_external_records_accepted",
        "external_validation_completed",
        "independent_backend_validated",
    ):
        if kit_rollup.get(field) is not False:
            errors.append(f"external_reproduction_kit.rollup.{field} must be false")

    evidence_intake = payload.get("external_evidence_intake")
    if not _is_object(evidence_intake):
        errors.append("external_evidence_intake must be an object")
        evidence_intake = {}
    if evidence_intake.get("schema_version") != "external_evidence_intake.v1":
        errors.append("external_evidence_intake.schema_version mismatch")
    if evidence_intake.get("non_certification_notice") is not True:
        errors.append("external_evidence_intake.non_certification_notice must be true")
    if evidence_intake.get("intake_status") != "external_record_intake_ready_awaiting_external_submission":
        errors.append("external_evidence_intake must keep first external submission open")
    for field in ("record_count", "accepted_record_count", "rejected_record_count"):
        if evidence_intake.get(field) != 0:
            errors.append(f"external_evidence_intake.{field} must be 0")
    intake_policy = evidence_intake.get("validation_policy")
    if not isinstance(intake_policy, Mapping):
        errors.append("external_evidence_intake.validation_policy must be object")
        intake_policy = {}
    for field in ("reject_repository_maintainer_as_external", "reject_self_signed_repo_native_records"):
        if intake_policy.get(field) is not True:
            errors.append(f"external_evidence_intake.validation_policy.{field} must be true")
    intake_rollup = evidence_intake.get("rollup")
    if not isinstance(intake_rollup, Mapping):
        errors.append("external_evidence_intake.rollup must be object")
        intake_rollup = {}
    for field in (
        "first_real_external_record_present",
        "external_validation_completed",
        "independent_backend_validated",
        "qualification_complete",
        "certification_go",
    ):
        if intake_rollup.get(field) is not False:
            errors.append(f"external_evidence_intake.rollup.{field} must be false")

    validation_campaign = payload.get("external_validation_campaign")
    if not _is_object(validation_campaign):
        errors.append("external_validation_campaign must be an object")
        validation_campaign = {}
    if validation_campaign.get("schema_version") != "external_validation_campaign.v1":
        errors.append("external_validation_campaign.schema_version mismatch")
    if validation_campaign.get("non_certification_notice") is not True:
        errors.append("external_validation_campaign.non_certification_notice must be true")
    if validation_campaign.get("campaign_status") != "repo_campaign_ready_external_execution_required":
        errors.append("external_validation_campaign must keep external execution required")
    if validation_campaign.get("workstream_count") != 6:
        errors.append("external_validation_campaign.workstream_count must be 6")
    campaign_policy = validation_campaign.get("campaign_policy")
    if not isinstance(campaign_policy, Mapping):
        errors.append("external_validation_campaign.campaign_policy must be object")
        campaign_policy = {}
    for field in ("records_do_not_directly_unlock_claims", "proof_promotion_requires_followup_review"):
        if campaign_policy.get(field) is not True:
            errors.append(f"external_validation_campaign.campaign_policy.{field} must be true")
    campaign_rollup = validation_campaign.get("rollup")
    if not isinstance(campaign_rollup, Mapping):
        errors.append("external_validation_campaign.rollup must be object")
        campaign_rollup = {}
    if campaign_rollup.get("campaign_ready") is not True:
        errors.append("external_validation_campaign.rollup.campaign_ready must be true")
    if campaign_rollup.get("public_dossier_ready") is not True:
        errors.append("external_validation_campaign.rollup.public_dossier_ready must be true")
    for field in ("accepted_record_count", "accepted_external_record_count"):
        if campaign_rollup.get(field) != 0:
            errors.append(f"external_validation_campaign.rollup.{field} must be 0")
    for field in (
        "first_real_external_record_present",
        "external_validation_completed",
        "independent_backend_validated",
        "line_of_sight_model_complete",
        "qualification_complete",
        "proof_promotion_applied",
        "certification_go",
    ):
        if campaign_rollup.get(field) is not False:
            errors.append(f"external_validation_campaign.rollup.{field} must be false")
    proof_promotion = validation_campaign.get("proof_promotion_review")
    if not isinstance(proof_promotion, Mapping):
        errors.append("external_validation_campaign.proof_promotion_review must be object")
        proof_promotion = {}
    if proof_promotion.get("automatic_claim_promotion_allowed") is not False:
        errors.append("external_validation_campaign.proof_promotion_review.automatic_claim_promotion_allowed must be false")
    dossier = validation_campaign.get("public_evidence_dossier")
    if not isinstance(dossier, Mapping):
        errors.append("external_validation_campaign.public_evidence_dossier must be object")
        dossier = {}
    if dossier.get("marketing_claim_surface") is not False:
        errors.append("external_validation_campaign.public_evidence_dossier.marketing_claim_surface must be false")
    if dossier.get("certification_language_allowed") is not False:
        errors.append("external_validation_campaign.public_evidence_dossier.certification_language_allowed must be false")

    release_readiness = payload.get("release_candidate_readiness")
    if not _is_object(release_readiness):
        errors.append("release_candidate_readiness must be an object")
        release_readiness = {}
    if release_readiness.get("schema_version") != "release_candidate_readiness.v1":
        errors.append("release_candidate_readiness.schema_version mismatch")
    if release_readiness.get("non_certification_notice") is not True:
        errors.append("release_candidate_readiness.non_certification_notice must be true")
    if release_readiness.get("release_candidate_status") != "repo_publication_candidate_external_evidence_open":
        errors.append("release_candidate_readiness must keep external evidence open")
    release_rollup = release_readiness.get("rollup")
    if not isinstance(release_rollup, Mapping):
        errors.append("release_candidate_readiness.rollup must be object")
        release_rollup = {}
    if release_rollup.get("repo_publication_candidate_ready") is not True:
        errors.append("release_candidate_readiness.rollup.repo_publication_candidate_ready must be true")
    for field in (
        "certification_go",
        "flight_readiness_go",
        "external_validation_completed",
        "qualification_complete",
        "independent_backend_validated",
        "trust_grade_promotions_completed",
    ):
        if release_rollup.get(field) is not False:
            errors.append(f"release_candidate_readiness.rollup.{field} must be false")

    probability_coupling = payload.get("mission_probability_coupling")
    if not _is_object(probability_coupling):
        errors.append("mission_probability_coupling must be an object")
        probability_coupling = {}
    if probability_coupling.get("schema_version") != "mission_probability_coupling.v1":
        errors.append("mission_probability_coupling.schema_version mismatch")
    if probability_coupling.get("non_certification_notice") is not True:
        errors.append("mission_probability_coupling.non_certification_notice must be true")
    if probability_coupling.get("coupling_count") != 15:
        errors.append("mission_probability_coupling.coupling_count must be 15")
    rollup = probability_coupling.get("rollup")
    if not isinstance(rollup, Mapping) or rollup.get("rows_with_full_mission_probability_closed") != 0:
        errors.append("mission_probability_coupling.rollup must keep full mission probability open")
    coupling_rows = probability_coupling.get("coupling_rows")
    if not isinstance(coupling_rows, list) or len(coupling_rows) != 15:
        errors.append("mission_probability_coupling.coupling_rows must contain 15 rows")
    else:
        default_seen = False
        for index, row in enumerate(coupling_rows):
            if not isinstance(row, Mapping):
                errors.append(f"mission_probability_coupling.coupling_rows[{index}] must be object")
                continue
            if not isinstance(row.get("coupling_id"), str) or not str(row.get("coupling_id")).startswith("mpc-"):
                errors.append(f"mission_probability_coupling.coupling_rows[{index}].coupling_id must start with mpc-")
            if row.get("run_id") == probability_coupling.get("default_run_id"):
                default_seen = row.get("coupling_id") == probability_coupling.get("default_coupling_id")
            full = row.get("full_mission_probability")
            if not isinstance(full, Mapping) or full.get("status") != "not_closed_external_factors_open":
                errors.append(f"mission_probability_coupling.coupling_rows[{index}].full_mission_probability must remain open")
            elif any(full.get(key) is not None for key in ("p05", "p50", "p95")):
                errors.append(f"mission_probability_coupling.coupling_rows[{index}].full_mission_probability values must remain null")
            closed = row.get("closed_capsule_data_probability")
            if not isinstance(closed, Mapping) or closed.get("status") != "review_proxy_only":
                errors.append(f"mission_probability_coupling.coupling_rows[{index}].closed proxy status mismatch")
            elif not isinstance(closed.get("p50"), (int, float)) or not 0.0 <= float(closed["p50"]) <= 1.0:
                errors.append(f"mission_probability_coupling.coupling_rows[{index}].closed proxy p50 must be probability")
            if not isinstance(row.get("blocked_claims"), list) or "full mission probability closed" not in row["blocked_claims"]:
                errors.append(f"mission_probability_coupling.coupling_rows[{index}].blocked_claims must block closure")
            if not isinstance(row.get("external_evidence_gaps"), list) or not row["external_evidence_gaps"]:
                errors.append(f"mission_probability_coupling.coupling_rows[{index}].external_evidence_gaps must be non-empty")
        if not default_seen:
            errors.append("mission_probability_coupling.default_coupling_id must reference default run")

    uncertainty_interactions = payload.get("uncertainty_interactions")
    if not _is_object(uncertainty_interactions):
        errors.append("uncertainty_interactions must be an object")
        uncertainty_interactions = {}
    if uncertainty_interactions.get("schema_version") != "uncertainty_interactions.v1":
        errors.append("uncertainty_interactions.schema_version mismatch")
    if uncertainty_interactions.get("non_certification_notice") is not True:
        errors.append("uncertainty_interactions.non_certification_notice must be true")
    if uncertainty_interactions.get("mode") != "realistic":
        errors.append("uncertainty_interactions.mode must be realistic")
    if uncertainty_interactions.get("uncertainty_entry_count") != 4:
        errors.append("uncertainty_interactions.uncertainty_entry_count must be 4")
    if uncertainty_interactions.get("interaction_pair_count") != 6:
        errors.append("uncertainty_interactions.interaction_pair_count must be 6")
    rollup = uncertainty_interactions.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("uncertainty_interactions.rollup must be object")
    else:
        if rollup.get("validated_correlation_count") != 0:
            errors.append("uncertainty_interactions must not claim validated correlations")
        if rollup.get("full_uncertainty_interaction_closure") is not False:
            errors.append("uncertainty_interactions must keep full interaction closure false")
        if rollup.get("pairs_requiring_external_correlation_evidence") != 6:
            errors.append("uncertainty_interactions must require external evidence for all six pairs")
    main_effects = uncertainty_interactions.get("main_effects")
    if not isinstance(main_effects, list) or len(main_effects) != 4:
        errors.append("uncertainty_interactions.main_effects must contain 4 rows")
    else:
        for index, row in enumerate(main_effects):
            if not isinstance(row, Mapping):
                errors.append(f"uncertainty_interactions.main_effects[{index}] must be object")
                continue
            parameter_id = row.get("parameter_id")
            if not isinstance(parameter_id, str) or parameter_id not in registry_lookup:
                errors.append(f"uncertainty_interactions.main_effects[{index}].parameter_id not found in registry")
            if not isinstance(row.get("max_abs_effect"), (int, float)) or float(row.get("max_abs_effect", -1.0)) < 0.0:
                errors.append(f"uncertainty_interactions.main_effects[{index}].max_abs_effect must be >= 0")
    pair_interactions = uncertainty_interactions.get("pair_interactions")
    if not isinstance(pair_interactions, list) or len(pair_interactions) != 6:
        errors.append("uncertainty_interactions.pair_interactions must contain 6 rows")
    else:
        for index, row in enumerate(pair_interactions):
            if not isinstance(row, Mapping):
                errors.append(f"uncertainty_interactions.pair_interactions[{index}] must be object")
                continue
            if row.get("status") != "external_correlation_evidence_required":
                errors.append(f"uncertainty_interactions.pair_interactions[{index}].status must remain open")
            residual = row.get("interaction_residual")
            if not isinstance(residual, Mapping) or residual.get("classification") not in {"negligible", "weak", "material"}:
                errors.append(f"uncertainty_interactions.pair_interactions[{index}].interaction_residual classification invalid")
            correlation = row.get("correlation")
            if not isinstance(correlation, Mapping) or correlation.get("rho") is not None:
                errors.append(f"uncertainty_interactions.pair_interactions[{index}].correlation.rho must be null")
    blocked = uncertainty_interactions.get("blocked_claims")
    if not isinstance(blocked, list) or "validated uncertainty independence" not in blocked:
        errors.append("uncertainty_interactions.blocked_claims must block validated independence")
    gaps = uncertainty_interactions.get("external_evidence_gaps")
    if not isinstance(gaps, list) or not gaps:
        errors.append("uncertainty_interactions.external_evidence_gaps must be non-empty")

    evidence_upgrade = payload.get("evidence_upgrade_campaign")
    if not _is_object(evidence_upgrade):
        errors.append("evidence_upgrade_campaign must be an object")
        evidence_upgrade = {}
    if evidence_upgrade.get("schema_version") != "evidence_upgrade_campaign.v1":
        errors.append("evidence_upgrade_campaign.schema_version mismatch")
    if evidence_upgrade.get("non_certification_notice") is not True:
        errors.append("evidence_upgrade_campaign.non_certification_notice must be true")
    if evidence_upgrade.get("claim_count") != 66:
        errors.append("evidence_upgrade_campaign.claim_count must be 66")
    if evidence_upgrade.get("public_campaign_count") != 31:
        errors.append("evidence_upgrade_campaign.public_campaign_count must be 31")
    if evidence_upgrade.get("internal_audit_count") != 35:
        errors.append("evidence_upgrade_campaign.internal_audit_count must be 35")
    if evidence_upgrade.get("trust_distribution") != {"B": 8, "C": 56, "D": 2}:
        errors.append("evidence_upgrade_campaign.trust_distribution mismatch")
    if evidence_upgrade.get("public_trust_distribution") != {"B": 8, "C": 21, "D": 2}:
        errors.append("evidence_upgrade_campaign.public_trust_distribution mismatch")
    public_top = evidence_upgrade.get("public_top_priorities")
    if not isinstance(public_top, list) or not public_top:
        errors.append("evidence_upgrade_campaign.public_top_priorities must be non-empty")
    else:
        previous_score: float | None = None
        for index, row in enumerate(public_top):
            if not isinstance(row, Mapping):
                errors.append(f"evidence_upgrade_campaign.public_top_priorities[{index}] must be object")
                continue
            parameter_id = row.get("parameter_id")
            if not isinstance(parameter_id, str) or parameter_id.startswith("code_literal."):
                errors.append(f"evidence_upgrade_campaign public row leaks internal parameter: {parameter_id!r}")
            if row.get("visibility") != "public":
                errors.append(f"evidence_upgrade_campaign.public_top_priorities[{index}].visibility must be public")
            score = row.get("priority_score")
            if not isinstance(score, (int, float)) or isinstance(score, bool) or float(score) < 0.0:
                errors.append(f"evidence_upgrade_campaign.public_top_priorities[{index}].priority_score invalid")
                continue
            if previous_score is not None and float(score) > previous_score + 1e-12:
                errors.append("evidence_upgrade_campaign.public_top_priorities must be sorted")
            previous_score = float(score)
    blocked = evidence_upgrade.get("blocked_claims")
    if not isinstance(blocked, list) or "trust grades upgraded automatically" not in blocked:
        errors.append("evidence_upgrade_campaign.blocked_claims must block automatic upgrades")
    if isinstance(blocked, list) and "source correctness proven" not in blocked:
        errors.append("evidence_upgrade_campaign.blocked_claims must block source correctness proof")
    gaps = evidence_upgrade.get("external_evidence_gaps")
    if not isinstance(gaps, list) or not gaps:
        errors.append("evidence_upgrade_campaign.external_evidence_gaps must be non-empty")

    dag_boundary = payload.get("mission_dag_v2_boundary")
    if not _is_object(dag_boundary):
        errors.append("mission_dag_v2_boundary must be an object")
        dag_boundary = {}
    if dag_boundary.get("schema_version") != "mission_dag_v2_boundary.v1":
        errors.append("mission_dag_v2_boundary.schema_version mismatch")
    if dag_boundary.get("non_certification_notice") is not True:
        errors.append("mission_dag_v2_boundary.non_certification_notice must be true")
    if dag_boundary.get("module_count") != 6:
        errors.append("mission_dag_v2_boundary.module_count must be 6")
    rollup = dag_boundary.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("mission_dag_v2_boundary.rollup must be object")
        rollup = {}
    if rollup.get("state_trace_contract_complete") is not True:
        errors.append("mission_dag_v2_boundary.rollup.state_trace_contract_complete must be true")
    for field in (
        "independent_backend_complete",
        "high_fidelity_state_traces_available",
        "cross_backend_comparison_available",
        "external_reproduction_completed",
    ):
        if rollup.get(field) is not False:
            errors.append(f"mission_dag_v2_boundary.rollup.{field} must be false")
    rows = dag_boundary.get("module_boundaries")
    if not isinstance(rows, list) or len(rows) != 6:
        errors.append("mission_dag_v2_boundary.module_boundaries must contain 6 rows")
        rows = []
    module_ids: List[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"mission_dag_v2_boundary.module_boundaries[{index}] must be object")
            continue
        module_id = row.get("module_id")
        if not isinstance(module_id, str) or not module_id:
            errors.append(f"mission_dag_v2_boundary.module_boundaries[{index}].module_id must be non-empty")
        else:
            module_ids.append(module_id)
        if not isinstance(row.get("scenario_node_ids"), list) or not row["scenario_node_ids"]:
            errors.append(f"mission_dag_v2_boundary.module_boundaries[{index}].scenario_node_ids must be non-empty")
        if not isinstance(row.get("failure_taxonomy_ids"), list) or not row["failure_taxonomy_ids"]:
            errors.append(f"mission_dag_v2_boundary.module_boundaries[{index}].failure_taxonomy_ids must be non-empty")
        requirements = row.get("v2_boundary_requirements")
        if not isinstance(requirements, list) or "state trace hash" not in requirements:
            errors.append(f"mission_dag_v2_boundary.module_boundaries[{index}].v2_boundary_requirements must include state trace hash")
        current = row.get("current_v1_support")
        if not isinstance(current, Mapping) or current.get("independent_backend_id_declared") is not False:
            errors.append(f"mission_dag_v2_boundary.module_boundaries[{index}] must keep independent backend open")
    if len(module_ids) != len(set(module_ids)):
        errors.append("mission_dag_v2_boundary module ids must be unique")
    blocked = dag_boundary.get("blocked_claims")
    if not isinstance(blocked, list) or "independent physics backend validated" not in blocked:
        errors.append("mission_dag_v2_boundary.blocked_claims must block independent backend validation")
    if isinstance(blocked, list) and "flight-ready module approved" not in blocked:
        errors.append("mission_dag_v2_boundary.blocked_claims must block flight-ready module approval")

    return errors


def build_browser_dataset(
    *,
    repo_root: Path,
    determinism_status_path: Path,
    failure_surface_path: Path,
    manifest_path: Path,
    static_graph_path: Path,
    evidence_index_path: Path,
    p_success_defensibility_path: Path,
    objective_score_path: Path,
    optimization_search_space_path: Path,
    optimization_frontier_path: Path,
    output_path: Path,
    optimization_v2_path: Path = DEFAULT_OPTIMIZATION_V2,
    capsule_survivability_path: Path = DEFAULT_CAPSULE_SURVIVABILITY,
    capsule_risk_budget_path: Path = DEFAULT_CAPSULE_RISK_BUDGET,
    mission_feasibility_path: Path = DEFAULT_MISSION_FEASIBILITY,
    user_mission_run_catalog_path: Path = DEFAULT_USER_MISSION_RUN_CATALOG,
    runtime_scenario_generation_path: Path = DEFAULT_RUNTIME_SCENARIO_GENERATION,
    cost_procurement_architecture_path: Path = DEFAULT_COST_PROCUREMENT_ARCHITECTURE,
    external_validation_review_pack_path: Path = DEFAULT_EXTERNAL_VALIDATION_REVIEW_PACK,
    public_narrative_hardening_path: Path = DEFAULT_PUBLIC_NARRATIVE_HARDENING,
    external_validation_execution_ledger_path: Path = DEFAULT_EXTERNAL_VALIDATION_EXECUTION_LEDGER,
    independent_physics_backend_comparison_path: Path = DEFAULT_INDEPENDENT_PHYSICS_BACKEND_COMPARISON,
    capsule_qualification_evidence_pack_path: Path = DEFAULT_CAPSULE_QUALIFICATION_EVIDENCE_PACK,
    evidence_upgrade_closure_path: Path = DEFAULT_EVIDENCE_UPGRADE_CLOSURE,
    external_reproduction_kit_path: Path = DEFAULT_EXTERNAL_REPRODUCTION_KIT,
    external_evidence_intake_path: Path = DEFAULT_EXTERNAL_EVIDENCE_INTAKE,
    external_validation_campaign_path: Path = DEFAULT_EXTERNAL_VALIDATION_CAMPAIGN,
    release_candidate_readiness_path: Path = DEFAULT_RELEASE_CANDIDATE_READINESS,
    mission_probability_coupling_path: Path = DEFAULT_MISSION_PROBABILITY_COUPLING,
    uncertainty_interactions_path: Path = DEFAULT_UNCERTAINTY_INTERACTIONS,
    evidence_upgrade_campaign_path: Path = DEFAULT_EVIDENCE_UPGRADE_CAMPAIGN,
    mission_dag_v2_boundary_path: Path = DEFAULT_MISSION_DAG_V2_BOUNDARY,
    roadmap_closure_path: Path = DEFAULT_ROADMAP_CLOSURE,
) -> Dict[str, Any]:
    determinism_status = load_json(repo_root / determinism_status_path)
    failure_surface = load_json(repo_root / failure_surface_path)
    manifest = load_json(repo_root / manifest_path)
    static_graph = load_json(repo_root / static_graph_path)
    evidence_index = load_json(repo_root / evidence_index_path)
    p_success_defensibility = load_json(repo_root / p_success_defensibility_path)
    objective_score = load_json(repo_root / objective_score_path)
    optimization_search_space = load_json(repo_root / optimization_search_space_path)
    optimization_frontier = load_json(repo_root / optimization_frontier_path)
    optimization_v2 = load_json(repo_root / optimization_v2_path)
    capsule_survivability = load_json(repo_root / capsule_survivability_path)
    capsule_risk_budget = load_json(repo_root / capsule_risk_budget_path)
    mission_feasibility = load_json(repo_root / mission_feasibility_path)
    user_mission_run_catalog = load_json(repo_root / user_mission_run_catalog_path)
    runtime_scenario_generation = load_json(repo_root / runtime_scenario_generation_path)
    cost_procurement_architecture = load_json(repo_root / cost_procurement_architecture_path)
    external_validation_review_pack = load_json(repo_root / external_validation_review_pack_path)
    public_narrative_hardening = load_json(repo_root / public_narrative_hardening_path)
    external_validation_execution_ledger = load_json(repo_root / external_validation_execution_ledger_path)
    independent_physics_backend_comparison = load_json(repo_root / independent_physics_backend_comparison_path)
    capsule_qualification_evidence_pack = load_json(repo_root / capsule_qualification_evidence_pack_path)
    evidence_upgrade_closure = load_json(repo_root / evidence_upgrade_closure_path)
    external_reproduction_kit = load_json(repo_root / external_reproduction_kit_path)
    external_evidence_intake = load_json(repo_root / external_evidence_intake_path)
    external_validation_campaign = load_json(repo_root / external_validation_campaign_path)
    release_candidate_readiness = load_json(repo_root / release_candidate_readiness_path)
    mission_probability_coupling = load_json(repo_root / mission_probability_coupling_path)
    uncertainty_interactions = load_json(repo_root / uncertainty_interactions_path)
    evidence_upgrade_campaign = load_json(repo_root / evidence_upgrade_campaign_path)
    mission_dag_v2_boundary = load_json(repo_root / mission_dag_v2_boundary_path)
    roadmap_closure = load_json(repo_root / roadmap_closure_path)

    payload = {
        "schema_version": "browser_dataset.v1",
        "generator": "scripts/build_browser_dataset_artifact.py",
        "public_scope": "tracked_generated_only",
        "source_paths": dict(PUBLIC_DATASET_PATHS),
        "source_artifacts": [
            {
                "path": str(path),
                "sha256": _sha256_file(repo_root / path),
            }
            for path in [
                determinism_status_path,
                failure_surface_path,
                manifest_path,
                static_graph_path,
                evidence_index_path,
                p_success_defensibility_path,
                objective_score_path,
                optimization_search_space_path,
                optimization_frontier_path,
                optimization_v2_path,
                capsule_survivability_path,
                capsule_risk_budget_path,
                mission_feasibility_path,
                user_mission_run_catalog_path,
                runtime_scenario_generation_path,
                cost_procurement_architecture_path,
                external_validation_review_pack_path,
                public_narrative_hardening_path,
                external_validation_execution_ledger_path,
                independent_physics_backend_comparison_path,
                capsule_qualification_evidence_pack_path,
                evidence_upgrade_closure_path,
                external_reproduction_kit_path,
                external_evidence_intake_path,
                external_validation_campaign_path,
                release_candidate_readiness_path,
                mission_probability_coupling_path,
                uncertainty_interactions_path,
                evidence_upgrade_campaign_path,
                mission_dag_v2_boundary_path,
                roadmap_closure_path,
            ]
        ],
        "determinism_status": determinism_status,
        "failure_surface_baseline": failure_surface,
        "manifest": manifest,
        "static_usage_graph": static_graph,
        "evidence_index": evidence_index,
        "p_success_defensibility": p_success_defensibility,
        "objective_contract": objective_score.get("contract_snapshot"),
        "objective_score_baseline": objective_score,
        "optimization_search_space": optimization_search_space,
        "optimization_frontier": optimization_frontier,
        "optimization_v2": _optimization_v2_summary(optimization_v2),
        "capsule_survivability_lab": capsule_survivability,
        "capsule_risk_budget": _capsule_risk_budget_summary(capsule_risk_budget),
        "mission_feasibility_screen": _mission_feasibility_summary(mission_feasibility),
        "user_mission_run_catalog": _user_mission_run_catalog_summary(user_mission_run_catalog),
        "runtime_scenario_generation": _runtime_scenario_generation_summary(runtime_scenario_generation),
        "cost_procurement_architecture_feasibility": _cost_procurement_architecture_summary(
            cost_procurement_architecture
        ),
        "external_validation_review_pack": _external_validation_review_pack_summary(external_validation_review_pack),
        "public_narrative_hardening": _public_narrative_hardening_summary(public_narrative_hardening),
        "external_validation_execution_ledger": _external_validation_execution_ledger_summary(
            external_validation_execution_ledger
        ),
        "independent_physics_backend_comparison": _independent_physics_backend_comparison_summary(
            independent_physics_backend_comparison
        ),
        "capsule_qualification_evidence_pack": _capsule_qualification_evidence_pack_summary(
            capsule_qualification_evidence_pack
        ),
        "evidence_upgrade_closure": _evidence_upgrade_closure_summary(evidence_upgrade_closure),
        "external_reproduction_kit": _external_reproduction_kit_summary(external_reproduction_kit),
        "external_evidence_intake": _external_evidence_intake_summary(external_evidence_intake),
        "external_validation_campaign": _external_validation_campaign_summary(external_validation_campaign),
        "release_candidate_readiness": _release_candidate_readiness_summary(release_candidate_readiness),
        "mission_probability_coupling": _mission_probability_coupling_summary(mission_probability_coupling),
        "uncertainty_interactions": _uncertainty_interactions_summary(uncertainty_interactions),
        "evidence_upgrade_campaign": _evidence_upgrade_campaign_summary(evidence_upgrade_campaign),
        "mission_dag_v2_boundary": _mission_dag_v2_boundary_summary(mission_dag_v2_boundary),
        "roadmap_closure": _roadmap_closure_summary(roadmap_closure),
    }
    errors = validate_browser_dataset(payload=payload, repo_root=repo_root)

    output_abs = repo_root / output_path
    if errors:
        return {
            "status": "FAIL",
            "browser_dataset_sha256": None,
            "parameter_count": int(manifest.get("parameter_count", 0)),
            "errors": errors,
        }

    write_json(output_abs, payload)
    return {
        "status": "PASS",
        "browser_dataset_sha256": _sha256_file(output_abs),
        "parameter_count": int(manifest.get("parameter_count", 0)),
        "errors": errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--determinism-status", default=str(DEFAULT_DETERMINISM_STATUS))
    parser.add_argument("--failure-surface", default=str(DEFAULT_FAILURE_SURFACE))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--static-graph", default=str(DEFAULT_STATIC_GRAPH))
    parser.add_argument("--evidence-index", default=str(DEFAULT_EVIDENCE_INDEX))
    parser.add_argument("--p-success-defensibility", default=str(DEFAULT_P_SUCCESS_DEFENSIBILITY))
    parser.add_argument("--objective-score", default=str(DEFAULT_OBJECTIVE_SCORE))
    parser.add_argument("--optimization-search-space", default=str(DEFAULT_OPTIMIZATION_SEARCH_SPACE))
    parser.add_argument("--optimization-frontier", default=str(DEFAULT_OPTIMIZATION_FRONTIER))
    parser.add_argument("--optimization-v2", default=str(DEFAULT_OPTIMIZATION_V2))
    parser.add_argument("--capsule-survivability", default=str(DEFAULT_CAPSULE_SURVIVABILITY))
    parser.add_argument("--capsule-risk-budget", default=str(DEFAULT_CAPSULE_RISK_BUDGET))
    parser.add_argument("--mission-feasibility", default=str(DEFAULT_MISSION_FEASIBILITY))
    parser.add_argument("--user-mission-run-catalog", default=str(DEFAULT_USER_MISSION_RUN_CATALOG))
    parser.add_argument("--runtime-scenario-generation", default=str(DEFAULT_RUNTIME_SCENARIO_GENERATION))
    parser.add_argument("--cost-procurement-architecture", default=str(DEFAULT_COST_PROCUREMENT_ARCHITECTURE))
    parser.add_argument("--external-validation-review-pack", default=str(DEFAULT_EXTERNAL_VALIDATION_REVIEW_PACK))
    parser.add_argument("--public-narrative-hardening", default=str(DEFAULT_PUBLIC_NARRATIVE_HARDENING))
    parser.add_argument("--external-validation-execution-ledger", default=str(DEFAULT_EXTERNAL_VALIDATION_EXECUTION_LEDGER))
    parser.add_argument(
        "--independent-physics-backend-comparison",
        default=str(DEFAULT_INDEPENDENT_PHYSICS_BACKEND_COMPARISON),
    )
    parser.add_argument(
        "--capsule-qualification-evidence-pack",
        default=str(DEFAULT_CAPSULE_QUALIFICATION_EVIDENCE_PACK),
    )
    parser.add_argument("--evidence-upgrade-closure", default=str(DEFAULT_EVIDENCE_UPGRADE_CLOSURE))
    parser.add_argument("--external-reproduction-kit", default=str(DEFAULT_EXTERNAL_REPRODUCTION_KIT))
    parser.add_argument("--external-evidence-intake", default=str(DEFAULT_EXTERNAL_EVIDENCE_INTAKE))
    parser.add_argument("--external-validation-campaign", default=str(DEFAULT_EXTERNAL_VALIDATION_CAMPAIGN))
    parser.add_argument("--release-candidate-readiness", default=str(DEFAULT_RELEASE_CANDIDATE_READINESS))
    parser.add_argument("--mission-probability-coupling", default=str(DEFAULT_MISSION_PROBABILITY_COUPLING))
    parser.add_argument("--uncertainty-interactions", default=str(DEFAULT_UNCERTAINTY_INTERACTIONS))
    parser.add_argument("--evidence-upgrade-campaign", default=str(DEFAULT_EVIDENCE_UPGRADE_CAMPAIGN))
    parser.add_argument("--mission-dag-v2-boundary", default=str(DEFAULT_MISSION_DAG_V2_BOUNDARY))
    parser.add_argument("--roadmap-closure", default=str(DEFAULT_ROADMAP_CLOSURE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    result = build_browser_dataset(
        repo_root=repo_root,
        determinism_status_path=Path(args.determinism_status),
        failure_surface_path=Path(args.failure_surface),
        manifest_path=Path(args.manifest),
        static_graph_path=Path(args.static_graph),
        evidence_index_path=Path(args.evidence_index),
        p_success_defensibility_path=Path(args.p_success_defensibility),
        objective_score_path=Path(args.objective_score),
        optimization_search_space_path=Path(args.optimization_search_space),
        optimization_frontier_path=Path(args.optimization_frontier),
        optimization_v2_path=Path(args.optimization_v2),
        capsule_survivability_path=Path(args.capsule_survivability),
        capsule_risk_budget_path=Path(args.capsule_risk_budget),
        mission_feasibility_path=Path(args.mission_feasibility),
        user_mission_run_catalog_path=Path(args.user_mission_run_catalog),
        runtime_scenario_generation_path=Path(args.runtime_scenario_generation),
        cost_procurement_architecture_path=Path(args.cost_procurement_architecture),
        external_validation_review_pack_path=Path(args.external_validation_review_pack),
        public_narrative_hardening_path=Path(args.public_narrative_hardening),
        external_validation_execution_ledger_path=Path(args.external_validation_execution_ledger),
        independent_physics_backend_comparison_path=Path(args.independent_physics_backend_comparison),
        capsule_qualification_evidence_pack_path=Path(args.capsule_qualification_evidence_pack),
        evidence_upgrade_closure_path=Path(args.evidence_upgrade_closure),
        external_reproduction_kit_path=Path(args.external_reproduction_kit),
        external_evidence_intake_path=Path(args.external_evidence_intake),
        external_validation_campaign_path=Path(args.external_validation_campaign),
        release_candidate_readiness_path=Path(args.release_candidate_readiness),
        mission_probability_coupling_path=Path(args.mission_probability_coupling),
        uncertainty_interactions_path=Path(args.uncertainty_interactions),
        evidence_upgrade_campaign_path=Path(args.evidence_upgrade_campaign),
        mission_dag_v2_boundary_path=Path(args.mission_dag_v2_boundary),
        roadmap_closure_path=Path(args.roadmap_closure),
        output_path=Path(args.output),
    )

    if args.format == "json":
        print(render_json(result))
    else:
        print(f"{result['status']}: browser dataset artifact")
        print(f"- parameter_count: {result['parameter_count']}")
        if result["browser_dataset_sha256"]:
            print(f"- browser_dataset_sha256: {result['browser_dataset_sha256']}")
        if result["errors"]:
            print(f"- errors: {len(result['errors'])}")
            for error in result["errors"]:
                print(f"  - {error}")

    return 0 if not result["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
