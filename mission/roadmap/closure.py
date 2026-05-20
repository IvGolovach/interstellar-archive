"""Deterministic closure artifact for the 15-item v2 roadmap.

The artifact is deliberately a repository-native implementation contract, not
an external hardware qualification claim. It converts the roadmap into
machine-checkable capabilities, model summaries, validation hooks, and remaining
evidence gaps.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


SCHEMA_VERSION = "roadmap_closure.v1"
GENERATOR = "scripts/build_roadmap_closure_artifact.py"
PUBLIC_SCOPE = "full_v2_roadmap_repo_native_closure"
YEAR_S = 365.25 * 24.0 * 3600.0
LIGHT_YEAR_M = 9_460_730_472_580_800.0
G = 6.67430e-11
C = 299_792_458.0

REQUIRED_ITEM_IDS = tuple(f"roadmap-{index:02d}" for index in range(1, 16))
ITEM_STATUS = "repo_native_closure_implemented_external_evidence_open"


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_artifacts(repo_root: Path, paths: Sequence[str]) -> List[Dict[str, str]]:
    return [{"path": path, "sha256": _sha256_file(repo_root / path)} for path in paths]


def _kerr_summary(baseline: Mapping[str, Any]) -> Dict[str, Any]:
    mass_kg = float(baseline["bh_parameters"]["mass_kg"])
    spin_dimensionless = 0.65
    r_g = G * mass_kg / (C**2)
    r_plus = r_g * (1.0 + math.sqrt(1.0 - spin_dimensionless**2))
    schwarzschild = 2.0 * r_g
    return {
        "model": "deterministic_kerr_horizon_screen_v1",
        "mass_kg": _round(mass_kg),
        "spin_dimensionless_reference": spin_dimensionless,
        "gravitational_radius_m": _round(r_g),
        "schwarzschild_radius_m": _round(schwarzschild),
        "kerr_outer_horizon_m": _round(r_plus),
        "outer_horizon_vs_schwarzschild_ratio": _round(r_plus / schwarzschild),
        "implemented_boundary": "metric-screening contract; not full geodesic integration or MHD",
    }


def _trajectory_summary() -> Dict[str, Any]:
    speeds_km_s = [23.17, 33.75, 45.32, 60.0, 95.0]
    distances_ly = {
        "proxima_scale": 4.2465,
        "reference_black_hole_proxy": 1560.0,
        "galactic_center_rounded": 26000.0,
    }
    tof: Dict[str, Dict[str, float]] = {}
    for target_id, distance_ly in distances_ly.items():
        tof[target_id] = {}
        for speed in speeds_km_s:
            years = distance_ly * LIGHT_YEAR_M / (speed * 1000.0) / YEAR_S
            tof[target_id][f"{speed:g}_km_s"] = _round(years, 3)
    return {
        "model": "ballistic_reachability_table_v1",
        "speed_grid_km_s": speeds_km_s,
        "target_distances_ly": distances_ly,
        "time_of_flight_years": tof,
        "navigation_boundary": "flight time is computed; target acquisition and ephemeris validity remain separate gaps",
    }


def _dust_summary(capsule: Mapping[str, Any]) -> Dict[str, Any]:
    area_entry = capsule["capsule_design"]["survivability_model_inputs"]["frontal_area_m2"]
    area = float(area_entry.get("value", area_entry))
    density_kg_m3 = 2.1e-24
    path_ly = 1560.0
    velocity_km_s = 45.32
    swept_kg = density_kg_m3 * area * path_ly * LIGHT_YEAR_M
    specific_energy_j_kg = 0.5 * (velocity_km_s * 1000.0) ** 2
    kinetic_energy_j = swept_kg * specific_energy_j_kg
    return {
        "model": "local_ism_dust_tail_screen_v1",
        "source_backed_mass_density_kg_m3": density_kg_m3,
        "reference_path_ly": path_ly,
        "frontal_area_m2": _round(area),
        "velocity_km_s": velocity_km_s,
        "swept_dust_mass_kg": _round(swept_kg),
        "swept_specific_energy_j_kg": _round(specific_energy_j_kg),
        "swept_kinetic_energy_j": _round(kinetic_energy_j),
        "tail_boundary": "micron-class local anchor only; mm/cm tail remains explicit sensitivity",
    }


def _radiation_material_summary(capsule_risk: Mapping[str, Any]) -> Dict[str, Any]:
    dimensions = {
        str(item.get("id")): item
        for item in capsule_risk.get("uncertainty_dimensions", [])
        if isinstance(item, Mapping)
    }
    mode_count = len(capsule_risk.get("attack_modes", {}).get("modes", []))
    return {
        "model": "material_radiation_transport_hook_v1",
        "radiation_dimension_present": "radiation" in dimensions,
        "plasma_dimension_present": "plasma" in dimensions,
        "material_degradation_dimension_present": "material_degradation" in dimensions,
        "media_margin_dimension_present": "media_margin" in dimensions,
        "attack_mode_count": mode_count,
        "transport_boundary": "declares material/radiation hooks; does not replace particle transport or stack testing",
    }


def _uncertainty_summary(uncertainty_interactions: Mapping[str, Any]) -> Dict[str, Any]:
    main_effects = uncertainty_interactions.get("main_effects", [])
    pair_interactions = uncertainty_interactions.get("pair_interactions", [])
    dimension_ids = [
        str(item.get("parameter_id"))
        for item in main_effects
        if isinstance(item, Mapping) and isinstance(item.get("parameter_id"), str)
    ]
    dominant_pair: Mapping[str, Any] = {}
    rollup = uncertainty_interactions.get("rollup", {})
    dominant_pair_id = rollup.get("dominant_pair_id") if isinstance(rollup, Mapping) else None
    if isinstance(pair_interactions, list) and isinstance(dominant_pair_id, str):
        dominant_pair = next(
            (
                item
                for item in pair_interactions
                if isinstance(item, Mapping) and item.get("pair_id") == dominant_pair_id
            ),
            {},
        )
    return {
        "model": "artifact_backed_pairwise_uncertainty_interactions_v1",
        "artifact_ref": "artifacts/uncertainty_interactions.v1.json",
        "schema_version": uncertainty_interactions.get("schema_version"),
        "dimension_count": uncertainty_interactions.get("uncertainty_entry_count"),
        "dimension_ids": dimension_ids,
        "interaction_pair_count": uncertainty_interactions.get("interaction_pair_count"),
        "dominant_pair_id": dominant_pair_id,
        "dominant_pair_residual": dominant_pair.get("interaction_residual", {}),
        "validated_correlation_count": rollup.get("validated_correlation_count") if isinstance(rollup, Mapping) else None,
        "full_uncertainty_interaction_closure": rollup.get("full_uncertainty_interaction_closure")
        if isinstance(rollup, Mapping)
        else None,
        "external_evidence_gaps": uncertainty_interactions.get("external_evidence_gaps", []),
        "interaction_method": uncertainty_interactions.get("method", {}).get("name")
        if isinstance(uncertainty_interactions.get("method"), Mapping)
        else None,
        "tail_metric_ready": ["p05", "p01", "loss_probability"],
        "boundary": "pairwise residuals are tracked; validated covariance/correlation evidence remains external",
    }


def _evidence_upgrade_summary(evidence_upgrade_campaign: Mapping[str, Any]) -> Dict[str, Any]:
    top_priorities = evidence_upgrade_campaign.get("top_priorities", [])
    if not isinstance(top_priorities, list):
        top_priorities = []
    public_rows = evidence_upgrade_campaign.get("public_campaign_rows", [])
    if not isinstance(public_rows, list):
        public_rows = []
    rollup = evidence_upgrade_campaign.get("rollup", {})
    if not isinstance(rollup, Mapping):
        rollup = {}
    return {
        "model": "artifact_backed_evidence_upgrade_campaign_v1",
        "status": "implemented_as_tracked_campaign_ledger",
        "artifact_ref": "artifacts/evidence_upgrade_campaign.v1.json",
        "schema_version": evidence_upgrade_campaign.get("schema_version"),
        "claim_count": evidence_upgrade_campaign.get("claim_count"),
        "public_campaign_count": evidence_upgrade_campaign.get("public_campaign_count"),
        "internal_audit_count": evidence_upgrade_campaign.get("internal_audit_count"),
        "trust_grade_distribution": evidence_upgrade_campaign.get("trust_distribution", {}),
        "public_trust_distribution": evidence_upgrade_campaign.get("public_trust_distribution", {}),
        "top_priority_count": evidence_upgrade_campaign.get("top_priority_count"),
        "top_priority_ids": [
            str(row.get("parameter_id"))
            for row in top_priorities[:5]
            if isinstance(row, Mapping) and isinstance(row.get("parameter_id"), str)
        ],
        "public_upgrade_candidate_count": rollup.get("public_upgrade_candidate_count"),
        "speculative_quarantine_count": rollup.get("speculative_quarantine_count"),
        "external_evidence_gaps": evidence_upgrade_campaign.get("external_evidence_gaps", []),
        "blocked_claims": evidence_upgrade_campaign.get("blocked_claims", []),
        "boundary": "campaign ranks evidence review work; it does not promote trust grades or certify source correctness",
    }


def _mission_coupling_summary(
    baseline: Mapping[str, Any],
    capsule_risk: Mapping[str, Any],
    probability_coupling: Mapping[str, Any],
) -> Dict[str, Any]:
    default_row_id = capsule_risk.get("default_row_id")
    nominal = next(
        (
            row
            for row in capsule_risk.get("risk_budgets", [])
            if row.get("row_id") == default_row_id and row.get("attack_mode_id") == "nominal"
        ),
        {},
    )
    p_hit = 1.0
    p_survive = float(nominal.get("risk_budget", {}).get("survival_probability", 0.0))
    p_data_intact = float(nominal.get("risk_budget", {}).get("data_integrity_probability", 0.0))
    return {
        "model": "tracked_mission_probability_coupling_v1",
        "formula": probability_coupling.get("formula", "P_success = P_hit * P_survive * P_data_intact"),
        "reference_row_id": default_row_id,
        "artifact_ref": "artifacts/mission_probability_coupling.v1.json",
        "coupling_count": probability_coupling.get("coupling_count"),
        "default_coupling_id": probability_coupling.get("default_coupling_id"),
        "full_mission_probability_status": probability_coupling.get("factor_policy", {}).get("full_mission_probability_status"),
        "p_hit_reference": p_hit,
        "p_survive_reference": _round(p_survive),
        "p_data_intact_reference": _round(p_data_intact),
        "coupled_reference_probability": _round(p_hit * p_survive * p_data_intact),
        "baseline_success_threshold": baseline.get("success_threshold"),
        "coupling_boundary": "factor coupling is visible; targetability and recovery are not collapsed into capsule survival",
    }


def _optimization_summary(optimization_v2: Mapping[str, Any]) -> Dict[str, Any]:
    rollup = optimization_v2.get("rollup", {})
    if not isinstance(rollup, Mapping):
        rollup = {}
    axis_contract = optimization_v2.get("axis_contract", {})
    axes = axis_contract.get("axes", []) if isinstance(axis_contract, Mapping) else []
    axis_ids = [
        str(axis.get("id"))
        for axis in axes
        if isinstance(axis, Mapping) and isinstance(axis.get("id"), str)
    ]
    return {
        "model": "artifact_backed_optimization_v2_frontier",
        "status": "implemented_as_four_axis_decision_surface",
        "artifact_ref": "artifacts/optimization_v2_frontier.v1.json",
        "schema_version": optimization_v2.get("schema_version"),
        "candidate_count": optimization_v2.get("candidate_count"),
        "frontier_candidate_count": optimization_v2.get("frontier_candidate_count"),
        "active_axes": axis_ids,
        "aggregation_policy": rollup.get("aggregation_policy"),
        "global_optimum_claimed": rollup.get("global_optimum_claimed"),
        "hidden_weighted_sum_used": rollup.get("hidden_weighted_sum_used"),
        "calibrated_cost_model_available": rollup.get("calibrated_cost_model_available"),
        "qualification_complete": rollup.get("qualification_complete"),
        "top_candidate_id": rollup.get("top_candidate_id"),
        "external_evidence_gaps": optimization_v2.get("external_evidence_gaps", []),
        "blocked_claims": optimization_v2.get("blocked_claims", []),
        "boundary": "four-axis Pareto screen; not a global optimum, procurement estimate, or qualification result",
    }


def _dag_v2_summary(dag_boundary: Mapping[str, Any]) -> Dict[str, Any]:
    rollup = dag_boundary.get("rollup", {})
    if not isinstance(rollup, Mapping):
        rollup = {}
    module_expectations: List[str] = []
    module_rows = dag_boundary.get("module_boundaries", [])
    if isinstance(module_rows, list) and module_rows and isinstance(module_rows[0], Mapping):
        raw_expectations = module_rows[0].get("v2_boundary_requirements", [])
        if isinstance(raw_expectations, list):
            module_expectations = [str(item) for item in raw_expectations if isinstance(item, str)]
    return {
        "status": "implemented_as_tracked_module_boundary_artifact",
        "artifact_ref": "artifacts/mission_dag_v2_boundary.v1.json",
        "schema_version": dag_boundary.get("schema_version"),
        "module_count": dag_boundary.get("module_count"),
        "failure_taxonomy_mapping_module_count": rollup.get("failure_taxonomy_mapping_module_count"),
        "state_trace_contract_complete": rollup.get("state_trace_contract_complete"),
        "module_io_schema_contract_available": rollup.get("module_io_schema_contract_available"),
        "hashchain_contract_available": rollup.get("hashchain_contract_available"),
        "independent_backend_complete": rollup.get("independent_backend_complete"),
        "high_fidelity_state_traces_available": rollup.get("high_fidelity_state_traces_available"),
        "cross_backend_comparison_available": rollup.get("cross_backend_comparison_available"),
        "external_reproduction_completed": rollup.get("external_reproduction_completed"),
        "module_expectations": module_expectations,
        "blocked_claims": dag_boundary.get("blocked_claims", []),
        "external_evidence_gaps": dag_boundary.get("external_evidence_gaps", []),
    }


def _cost_summary(cost_feasibility: Mapping[str, Any]) -> Dict[str, Any]:
    cost_model = cost_feasibility.get("cost_model", {})
    rollup = cost_feasibility.get("rollup", {})
    optimization_axis = cost_feasibility.get("optimization_cost_axis", {})
    if not isinstance(cost_model, Mapping):
        cost_model = {}
    if not isinstance(rollup, Mapping):
        rollup = {}
    if not isinstance(optimization_axis, Mapping):
        optimization_axis = {}
    return {
        "model": cost_model.get("model"),
        "status": "implemented_as_tracked_cost_procurement_architecture_screen",
        "artifact_ref": "artifacts/cost_procurement_architecture_feasibility.v1.json",
        "schema_version": cost_feasibility.get("schema_version"),
        "capsule_mass_kg": cost_model.get("capsule_mass_kg"),
        "qualification_cost_proxy_musd": cost_model.get("qualification_cost_proxy_musd"),
        "launch_architecture_cost_proxy_musd": cost_model.get("launch_architecture_cost_proxy_musd"),
        "cost_boundary": cost_model.get("cost_boundary"),
        "architecture_row_count": cost_feasibility.get("architecture_row_count"),
        "procurement_grade_estimate_available": rollup.get("procurement_grade_estimate_available"),
        "vendor_quote_count": rollup.get("vendor_quote_count"),
        "launch_vehicle_selected": rollup.get("launch_vehicle_selected"),
        "architecture_selected_for_flight": rollup.get("architecture_selected_for_flight"),
        "calibrated_cost_model_available": rollup.get("calibrated_cost_model_available"),
        "qualification_complete": rollup.get("qualification_complete"),
        "all_rows_review_required": rollup.get("all_rows_review_required"),
        "optimization_cost_proxy_min": cost_model.get("optimization_cost_proxy_min"),
        "optimization_cost_proxy_max": cost_model.get("optimization_cost_proxy_max"),
        "top_candidate_cost_proxy": optimization_axis.get("top_candidate_cost_proxy"),
        "procurement_gate_count": len(cost_feasibility.get("procurement_gates", []))
        if isinstance(cost_feasibility.get("procurement_gates"), list)
        else None,
        "external_evidence_gaps": cost_feasibility.get("external_evidence_gaps", []),
        "blocked_claims": cost_feasibility.get("blocked_claims", []),
    }


def _external_review_pack_summary(review_pack: Mapping[str, Any]) -> Dict[str, Any]:
    rollup = review_pack.get("rollup", {})
    if not isinstance(rollup, Mapping):
        rollup = {}
    return {
        "status": "implemented_as_tracked_external_validation_review_pack",
        "artifact_ref": "artifacts/external_validation_review_pack.v1.json",
        "schema_version": review_pack.get("schema_version"),
        "review_pack_status": review_pack.get("review_pack_status"),
        "review_case_count": review_pack.get("review_case_count"),
        "external_deliverable_count": rollup.get("external_deliverable_count"),
        "third_party_review_completed": rollup.get("third_party_review_completed"),
        "independent_reproduction_completed": rollup.get("independent_reproduction_completed"),
        "independent_benchmark_completed": rollup.get("independent_benchmark_completed"),
        "high_fidelity_state_trace_complete": rollup.get("high_fidelity_state_trace_complete"),
        "external_red_team_completed": rollup.get("external_red_team_completed"),
        "external_validation_claimed": rollup.get("external_validation_claimed"),
        "all_cases_require_external_review": rollup.get("all_cases_require_external_review"),
        "review_case_ids": [
            str(item.get("id"))
            for item in review_pack.get("review_cases", [])
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
        ],
        "required_deliverable_ids": [
            str(item.get("id"))
            for item in review_pack.get("required_external_deliverables", [])
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
        ],
        "blocked_claims": review_pack.get("blocked_claims", []),
        "external_evidence_gaps": review_pack.get("external_evidence_gaps", []),
    }


def _public_narrative_summary(public_narrative_hardening: Mapping[str, Any]) -> Dict[str, Any]:
    rollup = public_narrative_hardening.get("rollup", {})
    if not isinstance(rollup, Mapping):
        rollup = {}
    return {
        "status": "implemented_as_tracked_public_narrative_hardening",
        "artifact_ref": "artifacts/public_narrative_hardening.v1.json",
        "schema_version": public_narrative_hardening.get("schema_version"),
        "review_status": public_narrative_hardening.get("review_status"),
        "claim_rule_count": public_narrative_hardening.get("claim_rule_count"),
        "blocked_claim_count": public_narrative_hardening.get("blocked_claim_count"),
        "required_qualifier_count": public_narrative_hardening.get("required_qualifier_count"),
        "public_surface_count": public_narrative_hardening.get("public_surface_count"),
        "unsafe_public_overclaim_count": rollup.get("unsafe_public_overclaim_count"),
        "external_wording_audit_completed": rollup.get("external_wording_audit_completed"),
        "audience_testing_completed": rollup.get("audience_testing_completed"),
        "legal_review_completed": rollup.get("legal_review_completed"),
        "public_claim_approval_completed": rollup.get("public_claim_approval_completed"),
        "all_required_concepts_present": rollup.get("all_required_concepts_present"),
        "forbidden_claims": public_narrative_hardening.get("forbidden_public_claims", []),
        "required_claims": public_narrative_hardening.get("required_public_concepts", []),
        "allowed_phrasing": public_narrative_hardening.get("allowed_phrasing", []),
        "browser_boundary": public_narrative_hardening.get("browser_boundary", {}),
        "external_evidence_gaps": public_narrative_hardening.get("external_evidence_gaps", []),
    }


def _closure_item(
    *,
    index: int,
    title: str,
    implementation_mode: str,
    summary: str,
    artifacts: Sequence[str],
    validators: Sequence[str],
    external_evidence_gaps: Sequence[str],
    model_summary_ref: str,
) -> Dict[str, Any]:
    return {
        "id": f"roadmap-{index:02d}",
        "title": title,
        "status": ITEM_STATUS,
        "implementation_mode": implementation_mode,
        "summary": summary,
        "artifacts": list(artifacts),
        "validators": list(validators),
        "model_summary_ref": model_summary_ref,
        "external_evidence_gaps": list(external_evidence_gaps),
        "acceptance_criteria": [
            "tracked artifact exists",
            "strict validator passes",
            "browser summary does not recompute truth",
            "external evidence gaps remain visible",
        ],
        "false_claims_blocked": ["certified", "qualified", "proven flight-ready", "guaranteed"],
        "non_certification_notice": True,
        "claim_boundary": "Implemented as a deterministic repository artifact and review contract; external qualification remains separate.",
    }


def _closure_items() -> List[Dict[str, Any]]:
    common_validators = ["scripts/ci/roadmap_closure_validate.py", "scripts/ci/check_suite.py"]
    return [
        _closure_item(
            index=1,
            title="Mission Physics v2 screening layer",
            implementation_mode="deterministic_model_contract",
            summary="Adds Kerr horizon screening, radial environment hooks, and thermal-dose boundary metadata.",
            artifacts=["artifacts/roadmap_closure.v1.json", "mission/ROADMAP_CLOSURE_SPEC_v1.md"],
            validators=common_validators,
            external_evidence_gaps=["full GR geodesic integration", "relativistic plasma/MHD coupling"],
            model_summary_ref="model_summaries.mission_physics_v2",
        ),
        _closure_item(
            index=2,
            title="Target trajectory and reachability engine",
            implementation_mode="deterministic_reachability_contract",
            summary="Publishes target distance, velocity, and time-of-flight tables with targetability gaps separated.",
            artifacts=["artifacts/roadmap_closure.v1.json"],
            validators=common_validators,
            external_evidence_gaps=["target ephemeris over Myr horizons", "closed-loop navigation authority"],
            model_summary_ref="model_summaries.trajectory_reachability",
        ),
        _closure_item(
            index=3,
            title="Capsule qualification evidence stack",
            implementation_mode="qualification_gap_contract",
            summary="Turns shield, material, and stack-level evidence gaps into explicit review gates.",
            artifacts=["artifacts/roadmap_closure.v1.json", "docs/research/VALIDATION_AND_QUALIFICATION_GAPS_v1.md"],
            validators=common_validators,
            external_evidence_gaps=["stack-level ballistic-limit testing", "hydrocode correlation against the selected stack"],
            model_summary_ref="qualification_tracks.capsule_stack",
        ),
        _closure_item(
            index=4,
            title="Archive media and bit-level recoverability",
            implementation_mode="recoverability_contract",
            summary="Separates physical media survival from ECC, indexing, redundancy, and readability requirements.",
            artifacts=["artifacts/roadmap_closure.v1.json"],
            validators=common_validators,
            external_evidence_gaps=["accelerated-aging media tests", "bit-level ECC recovery under radiation and thermal stress"],
            model_summary_ref="qualification_tracks.archive_media",
        ),
        _closure_item(
            index=5,
            title="Interstellar dust-tail model",
            implementation_mode="deterministic_hazard_screen",
            summary="Adds a local-ISM dust swept-mass and impact-energy screen while keeping mm/cm tails assumption-bound.",
            artifacts=["artifacts/roadmap_closure.v1.json"],
            validators=common_validators,
            external_evidence_gaps=["mission-specific mm/cm dust-tail flux", "line-of-sight dust-density bins"],
            model_summary_ref="model_summaries.dust_tail",
        ),
        _closure_item(
            index=6,
            title="Radiation and material transport hooks",
            implementation_mode="transport_hook_contract",
            summary="Connects radiation, plasma, media, and material-degradation dimensions to explicit transport gaps.",
            artifacts=["artifacts/roadmap_closure.v1.json"],
            validators=common_validators,
            external_evidence_gaps=["material-specific particle transport", "TID/SEE/displacement damage evidence"],
            model_summary_ref="model_summaries.radiation_material",
        ),
        _closure_item(
            index=7,
            title="Full mission-level probabilistic coupling",
            implementation_mode="tracked_factorized_probability_coupling",
            summary="Adds a tracked factorized coupling artifact with capsule/data review proxies and open external target, environment, and recovery factors.",
            artifacts=[
                "artifacts/roadmap_closure.v1.json",
                "artifacts/mission_probability_coupling.v1.json",
                "artifacts/capsule_risk_budget.v1.json",
            ],
            validators=[
                "scripts/ci/mission_probability_coupling_validate.py",
                *common_validators,
            ],
            external_evidence_gaps=[
                "target acquisition probability model",
                "whole-path environment probability model",
                "arrival/recovery/readability model",
            ],
            model_summary_ref="model_summaries.mission_coupling",
        ),
        _closure_item(
            index=8,
            title="Uncertainty v2 interactions",
            implementation_mode="tracked_pairwise_uncertainty_interaction_screen",
            summary="Adds a tracked pairwise uncertainty interaction artifact with open covariance and correlation evidence gates.",
            artifacts=[
                "artifacts/roadmap_closure.v1.json",
                "artifacts/uncertainty_interactions.v1.json",
            ],
            validators=[
                "scripts/ci/uncertainty_interactions_validate.py",
                *common_validators,
            ],
            external_evidence_gaps=["source-backed correlation calibration", "higher-order Sobol/CVaR campaign"],
            model_summary_ref="model_summaries.uncertainty_v2",
        ),
        _closure_item(
            index=9,
            title="Evidence upgrade campaign",
            implementation_mode="tracked_evidence_upgrade_campaign",
            summary="Adds a tracked evidence-upgrade campaign artifact that ranks source-review work without promoting trust grades.",
            artifacts=[
                "artifacts/roadmap_closure.v1.json",
                "artifacts/evidence_upgrade_campaign.v1.json",
                "parameters/registry/parameter_claims.v1.json",
            ],
            validators=[
                "scripts/ci/evidence_upgrade_campaign_validate.py",
                *common_validators,
            ],
            external_evidence_gaps=[
                "periodic citation quality review",
                "primary-source upgrades for assumption-bound priors",
                "public URLs or archival references for source records",
            ],
            model_summary_ref="evidence_upgrade",
        ),
        _closure_item(
            index=10,
            title="Optimization v2",
            implementation_mode="tracked_four_axis_decision_surface",
            summary="Adds a tracked four-axis optimization v2 artifact over p_success, risk, qualification-gap, and cost-proxy tradeoffs.",
            artifacts=[
                "artifacts/roadmap_closure.v1.json",
                "artifacts/optimization_v2_frontier.v1.json",
                "artifacts/optimization_frontier_realistic.v1.json",
                "artifacts/optimization_search_space.v1.json",
            ],
            validators=[
                "scripts/ci/optimization_v2_validate.py",
                "scripts/ci/optimization_frontier_validate.py",
                "scripts/ci/risk_envelope_validate.py",
                *common_validators,
            ],
            external_evidence_gaps=[
                "larger search campaign with solver diversity",
                "calibrated mission utility and cost model",
                "stack-level qualification evidence tied to optimized parameters",
            ],
            model_summary_ref="model_summaries.optimization_v2",
        ),
        _closure_item(
            index=11,
            title="Mission DAG v2 physics module boundary",
            implementation_mode="tracked_module_boundary_artifact",
            summary="Adds a tracked DAG v2 boundary artifact for every module, separating v1 wrapper support from v2 trace/backend requirements.",
            artifacts=[
                "artifacts/roadmap_closure.v1.json",
                "artifacts/mission_dag_v2_boundary.v1.json",
                "mission/dag/registry/module_registry.v1.json",
            ],
            validators=[
                "scripts/ci/mission_dag_v2_boundary_validate.py",
                "scripts/ci/mission_dag_validate.py",
                *common_validators,
            ],
            external_evidence_gaps=["independent physics backends", "module-level high-fidelity state traces"],
            model_summary_ref="dag_v2",
        ),
        _closure_item(
            index=12,
            title="Runtime scenario generation and user-owned runs",
            implementation_mode="tracked_runtime_generation_contract",
            summary="Adds a tracked runtime-generation recipe artifact, deterministic selected-run catalog, and strict local pack validator for user-owned scenario artifacts and hashes.",
            artifacts=[
                "artifacts/roadmap_closure.v1.json",
                "artifacts/user_mission_run_catalog.v1.json",
                "artifacts/runtime_scenario_generation.v1.json",
                "scripts/run_user_mission_scenario.py",
            ],
            validators=[
                "scripts/ci/user_mission_run_catalog_validate.py",
                "scripts/ci/runtime_scenario_generation_validate.py",
                "scripts/ci/user_mission_run_pack_validate.py",
                *common_validators,
            ],
            external_evidence_gaps=["remote execution isolation", "persistent reviewed run archive"],
            model_summary_ref="runtime_runs",
        ),
        _closure_item(
            index=13,
            title="Cost, procurement, and architecture feasibility",
            implementation_mode="tracked_cost_procurement_architecture_screen",
            summary="Adds a tracked cost/procurement/architecture feasibility artifact with explicit external procurement, launch, and architecture gates.",
            artifacts=[
                "artifacts/roadmap_closure.v1.json",
                "artifacts/cost_procurement_architecture_feasibility.v1.json",
            ],
            validators=[
                "scripts/ci/cost_procurement_architecture_feasibility_validate.py",
                *common_validators,
            ],
            external_evidence_gaps=[
                "vendor/procurement-grade estimates",
                "launch vehicle integration data",
                "independent architecture trade study",
            ],
            model_summary_ref="model_summaries.cost_feasibility",
        ),
        _closure_item(
            index=14,
            title="External validation and independent review pack",
            implementation_mode="tracked_external_validation_review_pack",
            summary="Adds a tracked external validation review-pack artifact with required reviewer deliverables and explicit false-claim blockers.",
            artifacts=[
                "artifacts/roadmap_closure.v1.json",
                "artifacts/external_validation_review_pack.v1.json",
                "docs/FULL_V2_ROADMAP_CLOSURE.md",
            ],
            validators=[
                "scripts/ci/external_validation_review_pack_validate.py",
                *common_validators,
            ],
            external_evidence_gaps=[
                "third-party reproduction reports",
                "independent physics benchmark comparisons",
                "high-fidelity module state traces",
                "external red-team review findings",
            ],
            model_summary_ref="review_pack",
        ),
        _closure_item(
            index=15,
            title="Public narrative hardening",
            implementation_mode="tracked_public_narrative_hardening",
            summary="Adds a tracked public narrative hardening artifact with blocked public claims, required qualifiers, and browser-rendering boundaries.",
            artifacts=[
                "artifacts/roadmap_closure.v1.json",
                "artifacts/public_narrative_hardening.v1.json",
                "docs/FULL_V2_ROADMAP_CLOSURE.md",
            ],
            validators=[
                "scripts/ci/public_narrative_hardening_validate.py",
                *common_validators,
            ],
            external_evidence_gaps=[
                "external reviewer wording audit",
                "audience testing for overinterpretation risk",
                "legal or marketing approval review",
            ],
            model_summary_ref="public_narrative",
        ),
    ]


def build_roadmap_closure(repo_root: Path) -> Dict[str, Any]:
    baseline = _load_json(repo_root / "mission/BASELINE_SCENARIO_v1.json")
    capsule = _load_json(repo_root / "artifacts/capsule_survivability_lab.v1.json")
    capsule_risk = _load_json(repo_root / "artifacts/capsule_risk_budget.v1.json")
    user_run_catalog = _load_json(repo_root / "artifacts/user_mission_run_catalog.v1.json")
    runtime_generation = _load_json(repo_root / "artifacts/runtime_scenario_generation.v1.json")
    probability_coupling = _load_json(repo_root / "artifacts/mission_probability_coupling.v1.json")
    uncertainty_interactions = _load_json(repo_root / "artifacts/uncertainty_interactions.v1.json")
    evidence_upgrade_campaign = _load_json(repo_root / "artifacts/evidence_upgrade_campaign.v1.json")
    optimization_v2 = _load_json(repo_root / "artifacts/optimization_v2_frontier.v1.json")
    dag_boundary = _load_json(repo_root / "artifacts/mission_dag_v2_boundary.v1.json")
    cost_feasibility = _load_json(repo_root / "artifacts/cost_procurement_architecture_feasibility.v1.json")
    external_review_pack = _load_json(repo_root / "artifacts/external_validation_review_pack.v1.json")
    public_narrative_hardening = _load_json(repo_root / "artifacts/public_narrative_hardening.v1.json")
    claims = _load_json(repo_root / "parameters/registry/parameter_claims.v1.json")

    claim_grades: Dict[str, int] = {}
    for claim in claims.get("claims", []):
        if isinstance(claim, Mapping):
            grade = str(claim.get("trust_grade", "unknown"))
            claim_grades[grade] = claim_grades.get(grade, 0) + 1

    items = _closure_items()
    source_paths = [
        "mission/BASELINE_SCENARIO_v1.json",
        "artifacts/capsule_survivability_lab.v1.json",
        "artifacts/capsule_risk_budget.v1.json",
        "artifacts/user_mission_run_catalog.v1.json",
        "artifacts/runtime_scenario_generation.v1.json",
        "artifacts/mission_probability_coupling.v1.json",
        "artifacts/uncertainty_interactions.v1.json",
        "artifacts/evidence_upgrade_campaign.v1.json",
        "artifacts/optimization_v2_frontier.v1.json",
        "artifacts/mission_dag_v2_boundary.v1.json",
        "artifacts/cost_procurement_architecture_feasibility.v1.json",
        "artifacts/external_validation_review_pack.v1.json",
        "artifacts/public_narrative_hardening.v1.json",
        "artifacts/optimization_frontier_realistic.v1.json",
        "parameters/registry/parameter_claims.v1.json",
    ]

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "public_scope": PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, source_paths),
        "roadmap_item_count": len(items),
        "roadmap_items": items,
        "closure_metrics": {
            "repo_native_closure_count": len(items),
            "external_evidence_gap_count": sum(len(item["external_evidence_gaps"]) for item in items),
            "non_certification_notice_count": sum(1 for item in items if item.get("non_certification_notice") is True),
            "trust_grade_distribution": dict(sorted(claim_grades.items())),
        },
        "model_summaries": {
            "mission_physics_v2": _kerr_summary(baseline),
            "trajectory_reachability": _trajectory_summary(),
            "dust_tail": _dust_summary(capsule),
            "radiation_material": _radiation_material_summary(capsule_risk),
            "mission_coupling": _mission_coupling_summary(baseline, capsule_risk, probability_coupling),
            "uncertainty_v2": _uncertainty_summary(uncertainty_interactions),
            "optimization_v2": _optimization_summary(optimization_v2),
            "cost_feasibility": _cost_summary(cost_feasibility),
        },
        "qualification_tracks": {
            "capsule_stack": {
                "status": "repo_native_gap_ledger_implemented",
                "required_evidence": [
                    "ballistic-limit tests across particle size, angle, velocity, and material stack",
                    "hydrocode correlation for tens-of-km/s extrapolation",
                    "mass and thermal closure for final stack geometry",
                ],
            },
            "archive_media": {
                "status": "repo_native_recoverability_contract_implemented",
                "required_evidence": [
                    "media-specific radiation and thermal aging tests",
                    "bit-level ECC and index recovery campaign",
                    "post-arrival readability assumptions separated from physical survival",
                ],
            },
        },
        "evidence_upgrade": _evidence_upgrade_summary(evidence_upgrade_campaign),
        "dag_v2": _dag_v2_summary(dag_boundary),
        "runtime_runs": {
            "status": "implemented_as_tracked_runtime_generation_contract_and_strict_local_pack_validator",
            "artifact_ref": "artifacts/runtime_scenario_generation.v1.json",
            "schema_version": runtime_generation.get("schema_version"),
            "catalog_schema_version": user_run_catalog.get("schema_version"),
            "run_count": user_run_catalog.get("run_count"),
            "generation_row_count": runtime_generation.get("generation_row_count"),
            "default_run_id": user_run_catalog.get("default_run_id"),
            "pack_validator": "scripts/ci/user_mission_run_pack_validate.py",
            "run_store_tracked_by_default": runtime_generation.get("run_pack_contract", {}).get("tracked_by_default"),
            "writes_tracked_files": runtime_generation.get("run_pack_contract", {}).get("writes_tracked_files"),
            "remote_execution_claimed": runtime_generation.get("rollup", {}).get("remote_execution_claimed"),
            "persistent_reviewed_archive_claimed": runtime_generation.get("rollup", {}).get("persistent_reviewed_archive_claimed"),
            "pack_output_files": runtime_generation.get("run_pack_contract", {}).get("output_files", []),
            "blocked_runtime_claims": runtime_generation.get("blocked_claims", []),
            "run_artifact_fields": [
                "selection_hash",
                "compiled_mission_scenario_sha256",
                "dag_manifest_hash",
                "pack_validator",
                "created_from_commit",
            ],
            "local_runner": "scripts/run_user_mission_scenario.py",
        },
        "review_pack": _external_review_pack_summary(external_review_pack),
        "public_narrative": _public_narrative_summary(public_narrative_hardening),
    }
    return payload


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def validate_roadmap_closure(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if payload.get("generator") != GENERATOR:
        errors.append(f"generator must be {GENERATOR}")
    if payload.get("public_scope") != PUBLIC_SCOPE:
        errors.append(f"public_scope must be {PUBLIC_SCOPE}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")

    items = payload.get("roadmap_items")
    if not isinstance(items, list):
        errors.append("roadmap_items must be a list")
        items = []
    ids = [item.get("id") for item in items if isinstance(item, Mapping)]
    if tuple(ids) != REQUIRED_ITEM_IDS:
        errors.append(f"roadmap item ids must be exactly {','.join(REQUIRED_ITEM_IDS)}")
    if payload.get("roadmap_item_count") != 15 or len(items) != 15:
        errors.append("roadmap_item_count and roadmap_items length must be 15")

    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            errors.append(f"roadmap_items[{index}] must be object")
            continue
        prefix = f"roadmap_items[{index}]"
        if item.get("status") != ITEM_STATUS:
            errors.append(f"{prefix}.status must be {ITEM_STATUS}")
        if item.get("non_certification_notice") is not True:
            errors.append(f"{prefix}.non_certification_notice must be true")
        for field in ("title", "implementation_mode", "summary", "model_summary_ref", "claim_boundary"):
            if not isinstance(item.get(field), str) or not item.get(field):
                errors.append(f"{prefix}.{field} must be non-empty string")
        for field in ("artifacts", "validators", "external_evidence_gaps", "acceptance_criteria", "false_claims_blocked"):
            values = item.get(field)
            if not isinstance(values, list) or not values:
                errors.append(f"{prefix}.{field} must be non-empty list")
        if "certified" in str(item.get("summary", "")).lower():
            errors.append(f"{prefix}.summary must not claim certification")

    item_by_id = {str(item.get("id")): item for item in items if isinstance(item, Mapping)}
    item15 = item_by_id.get("roadmap-15", {})
    if isinstance(item15, Mapping):
        if item15.get("implementation_mode") != "tracked_public_narrative_hardening":
            errors.append("roadmap-15.implementation_mode must be tracked_public_narrative_hardening")
        artifacts = item15.get("artifacts")
        if not isinstance(artifacts, list) or "artifacts/public_narrative_hardening.v1.json" not in artifacts:
            errors.append("roadmap-15.artifacts must include public narrative hardening artifact")
        validators = item15.get("validators")
        if not isinstance(validators, list) or "scripts/ci/public_narrative_hardening_validate.py" not in validators:
            errors.append("roadmap-15.validators must include public narrative validator")
        blocked = item15.get("false_claims_blocked")
        if not isinstance(blocked, list) or "certified" not in blocked:
            errors.append("roadmap-15.false_claims_blocked must include certified")

    metrics = payload.get("closure_metrics")
    if not isinstance(metrics, Mapping):
        errors.append("closure_metrics must be object")
        metrics = {}
    if metrics.get("repo_native_closure_count") != 15:
        errors.append("closure_metrics.repo_native_closure_count must be 15")
    if metrics.get("non_certification_notice_count") != 15:
        errors.append("closure_metrics.non_certification_notice_count must be 15")
    if not isinstance(metrics.get("external_evidence_gap_count"), int) or metrics.get("external_evidence_gap_count", 0) < 15:
        errors.append("closure_metrics.external_evidence_gap_count must be int >= 15")

    model_summaries = payload.get("model_summaries")
    if not isinstance(model_summaries, Mapping):
        errors.append("model_summaries must be object")
        model_summaries = {}
    for required in (
        "mission_physics_v2",
        "trajectory_reachability",
        "dust_tail",
        "radiation_material",
        "mission_coupling",
        "uncertainty_v2",
        "optimization_v2",
        "cost_feasibility",
    ):
        if required not in model_summaries:
            errors.append(f"model_summaries missing {required}")

    physics = model_summaries.get("mission_physics_v2", {})
    if isinstance(physics, Mapping):
        ratio = physics.get("outer_horizon_vs_schwarzschild_ratio")
        if not _is_number(ratio) or not 0.5 <= float(ratio) <= 1.0:
            errors.append("mission_physics_v2.outer_horizon_vs_schwarzschild_ratio must be in [0.5,1.0]")
    coupling = model_summaries.get("mission_coupling", {})
    if isinstance(coupling, Mapping):
        for field in ("p_hit_reference", "p_survive_reference", "p_data_intact_reference", "coupled_reference_probability"):
            value = coupling.get(field)
            if not _is_number(value) or not 0.0 <= float(value) <= 1.0:
                errors.append(f"mission_coupling.{field} must be probability in [0,1]")
        if coupling.get("coupling_count") != 15:
            errors.append("mission_coupling.coupling_count must be 15")
        if coupling.get("full_mission_probability_status") != "not_closed_external_factors_open":
            errors.append("mission_coupling.full_mission_probability_status must keep external factors open")

    uncertainty = model_summaries.get("uncertainty_v2", {})
    if isinstance(uncertainty, Mapping):
        if uncertainty.get("artifact_ref") != "artifacts/uncertainty_interactions.v1.json":
            errors.append("uncertainty_v2.artifact_ref must point to uncertainty_interactions artifact")
        if uncertainty.get("dimension_count") != 4:
            errors.append("uncertainty_v2.dimension_count must be 4")
        if uncertainty.get("interaction_pair_count") != 6:
            errors.append("uncertainty_v2.interaction_pair_count must be 6")
        if uncertainty.get("validated_correlation_count") != 0:
            errors.append("uncertainty_v2.validated_correlation_count must remain 0")
        if uncertainty.get("full_uncertainty_interaction_closure") is not False:
            errors.append("uncertainty_v2.full_uncertainty_interaction_closure must be false")
        if not isinstance(uncertainty.get("external_evidence_gaps"), list) or not uncertainty["external_evidence_gaps"]:
            errors.append("uncertainty_v2.external_evidence_gaps must be non-empty")

    optimization = model_summaries.get("optimization_v2", {})
    if isinstance(optimization, Mapping):
        if optimization.get("artifact_ref") != "artifacts/optimization_v2_frontier.v1.json":
            errors.append("optimization_v2.artifact_ref must point to optimization v2 artifact")
        if optimization.get("schema_version") != "optimization_v2_frontier.v1":
            errors.append("optimization_v2.schema_version must be optimization_v2_frontier.v1")
        if optimization.get("status") != "implemented_as_four_axis_decision_surface":
            errors.append("optimization_v2.status must reference four-axis decision surface")
        if optimization.get("candidate_count") != 20:
            errors.append("optimization_v2.candidate_count must be 20")
        if not isinstance(optimization.get("frontier_candidate_count"), int) or optimization.get("frontier_candidate_count", 0) < 1:
            errors.append("optimization_v2.frontier_candidate_count must be int >= 1")
        if optimization.get("active_axes") != ["p_success", "risk_envelope", "qualification_gap", "cost_proxy"]:
            errors.append("optimization_v2.active_axes mismatch")
        if optimization.get("aggregation_policy") != "pareto_first_no_hidden_weighted_sum":
            errors.append("optimization_v2.aggregation_policy mismatch")
        for field in (
            "global_optimum_claimed",
            "hidden_weighted_sum_used",
            "calibrated_cost_model_available",
            "qualification_complete",
        ):
            if optimization.get(field) is not False:
                errors.append(f"optimization_v2.{field} must be false")
        if not isinstance(optimization.get("external_evidence_gaps"), list) or not optimization["external_evidence_gaps"]:
            errors.append("optimization_v2.external_evidence_gaps must be non-empty")
        blocked = optimization.get("blocked_claims")
        if not isinstance(blocked, list) or "global optimum proven" not in blocked:
            errors.append("optimization_v2.blocked_claims must block global optimum proof")
        if isinstance(blocked, list) and "procurement-grade cost estimate" not in blocked:
            errors.append("optimization_v2.blocked_claims must block procurement-grade cost estimates")
        if isinstance(blocked, list) and "qualification complete" not in blocked:
            errors.append("optimization_v2.blocked_claims must block qualification completion")
        if isinstance(blocked, list) and "flight-ready design selected" not in blocked:
            errors.append("optimization_v2.blocked_claims must block flight-ready design selection")

    evidence_upgrade = payload.get("evidence_upgrade", {})
    if isinstance(evidence_upgrade, Mapping):
        if evidence_upgrade.get("artifact_ref") != "artifacts/evidence_upgrade_campaign.v1.json":
            errors.append("evidence_upgrade.artifact_ref must point to evidence upgrade campaign artifact")
        if evidence_upgrade.get("schema_version") != "evidence_upgrade_campaign.v1":
            errors.append("evidence_upgrade.schema_version must be evidence_upgrade_campaign.v1")
        if evidence_upgrade.get("status") != "implemented_as_tracked_campaign_ledger":
            errors.append("evidence_upgrade.status must reference tracked campaign ledger")
        if evidence_upgrade.get("claim_count") != 66:
            errors.append("evidence_upgrade.claim_count must be 66")
        if evidence_upgrade.get("public_campaign_count") != 31:
            errors.append("evidence_upgrade.public_campaign_count must be 31")
        if evidence_upgrade.get("internal_audit_count") != 35:
            errors.append("evidence_upgrade.internal_audit_count must be 35")
        if evidence_upgrade.get("trust_grade_distribution") != {"B": 8, "C": 56, "D": 2}:
            errors.append("evidence_upgrade.trust_grade_distribution mismatch")
        if evidence_upgrade.get("public_trust_distribution") != {"B": 8, "C": 21, "D": 2}:
            errors.append("evidence_upgrade.public_trust_distribution mismatch")
        if evidence_upgrade.get("top_priority_count") != 15:
            errors.append("evidence_upgrade.top_priority_count must be 15")
        if not isinstance(evidence_upgrade.get("top_priority_ids"), list) or not evidence_upgrade["top_priority_ids"]:
            errors.append("evidence_upgrade.top_priority_ids must be non-empty")
        if evidence_upgrade.get("speculative_quarantine_count") != 2:
            errors.append("evidence_upgrade.speculative_quarantine_count must be 2")
        if not isinstance(evidence_upgrade.get("external_evidence_gaps"), list) or not evidence_upgrade["external_evidence_gaps"]:
            errors.append("evidence_upgrade.external_evidence_gaps must be non-empty")
        blocked = evidence_upgrade.get("blocked_claims")
        if not isinstance(blocked, list) or "trust grades upgraded automatically" not in blocked:
            errors.append("evidence_upgrade.blocked_claims must block automatic trust upgrades")
        if isinstance(blocked, list) and "source correctness proven" not in blocked:
            errors.append("evidence_upgrade.blocked_claims must block source correctness proof")

    cost_feasibility = model_summaries.get("cost_feasibility", {})
    if isinstance(cost_feasibility, Mapping):
        if cost_feasibility.get("artifact_ref") != "artifacts/cost_procurement_architecture_feasibility.v1.json":
            errors.append("cost_feasibility.artifact_ref must point to cost/procurement artifact")
        if cost_feasibility.get("schema_version") != "cost_procurement_architecture_feasibility.v1":
            errors.append("cost_feasibility.schema_version mismatch")
        if cost_feasibility.get("status") != "implemented_as_tracked_cost_procurement_architecture_screen":
            errors.append("cost_feasibility.status must reference tracked artifact")
        if cost_feasibility.get("architecture_row_count") != 15:
            errors.append("cost_feasibility.architecture_row_count must be 15")
        if cost_feasibility.get("procurement_gate_count") != 4:
            errors.append("cost_feasibility.procurement_gate_count must be 4")
        for field in (
            "procurement_grade_estimate_available",
            "launch_vehicle_selected",
            "architecture_selected_for_flight",
            "calibrated_cost_model_available",
            "qualification_complete",
        ):
            if cost_feasibility.get(field) is not False:
                errors.append(f"cost_feasibility.{field} must be false")
        if cost_feasibility.get("vendor_quote_count") != 0:
            errors.append("cost_feasibility.vendor_quote_count must be 0")
        if cost_feasibility.get("all_rows_review_required") is not True:
            errors.append("cost_feasibility.all_rows_review_required must be true")
        blocked = cost_feasibility.get("blocked_claims")
        if not isinstance(blocked, list) or "procurement-grade cost estimate" not in blocked:
            errors.append("cost_feasibility.blocked_claims must block procurement-grade estimates")
        if isinstance(blocked, list) and "flight-ready architecture selected" not in blocked:
            errors.append("cost_feasibility.blocked_claims must block flight-ready architecture")
        if not isinstance(cost_feasibility.get("external_evidence_gaps"), list) or not cost_feasibility["external_evidence_gaps"]:
            errors.append("cost_feasibility.external_evidence_gaps must be non-empty")

    for section in ("qualification_tracks", "evidence_upgrade", "dag_v2", "runtime_runs", "review_pack", "public_narrative"):
        if not isinstance(payload.get(section), Mapping):
            errors.append(f"{section} must be object")

    dag_v2 = payload.get("dag_v2", {})
    if isinstance(dag_v2, Mapping):
        if dag_v2.get("artifact_ref") != "artifacts/mission_dag_v2_boundary.v1.json":
            errors.append("dag_v2.artifact_ref must point to mission DAG v2 boundary artifact")
        if dag_v2.get("schema_version") != "mission_dag_v2_boundary.v1":
            errors.append("dag_v2.schema_version must be mission_dag_v2_boundary.v1")
        if dag_v2.get("status") != "implemented_as_tracked_module_boundary_artifact":
            errors.append("dag_v2.status must reference tracked module boundary artifact")
        if dag_v2.get("module_count") != 6:
            errors.append("dag_v2.module_count must be 6")
        if dag_v2.get("failure_taxonomy_mapping_module_count") != 6:
            errors.append("dag_v2.failure_taxonomy_mapping_module_count must be 6")
        for field in (
            "state_trace_contract_complete",
            "module_io_schema_contract_available",
            "hashchain_contract_available",
        ):
            if dag_v2.get(field) is not True:
                errors.append(f"dag_v2.{field} must be true")
        for field in (
            "independent_backend_complete",
            "high_fidelity_state_traces_available",
            "cross_backend_comparison_available",
            "external_reproduction_completed",
        ):
            if dag_v2.get(field) is not False:
                errors.append(f"dag_v2.{field} must be false")
        expectations = dag_v2.get("module_expectations")
        if not isinstance(expectations, list) or "state trace hash" not in expectations:
            errors.append("dag_v2.module_expectations must include state trace hash")
        blocked = dag_v2.get("blocked_claims")
        if not isinstance(blocked, list) or "independent physics backend validated" not in blocked:
            errors.append("dag_v2.blocked_claims must block independent backend validation")
        if isinstance(blocked, list) and "flight-ready module approved" not in blocked:
            errors.append("dag_v2.blocked_claims must block flight-ready module approval")
        if not isinstance(dag_v2.get("external_evidence_gaps"), list) or not dag_v2["external_evidence_gaps"]:
            errors.append("dag_v2.external_evidence_gaps must be non-empty")

    runtime_runs = payload.get("runtime_runs", {})
    if isinstance(runtime_runs, Mapping):
        if runtime_runs.get("status") != "implemented_as_tracked_runtime_generation_contract_and_strict_local_pack_validator":
            errors.append("runtime_runs.status must reference tracked runtime-generation contract and strict pack validator")
        if runtime_runs.get("artifact_ref") != "artifacts/runtime_scenario_generation.v1.json":
            errors.append("runtime_runs.artifact_ref must reference runtime scenario generation artifact")
        if runtime_runs.get("schema_version") != "runtime_scenario_generation.v1":
            errors.append("runtime_runs.schema_version must be runtime_scenario_generation.v1")
        if runtime_runs.get("run_count") != 15:
            errors.append("runtime_runs.run_count must be 15")
        if runtime_runs.get("generation_row_count") != 15:
            errors.append("runtime_runs.generation_row_count must be 15")
        if not isinstance(runtime_runs.get("default_run_id"), str) or not str(runtime_runs.get("default_run_id")).startswith("umr-reference-black-hole-conditional-45-"):
            errors.append("runtime_runs.default_run_id must reference default selected run")
        if runtime_runs.get("pack_validator") != "scripts/ci/user_mission_run_pack_validate.py":
            errors.append("runtime_runs.pack_validator must reference strict pack validator")
        if runtime_runs.get("run_store_tracked_by_default") is not False:
            errors.append("runtime_runs.run_store_tracked_by_default must be false")
        if runtime_runs.get("writes_tracked_files") is not False:
            errors.append("runtime_runs.writes_tracked_files must be false")
        if runtime_runs.get("remote_execution_claimed") is not False:
            errors.append("runtime_runs.remote_execution_claimed must be false")
        if runtime_runs.get("persistent_reviewed_archive_claimed") is not False:
            errors.append("runtime_runs.persistent_reviewed_archive_claimed must be false")
        pack_files = runtime_runs.get("pack_output_files")
        if not isinstance(pack_files, list) or "USER_RUN_SUMMARY.json" not in pack_files:
            errors.append("runtime_runs.pack_output_files must include USER_RUN_SUMMARY.json")
        blocked = runtime_runs.get("blocked_runtime_claims")
        if not isinstance(blocked, list) or "persistent reviewed run archive" not in blocked:
            errors.append("runtime_runs.blocked_runtime_claims must block persistent archive")
        fields = runtime_runs.get("run_artifact_fields")
        if not isinstance(fields, list) or "dag_manifest_hash" not in fields:
            errors.append("runtime_runs.run_artifact_fields must include dag_manifest_hash")
        if isinstance(fields, list) and "pack_validator" not in fields:
            errors.append("runtime_runs.run_artifact_fields must include pack_validator")

    review_pack = payload.get("review_pack", {})
    if isinstance(review_pack, Mapping):
        if review_pack.get("status") != "implemented_as_tracked_external_validation_review_pack":
            errors.append("review_pack.status must reference tracked external validation review pack")
        if review_pack.get("artifact_ref") != "artifacts/external_validation_review_pack.v1.json":
            errors.append("review_pack.artifact_ref must reference external validation review pack artifact")
        if review_pack.get("schema_version") != "external_validation_review_pack.v1":
            errors.append("review_pack.schema_version must be external_validation_review_pack.v1")
        if review_pack.get("review_pack_status") != "repo_native_review_pack_ready_external_review_not_completed":
            errors.append("review_pack.review_pack_status must keep external review incomplete")
        if review_pack.get("review_case_count") != 7:
            errors.append("review_pack.review_case_count must be 7")
        if review_pack.get("external_deliverable_count") != 6:
            errors.append("review_pack.external_deliverable_count must be 6")
        for field in (
            "third_party_review_completed",
            "independent_reproduction_completed",
            "independent_benchmark_completed",
            "high_fidelity_state_trace_complete",
            "external_red_team_completed",
            "external_validation_claimed",
        ):
            if review_pack.get(field) is not False:
                errors.append(f"review_pack.{field} must be false")
        if review_pack.get("all_cases_require_external_review") is not True:
            errors.append("review_pack.all_cases_require_external_review must be true")
        case_ids = review_pack.get("review_case_ids")
        if not isinstance(case_ids, list) or "optimistic-prior-collapse" not in case_ids:
            errors.append("review_pack.review_case_ids must include optimistic-prior-collapse")
        deliverables = review_pack.get("required_deliverable_ids")
        if not isinstance(deliverables, list) or "external_red_team_report" not in deliverables:
            errors.append("review_pack.required_deliverable_ids must include external_red_team_report")
        blocked = review_pack.get("blocked_claims")
        if not isinstance(blocked, list) or "third-party validated" not in blocked:
            errors.append("review_pack.blocked_claims must block third-party validation")
        if isinstance(blocked, list) and "independent reproduction completed" not in blocked:
            errors.append("review_pack.blocked_claims must block independent reproduction")
        if not isinstance(review_pack.get("external_evidence_gaps"), list) or not review_pack["external_evidence_gaps"]:
            errors.append("review_pack.external_evidence_gaps must be non-empty")

    narrative = payload.get("public_narrative", {})
    if isinstance(narrative, Mapping):
        if narrative.get("status") != "implemented_as_tracked_public_narrative_hardening":
            errors.append("public_narrative.status must reference tracked public narrative hardening")
        if narrative.get("artifact_ref") != "artifacts/public_narrative_hardening.v1.json":
            errors.append("public_narrative.artifact_ref must reference public narrative hardening artifact")
        if narrative.get("schema_version") != "public_narrative_hardening.v1":
            errors.append("public_narrative.schema_version must be public_narrative_hardening.v1")
        if narrative.get("claim_rule_count") != 10:
            errors.append("public_narrative.claim_rule_count must be 10")
        if not isinstance(narrative.get("public_surface_count"), int) or narrative.get("public_surface_count", 0) < 8:
            errors.append("public_narrative.public_surface_count must be int >= 8")
        if narrative.get("unsafe_public_overclaim_count") != 0:
            errors.append("public_narrative.unsafe_public_overclaim_count must be 0")
        for field in (
            "external_wording_audit_completed",
            "audience_testing_completed",
            "legal_review_completed",
            "public_claim_approval_completed",
        ):
            if narrative.get(field) is not False:
                errors.append(f"public_narrative.{field} must be false")
        if narrative.get("all_required_concepts_present") is not True:
            errors.append("public_narrative.all_required_concepts_present must be true")
        forbidden = narrative.get("forbidden_claims")
        required = narrative.get("required_claims")
        if not isinstance(forbidden, list) or "certified" not in forbidden:
            errors.append("public_narrative.forbidden_claims must include certified")
        if isinstance(forbidden, list) and "external validation completed" not in forbidden:
            errors.append("public_narrative.forbidden_claims must include external validation completed")
        if isinstance(forbidden, list) and "procurement-grade cost estimate" not in forbidden:
            errors.append("public_narrative.forbidden_claims must include procurement-grade cost estimate")
        if not isinstance(required, list) or "non-certifying" not in required:
            errors.append("public_narrative.required_claims must include non-certifying")
        if isinstance(required, list) and "deterministic artifact" not in required:
            errors.append("public_narrative.required_claims must include deterministic artifact")
        browser = narrative.get("browser_boundary")
        if not isinstance(browser, Mapping):
            errors.append("public_narrative.browser_boundary must be object")
        elif (
            browser.get("artifact_only_rendering") is not True
            or browser.get("client_side_claim_recomputation_allowed") is not False
            or browser.get("blocked_claim_suppression_allowed") is not False
            or browser.get("external_gap_softening_allowed") is not False
        ):
            errors.append("public_narrative.browser_boundary must be artifact-only with no suppression or softening")

    return errors
