"""Deterministic target, trajectory, and feasibility screen.

This module is a reduced-order review surface. It makes target choice, velocity,
time of flight, local dust/gas anchors, black-hole horizon geometry, and
capsule-risk linkage explicit without claiming mission readiness.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


SCHEMA_VERSION = "mission_feasibility_screen.v1"
GENERATOR = "scripts/build_mission_feasibility_screen_artifact.py"
PUBLIC_SCOPE = "target_velocity_time_feasibility_screen"
SOURCE_CAPSULE = "artifacts/capsule_survivability_lab.v1.json"
SOURCE_RISK_BUDGET = "artifacts/capsule_risk_budget.v1.json"
SOURCE_BASELINE = "mission/BASELINE_SCENARIO_v1.json"
SOURCE_ENV_BRIEF = "docs/research/CAPSULE_ENVIRONMENT_DATA_BRIEF_v1.md"

C_M_S = 299_792_458.0
JULIAN_YEAR_S = 31_557_600.0
LIGHT_YEAR_M = C_M_S * JULIAN_YEAR_S
G_M3_KG_S2 = 6.67430e-11
LOCAL_DUST_DENSITY_KG_M3 = 2.1e-24
LOCAL_DUST_DENSITY_SIGMA_KG_M3 = 0.6e-24
LOCAL_NEUTRAL_H_MASS_DENSITY_KG_M3 = 2.13e-22

DEFAULT_CAPSULE_ID = "baseline-stack"
BALLISTIC_TIME_ID = "ballistic-arrival"
DEFAULT_TARGET_ID = "reference-black-hole"
DEFAULT_VELOCITY_ID = "conditional-45"


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


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _control_lookup(items: Iterable[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {str(item["id"]): item for item in items if isinstance(item, Mapping) and isinstance(item.get("id"), str)}


def _risk_budget_lookup(risk_budget: Mapping[str, Any]) -> Dict[tuple[str, str], Mapping[str, Any]]:
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


def _black_hole_screen(*, baseline: Mapping[str, Any], target_id: str) -> Dict[str, Any]:
    applies = target_id in {"reference-black-hole", "sgr-a-rounded"}
    if not applies:
        return {
            "applies": False,
            "model": "not_black_hole_target",
            "claim_boundary": "No horizon-crossing geometry is evaluated for this target row.",
        }
    bh = baseline.get("bh_parameters", {})
    if not isinstance(bh, Mapping):
        bh = {}
    mass_kg = float(bh.get("mass_kg", 0.0))
    periapsis_m = float(bh.get("periapsis_distance_m", 0.0))
    schwarzschild_radius_m = 2.0 * G_M3_KG_S2 * mass_kg / (C_M_S**2)
    ratio = periapsis_m / schwarzschild_radius_m if schwarzschild_radius_m > 0.0 else math.inf
    return {
        "applies": True,
        "model": "schwarzschild_with_kerr_screening_placeholder",
        "mass_kg": _round(mass_kg, 6),
        "schwarzschild_radius_m": _round(schwarzschild_radius_m, 6),
        "periapsis_distance_m": _round(periapsis_m, 6),
        "periapsis_to_schwarzschild_ratio": _round(ratio, 12),
        "crossing_condition_met": bool(periapsis_m <= schwarzschild_radius_m),
        "kerr_screening": [
            {
                "spin_a_dimensionless": 0.0,
                "outer_horizon_vs_schwarzschild_ratio": 1.0,
                "status": "implemented_screen",
            },
            {
                "spin_a_dimensionless": 0.5,
                "outer_horizon_vs_schwarzschild_ratio": _round((1.0 + math.sqrt(1.0 - 0.5**2)) / 2.0, 12),
                "status": "screen_only_not_metric_integration",
            },
            {
                "spin_a_dimensionless": 0.99,
                "outer_horizon_vs_schwarzschild_ratio": _round((1.0 + math.sqrt(1.0 - 0.99**2)) / 2.0, 12),
                "status": "screen_only_not_metric_integration",
            },
        ],
        "claim_boundary": "This is a horizon-geometry screen, not GR trajectory integration or MHD accretion modeling.",
    }


def _time_class(years: float) -> str:
    if years < 100_000:
        return "near_interstellar"
    if years < 10_000_000:
        return "myr_sub_10"
    if years < 100_000_000:
        return "myr_10_to_100"
    return "hundred_myr_plus"


def _dust_screen(*, distance_ly: float, velocity_km_s: float, frontal_area_m2: float, dust_scale: float) -> Dict[str, Any]:
    path_m = distance_ly * LIGHT_YEAR_M
    swept_local_mass_kg = LOCAL_DUST_DENSITY_KG_M3 * path_m * frontal_area_m2
    swept_scaled_mass_kg = swept_local_mass_kg * dust_scale
    impact_energy_j = 0.5 * swept_scaled_mass_kg * (velocity_km_s * 1000.0) ** 2
    return {
        "local_dust_density_kg_m3": LOCAL_DUST_DENSITY_KG_M3,
        "local_dust_density_sigma_kg_m3": LOCAL_DUST_DENSITY_SIGMA_KG_M3,
        "dust_flux_scale": dust_scale,
        "swept_local_dust_mass_kg": _round(swept_local_mass_kg, 15),
        "swept_scaled_dust_mass_kg": _round(swept_scaled_mass_kg, 15),
        "bulk_kinetic_energy_j": _round(impact_energy_j, 6),
        "specific_kinetic_energy_kj_g": _round(0.5 * (velocity_km_s * 1000.0) ** 2 / 1_000_000.0, 6),
        "large_particle_tail_status": "assumption_bound_external_required",
        "claim_boundary": "Local dust mass density is a source-backed prior; mm/cm tail flux is not closed.",
    }


def _gas_screen(*, distance_ly: float, frontal_area_m2: float) -> Dict[str, Any]:
    path_m = distance_ly * LIGHT_YEAR_M
    swept_mass_kg = LOCAL_NEUTRAL_H_MASS_DENSITY_KG_M3 * path_m * frontal_area_m2
    return {
        "local_neutral_h_mass_density_kg_m3": LOCAL_NEUTRAL_H_MASS_DENSITY_KG_M3,
        "swept_local_neutral_h_mass_kg": _round(swept_mass_kg, 12),
        "applicability": "local heliosphere/VLISM anchor only; not a whole-path average.",
    }


def _cost_proxy(*, capsule_mass_kg: float, velocity_km_s: float, reference_velocity_km_s: float = 23.17) -> Dict[str, Any]:
    energy_j = 0.5 * capsule_mass_kg * (velocity_km_s * 1000.0) ** 2
    reference_energy_j = 0.5 * capsule_mass_kg * (reference_velocity_km_s * 1000.0) ** 2
    return {
        "capsule_kinetic_energy_j": _round(energy_j, 3),
        "relative_to_23_17_km_s": _round(energy_j / reference_energy_j if reference_energy_j else 0.0, 9),
        "procurement_status": "external_required",
        "claim_boundary": "Energy proxy is not a launch quote, procurement estimate, or mission architecture cost.",
    }


def _risk_link(row_id: str, risk_lookup: Mapping[tuple[str, str], Mapping[str, Any]]) -> Dict[str, Any]:
    risk_row = risk_lookup.get((row_id, "nominal"))
    if not isinstance(risk_row, Mapping):
        return {
            "matched": False,
            "row_id": row_id,
            "claim_boundary": "No nominal Capsule Risk Budget row matched this scenario.",
        }
    quantiles = risk_row.get("quantiles", {})
    risk_budget = risk_row.get("risk_budget", {})
    return {
        "matched": True,
        "row_id": row_id,
        "attack_mode_id": "nominal",
        "survival_p05": quantiles.get("p05") if isinstance(quantiles, Mapping) else None,
        "survival_p50": quantiles.get("p50") if isinstance(quantiles, Mapping) else None,
        "survival_p95": quantiles.get("p95") if isinstance(quantiles, Mapping) else None,
        "data_integrity_p50": risk_budget.get("data_integrity_probability") if isinstance(risk_budget, Mapping) else None,
        "evidence_gap_ids": risk_row.get("evidence_gap_ids", []),
        "blocking_claims": risk_row.get("blocking_claims", []),
    }


def _row_status(*, flight_years: float, risk_link: Mapping[str, Any], target_id: str) -> Dict[str, Any]:
    blockers: List[str] = []
    if flight_years > 100_000_000:
        blockers.append("flight_horizon_exceeds_100_myr_review_band")
    if not risk_link.get("matched"):
        blockers.append("capsule_risk_budget_match_missing")
    blockers.append("external_launch_procurement_and_navigation_review_required")
    blockers.append("dust_tail_and_material_qualification_external_required")
    if target_id in {"reference-black-hole", "sgr-a-rounded"}:
        blockers.append("black_hole_environment_model_external_required")
    return {
        "status": "review_required",
        "blockers": blockers,
        "non_certification_notice": True,
    }


def build_feasibility_screen(repo_root: Path) -> Dict[str, Any]:
    baseline = _load_json(repo_root / SOURCE_BASELINE)
    capsule = _load_json(repo_root / SOURCE_CAPSULE)
    risk_budget = _load_json(repo_root / SOURCE_RISK_BUDGET)
    risk_lookup = _risk_budget_lookup(risk_budget)

    controls = capsule.get("controls", {})
    if not isinstance(controls, Mapping):
        controls = {}
    targets = _control_lookup(controls.get("targets", []))
    velocities = _control_lookup(controls.get("velocityBands", []))
    rows = capsule.get("rows", [])
    if not isinstance(rows, list):
        rows = []
    capsule_model = baseline.get("capsule_model", {})
    environment_model = baseline.get("environment_model", {})
    if not isinstance(capsule_model, Mapping):
        capsule_model = {}
    if not isinstance(environment_model, Mapping):
        environment_model = {}
    capsule_mass_kg = float(capsule_model.get("mass_kg", 0.0))
    frontal_area_m2 = float(capsule_model.get("frontal_area_m2", 0.0))
    dust_scale = float(environment_model.get("dust_flux_scale", 1.0))

    scenario_rows: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if row.get("capsuleId") != DEFAULT_CAPSULE_ID or row.get("timeId") != BALLISTIC_TIME_ID:
            continue
        target_id = str(row.get("targetId"))
        velocity_id = str(row.get("velocityId"))
        distance_ly = float(row.get("distanceLy", 0.0))
        velocity_km_s = float(row.get("velocityKmS", 0.0))
        flight_years = float(row.get("flightYears", 0.0))
        risk = _risk_link(str(row.get("rowId")), risk_lookup)
        scenario_rows.append(
            {
                "id": f"feas-{target_id}-{velocity_id}",
                "source_capsule_row_id": row.get("rowId"),
                "target_id": target_id,
                "target_label": targets.get(target_id, {}).get("label", target_id),
                "target_detail": targets.get(target_id, {}).get("detail", ""),
                "distance_ly": _round(distance_ly, 9),
                "velocity_id": velocity_id,
                "velocity_label": velocities.get(velocity_id, {}).get("label", velocity_id),
                "velocity_detail": velocities.get(velocity_id, {}).get("detail", ""),
                "velocity_km_s": _round(velocity_km_s, 6),
                "velocity_fraction_c": _round((velocity_km_s * 1000.0) / C_M_S, 12),
                "flight_years": _round(flight_years, 6),
                "time_horizon_class": _time_class(flight_years),
                "black_hole_screen": _black_hole_screen(baseline=baseline, target_id=target_id),
                "dust_screen": _dust_screen(
                    distance_ly=distance_ly,
                    velocity_km_s=velocity_km_s,
                    frontal_area_m2=frontal_area_m2,
                    dust_scale=dust_scale,
                ),
                "gas_screen": _gas_screen(distance_ly=distance_ly, frontal_area_m2=frontal_area_m2),
                "radiation_material_hooks": {
                    "gcr_model_status": "reference_hook_only",
                    "material_transport_status": "external_required",
                    "archive_media_recovery_status": "external_required",
                    "claim_boundary": "No fixed Myr radiation dose or bit recovery claim is produced by this screen.",
                },
                "capsule_risk_budget_link": risk,
                "cost_energy_proxy": _cost_proxy(capsule_mass_kg=capsule_mass_kg, velocity_km_s=velocity_km_s),
                "feasibility": _row_status(flight_years=flight_years, risk_link=risk, target_id=target_id),
                "external_evidence_gaps": [
                    "target-specific line-of-sight dust and gas model",
                    "stack-level ballistic-limit and material qualification",
                    "radiation/material transport and archive bit recovery",
                    "launch procurement, navigation, legal, and operations review",
                ],
                "blocked_claims": [
                    "mission feasible",
                    "flight ready",
                    "certified capsule survival",
                    "guaranteed arrival or archive recovery",
                ],
            }
        )

    scenario_rows.sort(key=lambda item: (str(item["target_id"]), float(item["flight_years"]), str(item["velocity_id"])))
    default_row = next(
        (
            item
            for item in scenario_rows
            if item["target_id"] == DEFAULT_TARGET_ID and item["velocity_id"] == DEFAULT_VELOCITY_ID
        ),
        None,
    )
    matched_count = sum(1 for item in scenario_rows if item["capsule_risk_budget_link"].get("matched"))
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "public_scope": PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": {
            SOURCE_BASELINE: _sha256_file(repo_root / SOURCE_BASELINE),
            SOURCE_CAPSULE: _sha256_file(repo_root / SOURCE_CAPSULE),
            SOURCE_RISK_BUDGET: _sha256_file(repo_root / SOURCE_RISK_BUDGET),
            SOURCE_ENV_BRIEF: _sha256_file(repo_root / SOURCE_ENV_BRIEF),
        },
        "constants": {
            "c_m_s": C_M_S,
            "julian_year_s": JULIAN_YEAR_S,
            "light_year_m": LIGHT_YEAR_M,
            "g_m3_kg_s2": G_M3_KG_S2,
            "local_dust_density_kg_m3": LOCAL_DUST_DENSITY_KG_M3,
            "local_neutral_h_mass_density_kg_m3": LOCAL_NEUTRAL_H_MASS_DENSITY_KG_M3,
        },
        "target_count": len(targets),
        "velocity_count": len(velocities),
        "scenario_count": len(scenario_rows),
        "default_scenario_id": default_row.get("id") if isinstance(default_row, Mapping) else None,
        "default_black_hole_flight_years": default_row.get("flight_years") if isinstance(default_row, Mapping) else None,
        "capsule_risk_budget_match_count": matched_count,
        "scenario_rows": scenario_rows,
        "interpretation_limits": [
            "Ballistic time of flight ignores acceleration, navigation authority, and operational maintenance.",
            "Dust/gas screens use local anchors and do not close whole-path or target-region environments.",
            "Cost proxy is kinetic-energy scaling only, not procurement or launch pricing.",
            "Every row is review-required and non-certifying.",
        ],
    }


def validate_feasibility_screen(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be mission_feasibility_screen.v1")
    if payload.get("generator") != GENERATOR:
        errors.append("generator mismatch")
    if payload.get("public_scope") != PUBLIC_SCOPE:
        errors.append("public_scope mismatch")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("target_count") != 3:
        errors.append("target_count must be 3")
    if payload.get("velocity_count") != 5:
        errors.append("velocity_count must be 5")
    rows = payload.get("scenario_rows")
    if not isinstance(rows, list) or len(rows) != 15:
        errors.append("scenario_rows must contain exactly 15 rows")
        rows = []
    if payload.get("scenario_count") != len(rows):
        errors.append("scenario_count must equal len(scenario_rows)")
    if payload.get("capsule_risk_budget_match_count") != len(rows):
        errors.append("capsule_risk_budget_match_count must equal nominal risk-budget-linked row count")
    source_artifacts = payload.get("source_artifacts")
    if not isinstance(source_artifacts, Mapping):
        errors.append("source_artifacts must be an object")
    else:
        for path in (SOURCE_BASELINE, SOURCE_CAPSULE, SOURCE_RISK_BUDGET, SOURCE_ENV_BRIEF):
            digest = source_artifacts.get(path)
            if not isinstance(digest, str) or len(digest) != 64:
                errors.append(f"source_artifacts missing sha256 for {path}")
    default_seen = False
    target_ids = set()
    velocity_ids = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"scenario_rows[{index}] must be object")
            continue
        prefix = f"scenario_rows[{index}]"
        target_ids.add(row.get("target_id"))
        velocity_ids.add(row.get("velocity_id"))
        for key in ("distance_ly", "velocity_km_s", "velocity_fraction_c", "flight_years"):
            if not _finite_number(row.get(key)) or float(row.get(key)) <= 0.0:
                errors.append(f"{prefix}.{key} must be a positive finite number")
        if not isinstance(row.get("dust_screen"), Mapping):
            errors.append(f"{prefix}.dust_screen must be object")
        else:
            dust = row["dust_screen"]
            for key in ("swept_scaled_dust_mass_kg", "bulk_kinetic_energy_j", "specific_kinetic_energy_kj_g"):
                if not _finite_number(dust.get(key)) or float(dust.get(key)) < 0.0:
                    errors.append(f"{prefix}.dust_screen.{key} must be non-negative")
            if dust.get("large_particle_tail_status") != "assumption_bound_external_required":
                errors.append(f"{prefix}.dust_screen must keep large-particle tail external")
        risk = row.get("capsule_risk_budget_link")
        if not isinstance(risk, Mapping) or risk.get("matched") is not True:
            errors.append(f"{prefix}.capsule_risk_budget_link must match")
        elif not _finite_number(risk.get("survival_p50")):
            errors.append(f"{prefix}.capsule_risk_budget_link.survival_p50 must be finite")
        feasibility = row.get("feasibility")
        if not isinstance(feasibility, Mapping) or feasibility.get("non_certification_notice") is not True:
            errors.append(f"{prefix}.feasibility must keep non_certification_notice")
        if not isinstance(row.get("external_evidence_gaps"), list) or not row["external_evidence_gaps"]:
            errors.append(f"{prefix}.external_evidence_gaps must be non-empty")
        if not isinstance(row.get("blocked_claims"), list) or "flight ready" not in row["blocked_claims"]:
            errors.append(f"{prefix}.blocked_claims must block flight-ready claims")
        black_hole = row.get("black_hole_screen")
        if row.get("target_id") in {"reference-black-hole", "sgr-a-rounded"}:
            if not isinstance(black_hole, Mapping) or black_hole.get("applies") is not True:
                errors.append(f"{prefix}.black_hole_screen must apply")
            elif black_hole.get("crossing_condition_met") is not True:
                errors.append(f"{prefix}.black_hole_screen crossing_condition_met must be true")
        if row.get("target_id") == DEFAULT_TARGET_ID and row.get("velocity_id") == DEFAULT_VELOCITY_ID:
            default_seen = True
            years = float(row.get("flight_years", 0.0))
            if not 10_000_000 <= years <= 10_700_000:
                errors.append("default reference black-hole conditional-45 row must stay near 10 Myr")
    if target_ids != {"reference-black-hole", "alpha-centauri-scale", "sgr-a-rounded"}:
        errors.append("target ids must match Capsule Lab controls")
    if velocity_ids != {"oberth-23", "oberth-34", "conditional-45", "stress-60", "concept-95"}:
        errors.append("velocity ids must match Capsule Lab controls")
    if not default_seen:
        errors.append("default reference black-hole conditional-45 row missing")
    return errors
