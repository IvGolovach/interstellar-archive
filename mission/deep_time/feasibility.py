"""Deterministic deep-time archive feasibility artifact.

The artifact intentionally keeps the public claim narrow: present-day material
classes can be arranged into a plausible passive archive study, but the repo
does not yet contain lab qualification, whole-path environment closure, or a
closed recovery probability.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from models.constants import (
    AU_M,
    GRAVITATIONAL_CONSTANT_M3_KG_S2,
    LIGHT_YEAR_M,
    PU238_HALF_LIFE_YEARS,
    SECONDS_PER_JULIAN_YEAR,
    SOLAR_MASS_KG,
)
from models.core_physics import (
    oberth_asymptotic_speed_m_s,
    rtg_power_fraction,
    schwarzschild_radius_m,
    time_of_flight_years,
)


SCHEMA_VERSION = "deep_time_archive_feasibility.v1"
GENERATOR = "scripts/build_deep_time_archive_feasibility_artifact.py"
PUBLIC_SCOPE = "passive_archive_boundary_study"

SOURCE_SPEC = "mission/DEEP_TIME_ARCHIVE_FEASIBILITY_PROOF_SPEC_v1.md"
SOURCE_BUILDER = GENERATOR
SOURCE_VALIDATOR = "scripts/ci/deep_time_archive_feasibility_validate.py"
SOURCE_TEST = "tests/test_deep_time_archive_feasibility.py"
SOURCE_DOC = "docs/DEEP_TIME_ARCHIVE_FEASIBILITY_SPEC.md"
SOURCE_CAPSULE_DESIGN = "mission/capsule/capsule_design.v1.json"
SOURCE_CAPSULE_RISK = "artifacts/capsule_risk_budget.v1.json"
SOURCE_MISSION_PROBABILITY = "artifacts/mission_probability_coupling.v1.json"
SOURCE_CORE_PHYSICS = "models/core_physics.py"

SOURCE_PATHS = [
    SOURCE_SPEC,
    SOURCE_DOC,
    SOURCE_CAPSULE_DESIGN,
    SOURCE_CAPSULE_RISK,
    SOURCE_MISSION_PROBABILITY,
    SOURCE_CORE_PHYSICS,
    SOURCE_BUILDER,
    SOURCE_VALIDATOR,
    SOURCE_TEST,
]

REFERENCE_DISTANCE_LY = 1560.0
REFERENCE_BLACK_HOLE_MASS_MSUN = 10.0
REFERENCE_DUST_DENSITY_KG_M3 = 2.1e-24
REFERENCE_DUST_DENSITY_SIGMA_KG_M3 = 0.6e-24
GRAIN_DENSITY_KG_M3 = 3300.0
DIRECT_HVIT_MAX_VELOCITY_KM_S = 7.0

FORBIDDEN_CLAIMS = [
    "mission feasible",
    "proven feasible",
    "flight-ready",
    "flight ready",
    "certified",
    "qualified",
    "guaranteed survival",
    "guaranteed archive recovery",
    "black-hole capture targetable",
    "external validation completed",
    "third-party validated",
    "procurement-grade cost estimate",
    "launch vehicle selected",
]

REQUIRED_OPEN_FACTORS = [
    "target_delivery",
    "whole_path_environment",
    "stack_ballistic_limit",
    "material_aging",
    "media_readability",
    "recovery_readout",
]


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_artifacts(repo_root: Path) -> List[Dict[str, str]]:
    return [{"path": path, "sha256": _sha256_file(repo_root / path)} for path in SOURCE_PATHS]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _determinism_signature(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _distance_au(distance_ly: float = REFERENCE_DISTANCE_LY) -> float:
    return (distance_ly * LIGHT_YEAR_M) / AU_M


def _grain_mass_kg(radius_m: float, density_kg_m3: float = GRAIN_DENSITY_KG_M3) -> float:
    return (4.0 / 3.0) * math.pi * (radius_m**3) * density_kg_m3


def _impact_energy_j(radius_m: float, velocity_km_s: float) -> float:
    mass = _grain_mass_kg(radius_m)
    velocity_m_s = velocity_km_s * 1_000.0
    return 0.5 * mass * velocity_m_s * velocity_m_s


def _impact_momentum_kg_m_s(radius_m: float, velocity_km_s: float) -> float:
    return _grain_mass_kg(radius_m) * velocity_km_s * 1_000.0


def _impact_energy_table() -> List[Dict[str, Any]]:
    radii = [
        ("0p1_um", 1.0e-7),
        ("1_um", 1.0e-6),
        ("10_um", 1.0e-5),
        ("100_um", 1.0e-4),
        ("1_mm", 1.0e-3),
        ("1_cm", 1.0e-2),
    ]
    velocities = [23.0, 34.0, 45.0, 60.0]
    rows: List[Dict[str, Any]] = []
    for size_id, radius_m in radii:
        rows.append(
            {
                "size_id": size_id,
                "radius_m": radius_m,
                "grain_density_kg_m3": GRAIN_DENSITY_KG_M3,
                "mass_kg": _round(_grain_mass_kg(radius_m), 24),
                "energy_j_by_velocity_km_s": {
                    f"{velocity:g}": _round(_impact_energy_j(radius_m, velocity), 12)
                    for velocity in velocities
                },
                "momentum_kg_m_s_by_velocity_km_s": {
                    f"{velocity:g}": _round(_impact_momentum_kg_m_s(radius_m, velocity), 18)
                    for velocity in velocities
                },
            }
        )
    return rows


def _monodisperse_hit_sanity(frontal_area_m2: float) -> List[Dict[str, Any]]:
    distance_m = REFERENCE_DISTANCE_LY * LIGHT_YEAR_M
    rows: List[Dict[str, Any]] = []
    for size_id, radius_m in (
        ("1_um", 1.0e-6),
        ("10_um", 1.0e-5),
        ("100_um", 1.0e-4),
        ("1_mm", 1.0e-3),
        ("1_cm", 1.0e-2),
    ):
        mass = _grain_mass_kg(radius_m)
        number_density_m3 = REFERENCE_DUST_DENSITY_KG_M3 / mass
        expected_hits = number_density_m3 * frontal_area_m2 * distance_m
        rows.append(
            {
                "size_id": size_id,
                "radius_m": radius_m,
                "assumption": "all Ulysses local dust mass density placed into one grain radius; sanity check only",
                "expected_hits_lambda": _round(expected_hits, 9),
                "p_at_least_one": _round(1.0 - math.exp(-min(expected_hits, 700.0)), 12),
                "validity": "not a physical size distribution; large-tail risk must be modeled separately",
            }
        )
    return rows


def _b_max_au(r_int_au: float, velocity_km_s: float, mass_msun: float = REFERENCE_BLACK_HOLE_MASS_MSUN) -> float:
    r_m = r_int_au * AU_M
    velocity_m_s = velocity_km_s * 1_000.0
    mass_kg = mass_msun * SOLAR_MASS_KG
    focusing = 1.0 + (2.0 * GRAVITATIONAL_CONSTANT_M3_KG_S2 * mass_kg) / (r_m * velocity_m_s * velocity_m_s)
    return r_int_au * math.sqrt(focusing)


def _encounter_geometry() -> Dict[str, Any]:
    distance_au = _distance_au()
    rs_m = schwarzschild_radius_m(REFERENCE_BLACK_HOLE_MASS_MSUN * SOLAR_MASS_KG)
    rs_au = rs_m / AU_M
    case_b_rows: List[Dict[str, Any]] = []
    for r_int_au in (100.0, 1_000.0):
        for velocity_km_s in (23.0, 45.0):
            b_au = _b_max_au(r_int_au, velocity_km_s)
            theta_arcsec = (b_au / distance_au) * 206_265.0
            delta_v_m_s = velocity_km_s * 1_000.0 * (b_au / distance_au)
            case_b_rows.append(
                {
                    "case_id": f"case-b-r{int(r_int_au)}au-v{int(velocity_km_s)}",
                    "R_int_au": r_int_au,
                    "velocity_km_s": velocity_km_s,
                    "b_max_au": _round(b_au, 9),
                    "theta_cone_arcsec": _round(theta_arcsec, 9),
                    "delta_v_perp_req_m_s": _round(delta_v_m_s, 12),
                    "focusing_model": "newtonian_first_order",
                    "control_interpretation": "early-window reshaping possible if worldline and environment uncertainty are bounded",
                }
            )
    case_a_rows: List[Dict[str, Any]] = []
    for velocity_km_s in (23.0, 45.0):
        geometric_theta_microarcsec = (rs_au / distance_au) * 206_265.0 * 1_000_000.0
        geometric_delta_v_m_s = velocity_km_s * 1_000.0 * (rs_au / distance_au)
        capture_b_au = _b_max_au(rs_au, velocity_km_s)
        capture_theta_microarcsec = (capture_b_au / distance_au) * 206_265.0 * 1_000_000.0
        capture_delta_v_m_s = velocity_km_s * 1_000.0 * (capture_b_au / distance_au)
        case_a_rows.append(
            {
                "case_id": f"case-a-horizon-v{int(velocity_km_s)}",
                "R_int_au": _round(rs_au, 18),
                "velocity_km_s": velocity_km_s,
                "geometric_theta_microarcsec": _round(geometric_theta_microarcsec, 12),
                "geometric_delta_v_perp_req_m_s": _round(geometric_delta_v_m_s, 18),
                "focused_capture_b_max_au": _round(capture_b_au, 12),
                "focused_capture_theta_microarcsec": _round(capture_theta_microarcsec, 9),
                "focused_capture_delta_v_perp_req_m_s": _round(capture_delta_v_m_s, 15),
                "control_interpretation": "not operationally controllable on Myr horizons",
                "claim_boundary": "capture or horizon crossing is a boundary demonstration, not a targetable mission objective",
            }
        )
    return {
        "reference_mass_msun": REFERENCE_BLACK_HOLE_MASS_MSUN,
        "schwarzschild_radius_km": _round(rs_m / 1_000.0, 9),
        "distance_au": _round(distance_au, 3),
        "formulae": {
            "b_max": "R_int * sqrt(1 + 2GM / (R_int * v_inf^2))",
            "theta_cone": "b_max / D",
            "delta_v_perp_req": "v_inf * b_max / D",
        },
        "case_b_encounter_rows": case_b_rows,
        "case_a_capture_rows": case_a_rows,
    }


def _trajectory_modes() -> Dict[str, Any]:
    baseline_rows: List[Dict[str, Any]] = []
    for q_au in (0.05, 0.10):
        for delta_v_m_s in (2_000.0, 3_000.0):
            speed_m_s = oberth_asymptotic_speed_m_s(q_au=q_au, delta_v_m_s=delta_v_m_s)
            baseline_rows.append(
                {
                    "mode_id": f"baseline-q{q_au:.2f}-dv{int(delta_v_m_s)}",
                    "velocity_band": "baseline_23_34_km_s",
                    "q_au": q_au,
                    "srm_delta_v_m_s": delta_v_m_s,
                    "inbound_vinf_m_s": 0.0,
                    "outbound_vinf_km_s": _round(speed_m_s / 1_000.0, 9),
                    "flight_time_myr_1560ly": _round(time_of_flight_years(REFERENCE_DISTANCE_LY, speed_m_s) / 1_000_000.0, 9),
                    "claim_boundary": "near-parabolic Sun-Oberth energy check",
                }
            )
    conditional_rows: List[Dict[str, Any]] = []
    for inbound_vinf_km_s in (10.0, 20.0, 30.0):
        speed_m_s = oberth_asymptotic_speed_m_s(
            q_au=0.05,
            delta_v_m_s=3_000.0,
            inbound_vinf_m_s=inbound_vinf_km_s * 1_000.0,
        )
        conditional_rows.append(
            {
                "mode_id": f"conditional-q0.05-dv3000-inbound{int(inbound_vinf_km_s)}",
                "velocity_band": "conditional_35_45_km_s",
                "q_au": 0.05,
                "srm_delta_v_m_s": 3_000.0,
                "inbound_vinf_m_s": inbound_vinf_km_s * 1_000.0,
                "outbound_vinf_km_s": _round(speed_m_s / 1_000.0, 9),
                "flight_time_myr_1560ly": _round(time_of_flight_years(REFERENCE_DISTANCE_LY, speed_m_s) / 1_000_000.0, 9),
                "claim_boundary": "conditional speed band; requires inbound-energy and TPS/SRM closure",
            }
        )
    return {
        "architecture_modes": [
            {
                "mode_id": "archive_only",
                "summary": "Passive archive survivability study; no Sun-Oberth dependency and no terminal-interaction claim.",
                "allowed_success_levels": ["S0", "S1", "S2"],
                "blocked_success_levels": ["S3_targeting_guarantee"],
                "oberth_gate_required": False,
                "claim_boundary": "can study passive recovery physics without claiming Myr targeting control",
            },
            {
                "mode_id": "flagship_full",
                "summary": "Earth/Jupiter/Sun-Oberth option with finite early correction window before passive drift.",
                "allowed_success_levels": ["S0", "S1", "S2", "S3_probabilistic_outcome_class"],
                "blocked_success_levels": ["S3_capture_control", "mission_ready"],
                "oberth_gate_required": True,
                "claim_boundary": "conditional architecture; TPS/SRM, inbound-energy, RTG, and OD gates remain external",
            },
        ],
        "baseline_23_34_km_s": sorted(baseline_rows, key=lambda row: row["outbound_vinf_km_s"]),
        "conditional_35_45_km_s": sorted(conditional_rows, key=lambda row: row["outbound_vinf_km_s"]),
        "rtg_decay": [
            {
                "years": years,
                "pu238_thermal_fraction": _round(rtg_power_fraction(years, PU238_HALF_LIFE_YEARS), 15),
                "interpretation": "radioactive thermal fraction only; actuator and electronics reliability are separate",
            }
            for years in (10.0, 20.0, 50.0, 100.0, 1_000.0, 10_000_000.0)
        ],
        "control_window": {
            "baseline_years": [10, 50],
            "stretch_years": [100, 1000],
            "baseline_status": "credible_only_with_external_OD_and_actuator_evidence",
            "stretch_status": "reliability_limited_external_required",
            "no_myr_actuation_claim": True,
        },
        "perihelion_gate": {
            "q_au_range": [0.05, 0.10],
            "solar_flux_mw_m2_range": [0.1361, 0.5444],
            "parker_heritage_applicability": "solar-proximity TPS precedent only",
            "srm_hot_vacuum_integration_status": "external_required",
            "downgrade_path": "if TPS/SRM gate fails, keep Archive-only or lower-energy escape mode",
        },
    }


def _target_corridor() -> Dict[str, Any]:
    proper_motion_total_mas_yr = math.sqrt((6.437**2) + (25.480**2))
    flight_years_45 = time_of_flight_years(REFERENCE_DISTANCE_LY, 45_000.0)
    naive_sky_motion_deg = (proper_motion_total_mas_yr / 3_600_000.0) * flight_years_45
    pm_uncertainty_mas_yr = math.sqrt((0.123**2) + (0.093**2))
    distance_au = _distance_au()
    pm_uncertainty_rad = (pm_uncertainty_mas_yr / 1_000.0) / 206_265.0
    cross_track_uncertainty_au = distance_au * pm_uncertainty_rad * flight_years_45
    return {
        "target_id": "gaia-bh1-reference",
        "target_role": "reference catalog black-hole corridor for 1560 ly scale checks",
        "catalog_ids": ["Gaia DR3 4373465352415301632"],
        "distance_ly": REFERENCE_DISTANCE_LY,
        "distance_pc_from_parallax": _round(1_000.0 / 2.0700, 9),
        "icrs_j2000": {
            "ra_hms": "17 28 41.0966126056",
            "dec_dms": "-00 34 51.523377959",
            "ra_deg": _round((17.0 + 28.0 / 60.0 + 41.0966126056 / 3600.0) * 15.0, 12),
            "dec_deg": _round(-(34.0 / 60.0 + 51.523377959 / 3600.0), 12),
        },
        "galactic": {"l_deg": 22.6257666714495, "b_deg": 18.0458390584611},
        "astrometry": {
            "parallax_mas": 2.0700,
            "parallax_sigma_mas": 0.1167,
            "pm_ra_mas_yr": -6.437,
            "pm_ra_sigma_mas_yr": 0.123,
            "pm_dec_mas_yr": -25.480,
            "pm_dec_sigma_mas_yr": 0.093,
            "radial_velocity_km_s": 23.03,
            "radial_velocity_sigma_km_s": 2.63,
        },
        "static_environment_los": {
            "status": "usable_for_present_day_sightline_only",
            "required_datasets": ["Bayestar 3D dust", "HI4PI H I", "local VLISM anchors"],
        },
        "dynamic_target_worldline_corridor": {
            "status": "external_required",
            "naive_pm_sky_motion_deg_over_45km_s_arrival": _round(naive_sky_motion_deg, 6),
            "catalog_pm_uncertainty_cross_track_au_over_45km_s_arrival": _round(cross_track_uncertainty_au, 3),
            "required_models": ["Galactic potential", "stellar encounter perturbations", "full astrometric covariance"],
        },
        "claim_boundary": "current RA/Dec is not a 10 Myr terminal target corridor",
        "source_ids": ["SRC-ESA-GAIA-BH1", "SRC-SIMBAD-GAIA-BH1", "SRC-ELBADRY-GAIA-BH1-2023"],
    }


def _capsule_architecture(capsule_design: Mapping[str, Any]) -> Dict[str, Any]:
    layers = capsule_design.get("layers", [])
    if not isinstance(layers, list):
        layers = []
    layer_by_id = {layer.get("layer_id"): layer for layer in layers if isinstance(layer, Mapping)}
    inputs = capsule_design.get("survivability_model_inputs", {})
    if not isinstance(inputs, Mapping):
        inputs = {}
    frontal_area_m2 = float((inputs.get("frontal_area_m2") or {}).get("value", 1.81))
    shield_mass_kg = math.fsum(
        float((layer_by_id.get(layer_id) or {}).get("mass_kg", 0.0))
        for layer_id in ("c_c_sic_tps", "al_li_bumper", "b4c_ta_rear_wall")
    )
    current_areal_density = shield_mass_kg / frontal_area_m2
    equivalent_diameter_m = math.sqrt((4.0 * frontal_area_m2) / math.pi)
    return {
        "current_v1_proxy": {
            "design_id": capsule_design.get("design_id"),
            "configured_capsule_mass_kg": (capsule_design.get("mass_budget") or {}).get("configured_capsule_mass_kg"),
            "frontal_area_m2": _round(frontal_area_m2, 9),
            "equivalent_diameter_m": _round(equivalent_diameter_m, 9),
            "front_shield_mass_kg": _round(shield_mass_kg, 9),
            "front_shield_areal_density_kg_m2": _round(current_areal_density, 9),
            "stand_off_gap_m": (layer_by_id.get("stand_off_gap") or {}).get("stand_off_gap_m"),
            "interpretation": "optimistic reduced-order proxy, not stack-qualified hardware",
        },
        "physical_baseline_recommendation": {
            "geometry": "spin-stabilized shield-forward short axisymmetric capsule",
            "forward_shield_diameter_m_range": [1.35, 1.55],
            "frontal_area_m2_range": [1.43, 1.89],
            "overall_length_m_range": [0.75, 1.05],
            "stand_off_gap_m_range": [0.30, 0.45],
            "total_capsule_mass_kg_range": [280.0, 450.0],
            "front_shield_areal_density_kg_m2_target": [60.0, 120.0],
            "severe_dust_sensitivity_kg_m2": 150.0,
            "claim_boundary": "recommended sizing target pending ballistic-limit and hydrocode evidence",
        },
        "layer_recommendations": [
            {"layer": "C/C-SiC or C/C TPS erosion face", "thickness_m": [0.015, 0.030], "areal_density_kg_m2": [25.0, 65.0]},
            {"layer": "Al-Li sacrificial bumper", "thickness_m": [0.003, 0.008], "areal_density_kg_m2": [8.0, 22.0]},
            {"layer": "open Whipple stand-off", "gap_m": [0.30, 0.45], "areal_density_kg_m2": [0.0, 0.0]},
            {"layer": "B4C/Ta graded rear wall", "thickness_m": [0.0055, 0.014], "areal_density_kg_m2": [20.0, 65.0]},
            {"layer": "Ti-6Al-4V vault", "thickness_m": [0.008, 0.015], "mass_kg": [40.0, 90.0]},
            {"layer": "hybrid media package", "mass_kg": [20.0, 50.0]},
        ],
        "qualification_status": "external_required",
    }


def _dust_environment(frontal_area_m2: float) -> Dict[str, Any]:
    return {
        "source_backed_local_anchor": {
            "dust_density_kg_m3": REFERENCE_DUST_DENSITY_KG_M3,
            "dust_density_sigma_kg_m3": REFERENCE_DUST_DENSITY_SIGMA_KG_M3,
            "gas_to_dust_ratio": 193.0,
            "source_id": "SRC-ULYSSES-DUST-KRUEGER-2015",
            "applicability": "local interstellar dust prior only, not whole-path route truth",
        },
        "dust_size_regimes": [
            {
                "regime_id": "mrn_extinction_small_grains",
                "size_range_m": [5.0e-9, 2.5e-7],
                "distribution": "dn/da proportional to a^-3.5",
                "source_id": "SRC-MRN-1977",
                "validity": "small extinction grains; validator must reject extrapolation to mm/cm",
            },
            {
                "regime_id": "ulysses_local_large_grains",
                "size_range_m": [1.0e-7, 1.0e-6],
                "source_id": "SRC-ULYSSES-DUST-KRUEGER-2015",
                "validity": "local in-situ evidence; not universal route distribution",
            },
            {
                "regime_id": "catastrophic_tail_sensitivity",
                "size_range_m": [1.0e-4, 1.0e-2],
                "source_id": "SRC-DEEP-TIME-FEASIBILITY-ASSUMPTION",
                "validity": "assumption-bound mm/cm kill-tail sensitivity",
            },
        ],
        "impact_energy_table": _impact_energy_table(),
        "monodisperse_density_sanity": _monodisperse_hit_sanity(frontal_area_m2),
        "shield_response_boundary": {
            "direct_test_velocity_max_km_s": DIRECT_HVIT_MAX_VELOCITY_KM_S,
            "repo_velocity_bins_km_s": [23.0, 34.0, 45.0, 60.0],
            "hydrocode_extrapolation_required": True,
            "single_event_kill_candidates": ["mm_class_impact", "cm_class_impact", "dense_dust_cloud"],
            "claim_boundary": "do not mark shield_handles=true at 23-60 km/s without external stack evidence",
        },
    }


def _media_readability() -> Dict[str, Any]:
    return {
        "recommended_stack": [
            "analog etched sapphire/ceramic/metal bootstrap",
            "duplicated internal laser-written fused silica digital payload",
            "physically separated copies",
            "interleaved ECC with explicit erasure marking",
        ],
        "dense_payload_medium": {
            "medium_type": "high-purity fused silica or quartz-glass internal laser-written storage",
            "source_ids": ["SRC-PROJECT-SILICA-NATURE-2026", "SRC-SOUTHAMPTON-5D-FUSED-SILICA"],
            "supported_claim": "plausible material and encoding class for passive archival storage",
            "unsupported_claim": "10 Myr interstellar readability proven",
        },
        "bootstrap_medium": {
            "medium_type": "sapphire, ceramic, nickel, titanium, or equivalent analog plates",
            "source_ids": ["SRC-ROSETTA-DISK", "SRC-WIPP-MARKERS"],
            "purpose": "make the artifact recognizable and decoder grammar derivable without onboard power",
        },
        "probability_chain": [
            "P_media_physical_intact",
            "P_readable_given_intact",
            "P_decode_given_readable_and_damage",
        ],
        "copy_failure_model": {
            "formula": "P(all copies fail) = p_common + (1 - p_common) * product(p_fail_i)",
            "independence_warning": "three copies are not independent unless physical separation and damage tests support it",
        },
        "required_test_campaigns": [
            "coupon matrix",
            "accelerated aging",
            "radiation exposure and post-readout",
            "shock and fracture",
            "damage-to-decode",
            "bootstrap comprehension",
            "correlated failure Monte Carlo",
        ],
        "ten_myr_experimental_proof_available": False,
    }


def _source_records() -> List[Dict[str, Any]]:
    return [
        {
            "source_id": "SRC-ESA-GAIA-BH1",
            "label": "ESA Gaia BH1/BH2 announcement",
            "url": "https://www.esa.int/Science_Exploration/Space_Science/Gaia/Gaia_discovers_a_new_family_of_black_holes",
            "grade": "A",
            "quantity": "1560 ly Gaia BH1 distance context and approximately 10 solar mass black-hole class",
            "validity_bounds": "public discovery context, not trajectory worldline closure",
        },
        {
            "source_id": "SRC-SIMBAD-GAIA-BH1",
            "label": "SIMBAD Gaia DR3 4373465352415301632",
            "url": "https://simbad.cds.unistra.fr/simbad/sim-basic?Ident=Gaia+DR3+4373465352415301632&submit=SIMBAD+search",
            "grade": "A",
            "quantity": "ICRS coordinates, parallax, proper motion, radial velocity",
            "validity_bounds": "catalog state at epoch, not a Myr propagated target corridor",
        },
        {
            "source_id": "SRC-ELBADRY-GAIA-BH1-2023",
            "label": "El-Badry et al. Gaia BH1 paper",
            "url": "https://academic.oup.com/mnras/article/518/1/1057/6794289",
            "doi": "10.1093/mnras/stac3140",
            "grade": "A",
            "quantity": "Gaia BH1 astrophysical reference",
            "validity_bounds": "target identity and astrophysical context",
        },
        {
            "source_id": "SRC-ULYSSES-DUST-KRUEGER-2015",
            "label": "16 years of Ulysses interstellar dust measurements",
            "url": "https://arxiv.org/abs/1510.06180",
            "doi": "10.1088/0004-637X/812/2/139",
            "grade": "A",
            "quantity": "(2.1 +/- 0.6)e-24 kg/m3 local dust density, gas-to-dust 193 +85/-57",
            "validity_bounds": "local interstellar prior, not whole-route truth",
        },
        {
            "source_id": "SRC-MRN-1977",
            "label": "Mathis, Rumpl, Nordsieck dust size distribution",
            "url": "https://adsabs.harvard.edu/abs/1977ApJ...217..425M",
            "doi": "10.1086/155591",
            "grade": "A",
            "quantity": "small-grain extinction distribution",
            "validity_bounds": "do not extrapolate to mm/cm kill tail",
        },
        {
            "source_id": "SRC-NASA-HVIT",
            "label": "NASA JSC HyperVelocity Impact Technology testing capability",
            "url": "https://hvit.jsc.nasa.gov/hypervelocity-testing/",
            "grade": "B",
            "quantity": "100 micron to 10 mm aluminum projectiles below 2 to above 7 km/s",
            "validity_bounds": "test heritage below repo cruise impact velocities",
        },
        {
            "source_id": "SRC-PARKER-SOLAR-PROBE",
            "label": "NASA Parker Solar Probe TPS context",
            "url": "https://science.nasa.gov/mission/parker-solar-probe/",
            "grade": "B",
            "quantity": "4.5 inch carbon-composite shield and near-Sun thermal precedent",
            "validity_bounds": "heritage context, not integrated Sun-Oberth TPS/SRM qualification",
        },
        {
            "source_id": "SRC-NASA-NIAC-SOLAR-OBERTH",
            "label": "NASA NIAC combined heat shield and solar thermal propulsion for Oberth",
            "url": "https://www.nasa.gov/general/combined-heat-shield-and-solar-thermal-propulsion-system-for-an-oberth-manuever/",
            "grade": "B",
            "quantity": "solar Oberth concept and 2800 K subscale prototype context",
            "validity_bounds": "concept/prototype context with full-scale questions open",
        },
        {
            "source_id": "SRC-PROJECT-SILICA-NATURE-2026",
            "label": "Laser writing in glass for dense archival data storage",
            "url": "https://www.nature.com/articles/s41586-025-10042-w",
            "grade": "A",
            "quantity": "glass write/read/decode and TB-scale archival storage demonstration",
            "validity_bounds": "archival longevity evidence is not a 10 Myr interstellar proof",
        },
        {
            "source_id": "SRC-ROSETTA-DISK",
            "label": "Rosetta Project disk",
            "url": "https://rosettaproject.org/disk/interactive/",
            "grade": "B",
            "quantity": "analog human-readable bootstrap precedent",
            "validity_bounds": "readability design precedent, not interstellar material qualification",
        },
    ]


def _risk_proxy_summary(capsule_risk: Mapping[str, Any]) -> Dict[str, Any]:
    default_id = capsule_risk.get("default_row_id")
    rows = capsule_risk.get("risk_budgets", [])
    if not isinstance(rows, list):
        rows = []
    default_nominal = None
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if row.get("row_id") == default_id and row.get("attack_mode_id") == "nominal":
            default_nominal = row
            break
    quantiles = default_nominal.get("quantiles", {}) if isinstance(default_nominal, Mapping) else {}
    attack_modes = capsule_risk.get("attack_modes", {})
    return {
        "source_artifact_ref": SOURCE_CAPSULE_RISK,
        "default_row_id": default_id,
        "nominal_capsule_survival_quantiles": quantiles,
        "attack_modes_available": [
            mode.get("id")
            for mode in (attack_modes.get("modes", []) if isinstance(attack_modes, Mapping) else [])
            if isinstance(mode, Mapping)
        ],
        "interpretation": "existing repo proxy; not hardware qualification or final S2 closure",
    }


def _probability_decomposition(capsule_risk: Mapping[str, Any], mission_probability: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "formula": (
            "P_archive_recoverable = P(S0_launch_escape_intact) * P(S1_verified) * "
            "P(S2_environment_path) * P(S2_capsule_survival) * P(S2_data_recovered) * "
            "P(S3_discovery_retrieval_decode)"
        ),
        "full_P_archive_recoverable": None,
        "null_reason": "target delivery, whole-path environment, hardware qualification, and future recovery/readout remain external-open",
        "repo_proxy_inputs": {
            "capsule_risk_budget": _risk_proxy_summary(capsule_risk),
            "mission_probability_coupling_ref": SOURCE_MISSION_PROBABILITY,
            "mission_probability_schema_version": mission_probability.get("schema_version"),
        },
        "factor_status": [
            {"factor_id": "S0_launch_escape_intact", "status": "external_required", "value": None},
            {"factor_id": "S1_verified_OD_and_archive", "status": "external_required", "value": None},
            {"factor_id": "S2_environment_path", "status": "proxy_plus_assumption", "value": None},
            {"factor_id": "S2_capsule_survival", "status": "repo_proxy_not_qualified", "value": None},
            {"factor_id": "S2_data_recovered", "status": "model_required", "value": None},
            {"factor_id": "S3_encounter_or_recovery", "status": "external_required", "value": None},
        ],
        "open_factors": list(REQUIRED_OPEN_FACTORS),
    }


def build_deep_time_archive_feasibility(repo_root: Path) -> Dict[str, Any]:
    """Build the deterministic feasibility proof boundary artifact."""

    capsule_design = _load_json(repo_root / SOURCE_CAPSULE_DESIGN)
    capsule_risk = _load_json(repo_root / SOURCE_CAPSULE_RISK)
    mission_probability = _load_json(repo_root / SOURCE_MISSION_PROBABILITY)
    capsule_architecture = _capsule_architecture(capsule_design)
    frontal_area_m2 = capsule_architecture["current_v1_proxy"]["frontal_area_m2"]
    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "public_scope": PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root),
        "source_records": _source_records(),
        "thesis": {
            "claim": "passive_archive_survivability_boundary_study",
            "plain_language": (
                "The artifact asks what must be true for a passive archive capsule to preserve recoverable "
                "information over about 10 Myr; it does not certify a mission or guarantee recovery."
            ),
            "hard_proof_target": "S2 passive survivability and recoverable information",
            "not_the_proof_target": "S3 black-hole capture or terminal targeting guarantee",
        },
        "success_levels": [
            {"id": "S0", "meaning": "deployment and escape with capsule intact", "status": "external_required"},
            {"id": "S1", "meaning": "early verification and OD during finite control window", "status": "external_required"},
            {"id": "S2", "meaning": "passive survivability and recoverable information over Myr horizons", "status": "repo_proxy_open"},
            {"id": "S3", "meaning": "terminal outcome class by R_int", "status": "probabilistic_only"},
        ],
        "target_corridor": _target_corridor(),
        "encounter_geometry": _encounter_geometry(),
        "architecture_and_control": _trajectory_modes(),
        "capsule_architecture": capsule_architecture,
        "dust_and_particles": _dust_environment(float(frontal_area_m2)),
        "media_readability": _media_readability(),
        "probability_decomposition": _probability_decomposition(capsule_risk, mission_probability),
        "validator_guards": {
            "forbidden_public_claims": list(FORBIDDEN_CLAIMS),
            "full_probability_must_remain_null": True,
            "case_a_must_not_be_controllable": True,
            "conditional_speed_requires_inbound_energy": True,
            "mm_cm_tail_must_remain_assumption_bound": True,
        },
        "blocked_claims": list(FORBIDDEN_CLAIMS),
        "external_evidence_gaps": [
            "dynamic Gaia BH1 worldline corridor",
            "whole-path dust/gas/radiation model",
            "full-stack hypervelocity ballistic-limit evidence",
            "material aging and radiation transport campaign",
            "end-to-end data medium damage-to-decode campaign",
            "TPS/SRM hot-vacuum qualification for Sun-Oberth mode",
            "independent review and proof-promotion record",
        ],
    }
    payload["rollup"] = {
        "target_direction_fixed": True,
        "dynamic_worldline_closed": False,
        "baseline_and_conditional_velocities_separated": True,
        "ten_myr_media_proof_available": False,
        "full_probability_closed": False,
        "qualification_complete": False,
        "blocked_claim_count": len(payload["blocked_claims"]),
        "source_record_count": len(payload["source_records"]),
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "target_corridor": payload["target_corridor"],
            "encounter_geometry": payload["encounter_geometry"],
            "architecture_and_control": payload["architecture_and_control"],
            "capsule_proxy": payload["capsule_architecture"]["current_v1_proxy"],
            "probability_decomposition": payload["probability_decomposition"],
            "rollup": payload["rollup"],
        }
    )
    return payload


def _validate_sources(repo_root: Path, payload: Mapping[str, Any], errors: List[str]) -> None:
    sources = payload.get("source_artifacts")
    if not isinstance(sources, list):
        errors.append("source_artifacts must be list")
        return
    by_path = {item.get("path"): item for item in sources if isinstance(item, Mapping)}
    for required in SOURCE_PATHS:
        entry = by_path.get(required)
        if not isinstance(entry, Mapping):
            errors.append(f"source_artifacts missing {required}")
            continue
        path = repo_root / required
        if not path.exists():
            errors.append(f"required source path missing on disk: {required}")
            continue
        if entry.get("sha256") != _sha256_file(path):
            errors.append(f"source_artifacts sha mismatch for {required}")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _validate_impact_table(payload: Mapping[str, Any], errors: List[str]) -> None:
    dust = payload.get("dust_and_particles")
    if not isinstance(dust, Mapping):
        errors.append("dust_and_particles must be object")
        return
    table = dust.get("impact_energy_table")
    if not isinstance(table, list) or len(table) < 5:
        errors.append("impact_energy_table must contain multiple size rows")
        return
    previous_mass = 0.0
    for index, row in enumerate(table):
        if not isinstance(row, Mapping):
            errors.append(f"impact_energy_table[{index}] must be object")
            continue
        mass = row.get("mass_kg")
        if not _is_number(mass) or float(mass) <= previous_mass:
            errors.append(f"impact_energy_table[{index}].mass_kg must increase by grain radius")
        previous_mass = float(mass) if _is_number(mass) else previous_mass
        energies = row.get("energy_j_by_velocity_km_s")
        if not isinstance(energies, Mapping):
            errors.append(f"impact_energy_table[{index}].energy_j_by_velocity_km_s must be object")
            continue
        values = [float(energies[key]) for key in ("23", "34", "45", "60") if key in energies and _is_number(energies[key])]
        if values != sorted(values) or len(values) != 4:
            errors.append(f"impact_energy_table[{index}] energy must increase across 23/34/45/60 km/s")
    shield = dust.get("shield_response_boundary")
    if not isinstance(shield, Mapping):
        errors.append("shield_response_boundary must be object")
        return
    if shield.get("hydrocode_extrapolation_required") is not True:
        errors.append("shield_response_boundary.hydrocode_extrapolation_required must be true")
    if float(shield.get("direct_test_velocity_max_km_s", 0.0)) >= max(shield.get("repo_velocity_bins_km_s", [0.0])):
        errors.append("direct test max velocity must remain below repo stress velocities")


def validate_deep_time_archive_feasibility(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    """Return validation errors for the feasibility proof boundary artifact."""

    errors: List[str] = []
    if not isinstance(payload, Mapping):
        return ["payload must be object"]
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if payload.get("generator") != GENERATOR:
        errors.append(f"generator must be {GENERATOR}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if repo_root is not None:
        _validate_sources(repo_root, payload, errors)

    source_records = payload.get("source_records")
    if not isinstance(source_records, list) or len(source_records) < 8:
        errors.append("source_records must contain at least 8 records")
    else:
        for index, source in enumerate(source_records):
            if not isinstance(source, Mapping):
                errors.append(f"source_records[{index}] must be object")
                continue
            if not isinstance(source.get("url"), str) or not source["url"].startswith("http"):
                errors.append(f"source_records[{index}].url must be http(s)")
            if source.get("grade") not in {"A", "B", "C", "D"}:
                errors.append(f"source_records[{index}].grade must be A/B/C/D")

    target = payload.get("target_corridor")
    if not isinstance(target, Mapping):
        errors.append("target_corridor must be object")
        target = {}
    if target.get("target_id") != "gaia-bh1-reference":
        errors.append("target_corridor.target_id must be gaia-bh1-reference")
    if "Gaia DR3 4373465352415301632" not in target.get("catalog_ids", []):
        errors.append("target_corridor.catalog_ids must include Gaia DR3 4373465352415301632")
    worldline = target.get("dynamic_target_worldline_corridor")
    if not isinstance(worldline, Mapping) or worldline.get("status") != "external_required":
        errors.append("dynamic_target_worldline_corridor.status must be external_required")

    architecture = payload.get("architecture_and_control")
    if not isinstance(architecture, Mapping):
        errors.append("architecture_and_control must be object")
        architecture = {}
    baseline = architecture.get("baseline_23_34_km_s")
    conditional = architecture.get("conditional_35_45_km_s")
    if not isinstance(baseline, list) or not baseline:
        errors.append("baseline_23_34_km_s must be non-empty")
    else:
        for row in baseline:
            if isinstance(row, Mapping) and row.get("inbound_vinf_m_s") != 0.0:
                errors.append("baseline rows must have inbound_vinf_m_s = 0")
    if not isinstance(conditional, list) or not conditional:
        errors.append("conditional_35_45_km_s must be non-empty")
    else:
        for row in conditional:
            if isinstance(row, Mapping) and float(row.get("inbound_vinf_m_s", 0.0)) <= 0.0:
                errors.append("conditional rows must include positive inbound_vinf_m_s")
            if isinstance(row, Mapping) and "conditional" not in str(row.get("claim_boundary", "")):
                errors.append("conditional rows must carry conditional claim_boundary")
    control = architecture.get("control_window")
    if not isinstance(control, Mapping) or control.get("no_myr_actuation_claim") is not True:
        errors.append("control_window.no_myr_actuation_claim must be true")

    encounter = payload.get("encounter_geometry")
    if not isinstance(encounter, Mapping):
        errors.append("encounter_geometry must be object")
    else:
        case_a = encounter.get("case_a_capture_rows")
        if not isinstance(case_a, list) or not case_a:
            errors.append("case_a_capture_rows must be non-empty")
        else:
            for row in case_a:
                if isinstance(row, Mapping) and "not operationally controllable" not in str(row.get("control_interpretation", "")):
                    errors.append("Case A rows must be not operationally controllable")
        case_b = encounter.get("case_b_encounter_rows")
        if not isinstance(case_b, list) or len(case_b) < 4:
            errors.append("case_b_encounter_rows must include 100/1000 AU examples")

    capsule = payload.get("capsule_architecture")
    if not isinstance(capsule, Mapping):
        errors.append("capsule_architecture must be object")
    else:
        current = capsule.get("current_v1_proxy")
        physical = capsule.get("physical_baseline_recommendation")
        if not isinstance(current, Mapping) or not _is_number(current.get("front_shield_areal_density_kg_m2")):
            errors.append("current_v1_proxy.front_shield_areal_density_kg_m2 must be numeric")
        if not isinstance(physical, Mapping) or physical.get("claim_boundary") is None:
            errors.append("physical_baseline_recommendation must carry claim_boundary")
        if capsule.get("qualification_status") != "external_required":
            errors.append("capsule_architecture.qualification_status must be external_required")

    _validate_impact_table(payload, errors)

    media = payload.get("media_readability")
    if not isinstance(media, Mapping):
        errors.append("media_readability must be object")
    else:
        if media.get("ten_myr_experimental_proof_available") is not False:
            errors.append("media_readability.ten_myr_experimental_proof_available must be false")
        if len(media.get("probability_chain", [])) < 3:
            errors.append("media_readability.probability_chain must separate physical/readable/decode")

    probability = payload.get("probability_decomposition")
    if not isinstance(probability, Mapping):
        errors.append("probability_decomposition must be object")
    else:
        if probability.get("full_P_archive_recoverable") is not None:
            errors.append("full_P_archive_recoverable must remain null")
        open_factors = set(probability.get("open_factors", []))
        if not set(REQUIRED_OPEN_FACTORS).issubset(open_factors):
            errors.append("probability_decomposition.open_factors missing required open factors")

    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list):
        errors.append("blocked_claims must be list")
    else:
        for claim in ("mission feasible", "flight-ready", "certified", "qualified", "guaranteed archive recovery"):
            if claim not in blocked:
                errors.append(f"blocked_claims must include {claim}")

    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
    else:
        for field in ("dynamic_worldline_closed", "ten_myr_media_proof_available", "full_probability_closed", "qualification_complete"):
            if rollup.get(field) is not False:
                errors.append(f"rollup.{field} must be false")
        if rollup.get("baseline_and_conditional_velocities_separated") is not True:
            errors.append("rollup.baseline_and_conditional_velocities_separated must be true")
    signature = payload.get("determinism_signature")
    if not isinstance(signature, str) or len(signature) != 64:
        errors.append("determinism_signature must be a sha256 hex string")
    return errors
