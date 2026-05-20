#!/usr/bin/env python3
"""Build the deterministic capsule survivability lab artifact."""

from __future__ import annotations

import argparse
import copy
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

try:
    from .script_io import render_json, write_json
except ImportError:
    from script_io import render_json, write_json

REPO_ROOT_FALLBACK = Path(__file__).resolve().parents[1]
if str(REPO_ROOT_FALLBACK) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FALLBACK))

from mission.capsule.design import load_default_capsule_design, summarize_mass_budget, validate_capsule_design
from mission.survivability.engine import UncertaintyBand, run_survivability_analysis


SCHEMA_VERSION = "capsule_survivability_lab.v1"
DEFAULT_OUTPUT = Path("artifacts/capsule_survivability_lab.v1.json")
DEFAULT_CAPSULE_DESIGN = Path("mission/capsule/capsule_design.v1.json")
DEFAULT_ENVIRONMENT_BRIEF = Path("docs/research/CAPSULE_ENVIRONMENT_DATA_BRIEF_v1.md")
DEFAULT_SPEC = Path("mission/CAPSULE_SURVIVABILITY_SPEC_v1.md")

C_MPS = 299_792_458.0
YEAR_S = 31_557_600.0
LIGHT_YEAR_M = C_MPS * YEAR_S

SOURCE_INDEX: Sequence[Mapping[str, Any]] = (
    {
        "source_id": "SRC-GENESIS-SRC-205-6KG",
        "label": "Genesis sample return capsule mass",
        "url": "https://ntrs.nasa.gov/api/citations/20050060761/downloads/20050060761.pdf?attachment=true",
        "trust_class": "B",
        "stable_value": "205.6 kg Genesis SRC mass",
        "applicability": "Heritage proxy for 206 kg archive capsule sizing; not a new mass qualification.",
    },
    {
        "source_id": "SRC-GENESIS-SRC-DIAMETER-1-52M",
        "label": "Genesis sample return capsule diameter",
        "url": "https://www.jpl.nasa.gov/news/press_kits/genesisreturn.pdf",
        "trust_class": "B",
        "stable_value": "152 cm blunt-nosed cone diameter",
        "applicability": "Heritage proxy converted to 1.81 m^2 frontal area.",
    },
    {
        "source_id": "SRC-LOCAL-H-DENSITY-SWACZYNA-2020",
        "label": "Local interstellar neutral hydrogen density",
        "url": "https://www.nasa.gov/solar-system/new-evidence-our-neighborhood-in-space-is-stuffed-with-hydrogen/",
        "trust_class": "A",
        "stable_value": "0.127 +/- 0.015 cm^-3",
        "applicability": "Local heliosphere/VLISM cruise reference only.",
    },
    {
        "source_id": "SRC-VOYAGER-PLASMA-GURNETT-2013",
        "label": "Voyager 1 interstellar plasma density",
        "url": "https://pubmed.ncbi.nlm.nih.gov/24030496/",
        "trust_class": "A",
        "stable_value": "order 0.08 cm^-3 electron/plasma density",
        "applicability": "Near-heliopause plasma reference; not a target-region black-hole plasma model.",
    },
    {
        "source_id": "SRC-ULYSSES-DUST-KRUEGER-2015",
        "label": "Ulysses local interstellar dust mass density",
        "url": "https://arxiv.org/abs/1510.06180",
        "trust_class": "A",
        "stable_value": "(2.1 +/- 0.6)e-24 kg/m^3 dust mass density",
        "applicability": "Local in-situ dust prior; large-particle tail remains assumption-bound.",
    },
    {
        "source_id": "SRC-HVIT-NASA-JSC",
        "label": "NASA JSC hypervelocity impact testing capability",
        "url": "https://hvit.jsc.nasa.gov/hypervelocity-testing/",
        "trust_class": "B",
        "stable_value": "100 micron to 10 mm aluminum projectiles, below 2 to over 7 km/s",
        "applicability": "Ground-test validation context; tens-of-km/s cruise impact claims are extrapolation.",
    },
    {
        "source_id": "SRC-GRAVITY-SGRA-DISTANCE-2019",
        "label": "Galactic-center Sgr A* distance anchor",
        "url": "https://arxiv.org/abs/1904.05721",
        "trust_class": "A",
        "stable_value": "R0 = 8178 pc with small statistical/systematic uncertainty",
        "applicability": "Precision context for the repo's rounded 26000 ly Galactic-center scenario.",
    },
    {
        "source_id": "SRC-ALPHA-CENTAURI-HUBBLE",
        "label": "Alpha Centauri distance anchor",
        "url": "https://science.nasa.gov/missions/hubble/hubbles-best-image-of-alpha-centauri-a-and-b/",
        "trust_class": "A",
        "stable_value": "about 4.3 light-years",
        "applicability": "Nearby-star scaling scenario.",
    },
    {
        "source_id": "SRC-NIAC-SOLAR-OBERTH-2025",
        "label": "Solar Oberth architecture context",
        "url": "https://ntrs.nasa.gov/api/citations/20250001946/downloads/NIAC_2022_PhI_Benkoski_Oberth.pdf",
        "trust_class": "B",
        "stable_value": "7-8 AU/yr SLS plus Jupiter gravity-assist context; >10 AU/yr concept-study target",
        "applicability": "Architecture context only; repo baseline keeps 23-45 km/s Sun-Oberth band.",
    },
    {
        "source_id": "SRC-PARKER-SOLAR-PROBE-NASA",
        "label": "Parker Solar Probe speed context",
        "url": "https://science.nasa.gov/mission/parker-solar-probe",
        "trust_class": "B",
        "stable_value": "approximately 430000 mph near closest approach",
        "applicability": "Solar-proximity speed precedent, not an outbound escape speed for this mission.",
    },
    {
        "source_id": "SRC-CAPSULE-DESIGN-V1",
        "label": "Local capsule design contract",
        "url": "mission/capsule/capsule_design.v1.json",
        "trust_class": "C",
        "stable_value": "206 kg C/C-SiC, Al-Li, B4C/Ta, titanium, inert-media stack",
        "applicability": "Deterministic v1 design allocation, not hardware qualification.",
    },
    {
        "source_id": "SRC-CAPSULE-DEEP-TIME-PRIOR-V1",
        "label": "Deep-time material hazard prior",
        "url": "mission/capsule/capsule_design.v1.json#survivability_model_inputs",
        "trust_class": "C",
        "stable_value": "2.2e-8 1/year nominal, 1e-9 to 2e-7 1/year uncertainty band",
        "applicability": "Assumption-bound passive-material prior for interaction and review.",
    },
    {
        "source_id": "SRC-CAPSULE-MODEL-COEFFICIENTS-V1",
        "label": "Reduced-order survivability coefficient set",
        "url": "mission/survivability/engine.py",
        "trust_class": "C",
        "stable_value": "v1 annual hazard coefficients exposed by the engine output",
        "applicability": "Model coefficients, not source-backed hardware survival data.",
    },
)

SOURCE_DATA: Sequence[Mapping[str, Any]] = (
    {"id": "julian_year", "value": YEAR_S, "units": "s", "source_ids": ["SRC-CAPSULE-DESIGN-V1"]},
    {"id": "light_year", "value": LIGHT_YEAR_M, "units": "m", "source_ids": ["SRC-CAPSULE-DESIGN-V1"]},
    {"id": "local_neutral_h_cm3", "value": 0.127, "sigma": 0.015, "units": "cm^-3", "source_ids": ["SRC-LOCAL-H-DENSITY-SWACZYNA-2020"]},
    {"id": "local_neutral_h_m3", "value": 127000.0, "sigma": 15000.0, "units": "m^-3", "source_ids": ["SRC-LOCAL-H-DENSITY-SWACZYNA-2020"]},
    {"id": "voyager_plasma_density_cm3", "value": 0.08, "units": "cm^-3", "source_ids": ["SRC-VOYAGER-PLASMA-GURNETT-2013"]},
    {"id": "voyager_plasma_density_m3", "value": 80000.0, "units": "m^-3", "source_ids": ["SRC-VOYAGER-PLASMA-GURNETT-2013"]},
    {"id": "ulysses_dust_density_kg_m3", "value": 2.1e-24, "sigma": 0.6e-24, "units": "kg/m^3", "source_ids": ["SRC-ULYSSES-DUST-KRUEGER-2015"]},
    {"id": "ulysses_gas_to_dust_ratio", "value": 193.0, "minus": 57.0, "plus": 85.0, "units": "ratio", "source_ids": ["SRC-ULYSSES-DUST-KRUEGER-2015"]},
    {"id": "hvit_min_projectile_diameter_m", "value": 1.0e-4, "units": "m", "source_ids": ["SRC-HVIT-NASA-JSC"]},
    {"id": "hvit_max_projectile_diameter_m", "value": 1.0e-2, "units": "m", "source_ids": ["SRC-HVIT-NASA-JSC"]},
    {"id": "hvit_direct_test_velocity_min_km_s", "value": 2.0, "units": "km/s", "source_ids": ["SRC-HVIT-NASA-JSC"]},
    {"id": "hvit_direct_test_velocity_max_km_s", "value": 7.0, "units": "km/s", "source_ids": ["SRC-HVIT-NASA-JSC"]},
    {"id": "alpha_centauri_distance_ly", "value": 4.37, "units": "ly", "source_ids": ["SRC-ALPHA-CENTAURI-HUBBLE"]},
    {"id": "repo_reference_black_hole_distance_ly", "value": 1560.0, "units": "ly", "source_ids": ["SRC-CAPSULE-DESIGN-V1"]},
    {"id": "repo_galactic_center_rounded_distance_ly", "value": 26000.0, "units": "ly", "source_ids": ["SRC-GRAVITY-SGRA-DISTANCE-2019"]},
    {"id": "parker_solar_probe_context_speed_mph", "value": 430000.0, "units": "mph", "source_ids": ["SRC-PARKER-SOLAR-PROBE-NASA"]},
)

TARGETS: Sequence[Mapping[str, Any]] = (
    {
        "id": "reference-black-hole",
        "label": "Reference black-hole candidate",
        "detail": "Default project-owned 1560 ly black-hole scenario; 45.32 km/s gives about 10.3 Myr.",
        "targetClass": "black_hole_scenario_proxy",
        "distanceLy": 1560.0,
        "sourceIds": ["SRC-CAPSULE-DESIGN-V1"],
        "environmentProfile": {
            "radiation": 1.15,
            "plasma_m3": 160000.0,
            "dust_scale": 1.4,
            "label": "outer black-hole cruise proxy",
        },
    },
    {
        "id": "alpha-centauri-scale",
        "label": "Alpha Centauri scale",
        "detail": "Nearby-star control scenario using a NASA/Hubble 4.3 ly anchor.",
        "targetClass": "nearby_star_scale",
        "distanceLy": 4.37,
        "sourceIds": ["SRC-ALPHA-CENTAURI-HUBBLE"],
        "environmentProfile": {
            "radiation": 1.0,
            "plasma_m3": 80000.0,
            "dust_scale": 1.0,
            "label": "local interstellar reference",
        },
    },
    {
        "id": "sgr-a-rounded",
        "label": "Sgr A* rounded",
        "detail": "Repo-compatible Galactic-center stress scenario at rounded 26000 ly.",
        "targetClass": "galactic_center_black_hole_proxy",
        "distanceLy": 26000.0,
        "sourceIds": ["SRC-GRAVITY-SGRA-DISTANCE-2019"],
        "environmentProfile": {
            "radiation": 1.4,
            "plasma_m3": 320000.0,
            "dust_scale": 1.8,
            "label": "galactic-center path stress proxy",
        },
    },
)

VELOCITY_PROFILES: Sequence[Mapping[str, Any]] = (
    {
        "id": "oberth-23",
        "label": "23.17 km/s",
        "detail": "Near-parabolic Sun-Oberth lower band.",
        "velocityKmS": 23.17,
        "sourceIds": ["SRC-NIAC-SOLAR-OBERTH-2025"],
    },
    {
        "id": "oberth-34",
        "label": "33.75 km/s",
        "detail": "Near-parabolic Sun-Oberth upper band.",
        "velocityKmS": 33.75,
        "sourceIds": ["SRC-NIAC-SOLAR-OBERTH-2025"],
    },
    {
        "id": "conditional-45",
        "label": "45.32 km/s",
        "detail": "Conditional inbound-energy Sun-Oberth band; default black-hole row is near 10 Myr.",
        "velocityKmS": 45.32,
        "sourceIds": ["SRC-NIAC-SOLAR-OBERTH-2025"],
    },
    {
        "id": "stress-60",
        "label": "60 km/s",
        "detail": "High-relative-speed dust stress row, not a validation claim.",
        "velocityKmS": 60.0,
        "sourceIds": ["SRC-HVIT-NASA-JSC"],
    },
    {
        "id": "concept-95",
        "label": "95 km/s",
        "detail": "Concept-only speed stress to expose sensitivity, not current architecture baseline.",
        "velocityKmS": 95.0,
        "sourceIds": ["SRC-NIAC-SOLAR-OBERTH-2025", "SRC-PARKER-SOLAR-PROBE-NASA"],
    },
)

TIME_HORIZONS: Sequence[Mapping[str, Any]] = (
    {
        "id": "ballistic-arrival",
        "label": "Ballistic arrival",
        "detail": "Computed from selected target distance and selected cruise velocity.",
        "mode": "computed_time_of_flight",
    },
    {
        "id": "one-myr",
        "label": "1 Myr",
        "detail": "Fixed deep-time design horizon.",
        "mode": "fixed_years",
        "years": 1_000_000.0,
    },
    {
        "id": "ten-myr",
        "label": "10 Myr",
        "detail": "Fixed horizon matching the core project narrative scale.",
        "mode": "fixed_years",
        "years": 10_000_000.0,
    },
    {
        "id": "hundred-myr",
        "label": "100 Myr",
        "detail": "Extreme persistence stress horizon.",
        "mode": "fixed_years",
        "years": 100_000_000.0,
    },
)

CAPSULE_PROFILES: Sequence[Mapping[str, Any]] = (
    {
        "id": "baseline-stack",
        "label": "206 kg C/C-SiC archive stack",
        "detail": "Default capsule_design.v1 material stack and deep-time priors.",
        "shieldMultiplier": 1.0,
        "mediaMargin": None,
        "materialMu": None,
        "orientationFactor": 0.88,
    },
    {
        "id": "reinforced-media",
        "label": "Reinforced media sensitivity stack",
        "detail": "Same 206 kg shell with more conservative attitude and media-reserve sensitivity priors.",
        "shieldMultiplier": 1.14,
        "mediaMargin": 0.91,
        "materialMu": 1.4e-8,
        "orientationFactor": 0.80,
    },
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _source_artifacts(repo_root: Path, paths: Sequence[Path]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for path in paths:
        full = repo_root / path
        digest = hashlib.sha256(full.read_bytes()).hexdigest()
        out.append({"path": str(path), "sha256": digest})
    return out


def _option(item: Mapping[str, Any]) -> Dict[str, str]:
    return {
        "id": str(item["id"]),
        "label": str(item["label"]),
        "detail": str(item["detail"]),
    }


def _years_for(target: Mapping[str, Any], velocity: Mapping[str, Any], horizon: Mapping[str, Any]) -> float:
    if horizon["mode"] == "computed_time_of_flight":
        distance_m = float(target["distanceLy"]) * LIGHT_YEAR_M
        return distance_m / (float(velocity["velocityKmS"]) * 1000.0) / YEAR_S
    return float(horizon["years"])


def _value_entry(value: float, *, units: str, provenance: str, source_ids: Sequence[str], note: str) -> Dict[str, Any]:
    return {
        "value": value,
        "units": units,
        "provenance": provenance,
        "source_ids": list(source_ids),
        "note": note,
    }


def _profiled_design(base_design: Mapping[str, Any], profile: Mapping[str, Any]) -> Dict[str, Any]:
    design = copy.deepcopy(dict(base_design))
    inputs = design["survivability_model_inputs"]
    shield = copy.deepcopy(inputs["shield_areal_density_kg_m2"])
    shield["value"] = float(shield["value"]) * float(profile["shieldMultiplier"])
    shield["source_ids"] = sorted(set(shield.get("source_ids", []) + ["SRC-CAPSULE-DESIGN-V1"]))
    shield["note"] = f"{shield.get('note', '')} Profile multiplier {profile['shieldMultiplier']} applied for sensitivity row."
    inputs["shield_areal_density_kg_m2"] = shield

    if profile["mediaMargin"] is not None:
        media = copy.deepcopy(inputs["data_media_survival_margin"])
        media["value"] = float(profile["mediaMargin"])
        media["source_ids"] = sorted(set(media.get("source_ids", []) + ["SRC-CAPSULE-DESIGN-V1"]))
        media["note"] = "Profile sensitivity override for redundant inert media reserve."
        inputs["data_media_survival_margin"] = media
    if profile["materialMu"] is not None:
        material = copy.deepcopy(inputs["material_degradation_mu_1_per_year"])
        material["value"] = float(profile["materialMu"])
        material["source_ids"] = sorted(set(material.get("source_ids", []) + ["SRC-CAPSULE-DEEP-TIME-PRIOR-V1"]))
        material["note"] = "Profile sensitivity override inside the declared deep-time prior family."
        inputs["material_degradation_mu_1_per_year"] = material

    return design


def _target_payload(target: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "radiation_reference_w_m2": _value_entry(
            1.0,
            units="normalized proxy",
            provenance="proxy",
            source_ids=["SRC-CAPSULE-MODEL-COEFFICIENTS-V1"],
            note="Normalized reduced-order radiation reference; GCR model selection remains a source-data hook.",
        ),
        "plasma_reference_m3": _value_entry(
            80000.0,
            units="1/m^3",
            provenance="validated_source",
            source_ids=["SRC-VOYAGER-PLASMA-GURNETT-2013"],
            note="Voyager-order local interstellar plasma reference.",
        ),
        "dust_reference_scale": _value_entry(
            1.0,
            units="normalized dust scale",
            provenance="proxy",
            source_ids=["SRC-ULYSSES-DUST-KRUEGER-2015"],
            note="Normalized to the Ulysses local interstellar dust mass-density prior.",
        ),
    }


def _environment_payload(target: Mapping[str, Any]) -> Dict[str, Any]:
    profile = target["environmentProfile"]
    return {
        "radiative_flux_w_m2": _value_entry(
            float(profile["radiation"]),
            units="normalized proxy",
            provenance="proxy",
            source_ids=["SRC-CAPSULE-MODEL-COEFFICIENTS-V1"],
            note=str(profile["label"]),
        ),
        "plasma_density_proxy_m3": _value_entry(
            float(profile["plasma_m3"]),
            units="1/m^3",
            provenance="proxy",
            source_ids=["SRC-VOYAGER-PLASMA-GURNETT-2013"],
            note=str(profile["label"]),
        ),
        "dust_flux_scale": _value_entry(
            float(profile["dust_scale"]),
            units="normalized dust scale",
            provenance="proxy",
            source_ids=["SRC-ULYSSES-DUST-KRUEGER-2015"],
            note=str(profile["label"]),
        ),
    }


def _trajectory_payload(velocity: Mapping[str, Any], profile: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "encounter_velocity_km_s": _value_entry(
            float(velocity["velocityKmS"]),
            units="km/s",
            provenance="proxy",
            source_ids=list(velocity["sourceIds"]),
            note=str(velocity["detail"]),
        ),
        "exposure_fraction": _value_entry(
            1.0,
            units="fraction",
            provenance="assumption",
            source_ids=["SRC-CAPSULE-MODEL-COEFFICIENTS-V1"],
            note="Deep-time passive exposure integrates over the selected horizon.",
        ),
        "shield_orientation_factor": _value_entry(
            float(profile["orientationFactor"]),
            units="factor",
            provenance="assumption",
            source_ids=["SRC-CAPSULE-DESIGN-V1"],
            note="Assumed fraction of nominal frontal dust hazard after attitude and shield orientation control.",
        ),
    }


def _uncertainty_bands(
    design: Mapping[str, Any],
    target: Mapping[str, Any],
    velocity: Mapping[str, Any],
) -> List[UncertaintyBand]:
    inputs = design["survivability_model_inputs"]
    material_nominal = float(inputs["material_degradation_mu_1_per_year"]["value"])
    media_nominal = float(inputs["data_media_survival_margin"]["value"])
    shield_nominal = float(inputs["shield_areal_density_kg_m2"]["value"])
    dust = float(target["environmentProfile"]["dust_scale"])
    speed = float(velocity["velocityKmS"])
    return [
        UncertaintyBand(
            name="deep_time_material_hazard",
            target="capsule.material_degradation_mu_1_per_year",
            low=max(1.0e-10, material_nominal * 0.25),
            high=max(2.0e-10, material_nominal * 8.0),
            provenance="assumption",
        ),
        UncertaintyBand(
            name="archive_media_margin",
            target="capsule.data_media_survival_margin",
            low=max(0.5, media_nominal - 0.08),
            high=min(0.99, media_nominal + 0.06),
            provenance="assumption",
        ),
        UncertaintyBand(
            name="shield_areal_density",
            target="capsule.shield_areal_density_kg_m2",
            low=max(1.0, shield_nominal * 0.8),
            high=shield_nominal * 1.15,
            provenance="assumption",
        ),
        UncertaintyBand(
            name="dust_environment_scale",
            target="environment.dust_flux_scale",
            low=max(0.2, dust * 0.55),
            high=max(0.3, dust * 2.4),
            provenance="proxy",
        ),
        UncertaintyBand(
            name="velocity_sensitivity",
            target="trajectory.encounter_velocity_km_s",
            low=max(1.0, speed * 0.9),
            high=speed * 1.1,
            provenance="proxy",
        ),
    ]


def _top_drivers(analysis: Mapping[str, Any]) -> List[str]:
    components: List[tuple[str, float]] = []
    hazards = analysis["nominal"]["hazard_components"]
    for group, payload in hazards.items():
        for name, value in payload.items():
            components.append((f"{group} {name}", float(value)))
    components.sort(key=lambda item: item[1], reverse=True)
    return [name for name, _ in components[:3]]


def _status_from_probability(value: float) -> str:
    if value >= 0.5:
        return "PASS"
    if value >= 0.1:
        return "WATCH"
    return "FAIL"


def _outcome_band(total_band: Mapping[str, float]) -> str:
    if float(total_band["p05"]) >= 0.5:
        return "nominal"
    if float(total_band["p50"]) >= 0.1:
        return "stressed"
    return "critical"


def _verdict(band: str, years: float, target: Mapping[str, Any]) -> str:
    if band == "nominal":
        return f"Capsule-only survival stays nominal for {target['label']} over this selected horizon."
    if band == "stressed":
        return f"Capsule-only survival remains possible, but assumptions dominate the {years:,.0f} year row."
    return f"Capsule-only survival is critical under the selected {target['label']} horizon and priors."


def _build_row(
    *,
    base_design: Mapping[str, Any],
    target: Mapping[str, Any],
    velocity: Mapping[str, Any],
    horizon: Mapping[str, Any],
    profile: Mapping[str, Any],
    samples: int,
    seed: int,
) -> Dict[str, Any]:
    design = _profiled_design(base_design, profile)
    years = _years_for(target, velocity, horizon)
    trajectory = _trajectory_payload(velocity, profile)
    environment = _environment_payload(target)
    analysis = run_survivability_analysis(
        capsule_design=design,
        target=_target_payload(target),
        trajectory=trajectory,
        flight_years=years,
        environment=environment,
        uncertainty_bands=_uncertainty_bands(design, target, velocity),
        samples=samples,
        seed=seed,
    )

    total_band = analysis["scenario_bands"]["total_capsule_survival"]
    media_band = analysis["scenario_bands"]["media_integrity"]
    structure_band = analysis["scenario_bands"]["structure_survival"]
    band = _outcome_band(total_band)
    radiation_ratio = float(analysis["nominal"]["normalized_exposures"]["radiation_ratio"])
    shield_density = float(design["survivability_model_inputs"]["shield_areal_density_kg_m2"]["value"])
    row_id = f"cap-row-{target['id']}-{horizon['id']}-{velocity['id']}-{profile['id']}"

    row = {
        "rowId": row_id,
        "targetId": target["id"],
        "timeId": horizon["id"],
        "velocityId": velocity["id"],
        "capsuleId": profile["id"],
        "distanceLy": _round(float(target["distanceLy"]), 6),
        "velocityKmS": _round(float(velocity["velocityKmS"]), 6),
        "flightYears": _round(years, 6),
        "output": {
            "survivalProbability": _round(float(total_band["p50"])),
            "survivalP05": _round(float(total_band["p05"])),
            "survivalP95": _round(float(total_band["p95"])),
            "structureProbability": _round(float(structure_band["p50"])),
            "dataIntegrityProbability": _round(float(media_band["p50"])),
            "shieldMargin": _round(shield_density / 32.0),
            "thermalMargin": _round(1.0 / max(0.1, radiation_ratio)),
            "outcomeBand": band,
            "verdict": _verdict(band, years, target),
            "confidence": "Medium; source-backed environment anchors plus explicit assumption-bound model coefficients.",
        },
        "stages": [
            {
                "stage": "S0",
                "label": "Target",
                "status": "PASS" if target["id"] != "sgr-a-rounded" else "WATCH",
                "summary": f"{target['label']} at {float(target['distanceLy']):,.2f} ly with {target['environmentProfile']['label']}.",
            },
            {
                "stage": "S1",
                "label": "Flight horizon",
                "status": "FAIL" if years >= 100_000_000.0 else ("WATCH" if years >= 10_000_000.0 or float(velocity["velocityKmS"]) >= 60.0 else "PASS"),
                "summary": f"{years:,.0f} years at {float(velocity['velocityKmS']):.2f} km/s.",
            },
            {
                "stage": "S2",
                "label": "Shell",
                "status": _status_from_probability(float(structure_band["p05"])),
                "summary": f"Structure p05={float(structure_band['p05']):.3f}, p50={float(structure_band['p50']):.3f}.",
            },
            {
                "stage": "S3",
                "label": "Data",
                "status": _status_from_probability(float(media_band["p05"])),
                "summary": f"Media p05={float(media_band['p05']):.3f}, p50={float(media_band['p50']):.3f}.",
            },
        ],
        "driverLabels": _top_drivers(analysis),
        "scenarioBands": analysis["scenario_bands"],
        "assumptionSummary": analysis["provenance_summary"]["counts"],
        "uncertaintyDrivers": [
            {
                "name": band["name"],
                "target": band["target"],
                "provenance": band["provenance"],
            }
            for band in analysis["uncertainty_model"]
        ],
    }
    row["artifactDigest"] = _sha256_text(render_json(row, sort_keys=True))[:16]
    return row


def validate_capsule_survivability_artifact(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")

    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) < 100:
        errors.append("rows must contain at least 100 deterministic scenario rows")
        rows = []
    source_index = payload.get("source_index")
    if not isinstance(source_index, list) or len(source_index) < 10:
        errors.append("source_index must contain at least 10 entries")
    else:
        for source in source_index:
            if not isinstance(source, Mapping):
                errors.append("source_index entries must be objects")
                continue
            if not source.get("source_id") or not source.get("url") or source.get("trust_class") not in {"A", "B", "C", "D"}:
                errors.append(f"invalid source entry: {source!r}")

    controls = payload.get("controls")
    if not isinstance(controls, Mapping):
        errors.append("controls must be object")
        controls = {}
    valid_targets = {item.get("id") for item in controls.get("targets", []) if isinstance(item, Mapping)}
    valid_times = {item.get("id") for item in controls.get("timeHorizons", []) if isinstance(item, Mapping)}
    valid_velocities = {item.get("id") for item in controls.get("velocityBands", []) if isinstance(item, Mapping)}
    valid_capsules = {item.get("id") for item in controls.get("capsuleProfiles", []) if isinstance(item, Mapping)}

    default_row_seen = False
    row_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            errors.append("row entries must be objects")
            continue
        row_id = row.get("rowId")
        if not isinstance(row_id, str) or not row_id:
            errors.append("row.rowId must be non-empty string")
        elif row_id in row_ids:
            errors.append(f"duplicate rowId: {row_id}")
        else:
            row_ids.add(row_id)
        if row.get("targetId") not in valid_targets:
            errors.append(f"row {row_id} references unknown targetId")
        if row.get("timeId") not in valid_times:
            errors.append(f"row {row_id} references unknown timeId")
        if row.get("velocityId") not in valid_velocities:
            errors.append(f"row {row_id} references unknown velocityId")
        if row.get("capsuleId") not in valid_capsules:
            errors.append(f"row {row_id} references unknown capsuleId")
        output = row.get("output")
        if not isinstance(output, Mapping):
            errors.append(f"row {row_id} output must be object")
            continue
        for key in ("survivalProbability", "dataIntegrityProbability", "structureProbability"):
            value = output.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 <= float(value) <= 1.0:
                errors.append(f"row {row_id} output.{key} must be a probability")
        if output.get("outcomeBand") not in {"nominal", "stressed", "critical"}:
            errors.append(f"row {row_id} output.outcomeBand invalid")
        if (
            row.get("targetId") == "reference-black-hole"
            and row.get("velocityId") == "conditional-45"
            and row.get("timeId") == "ballistic-arrival"
            and row.get("capsuleId") == "baseline-stack"
        ):
            default_row_seen = True
            years = float(row.get("flightYears", 0.0))
            if not 10_000_000.0 <= years <= 11_000_000.0:
                errors.append(f"default black-hole row should be near 10 Myr, got {years}")
    if not default_row_seen:
        errors.append("missing default reference-black-hole/conditional-45/ballistic-arrival/baseline-stack row")

    return errors


def build_capsule_survivability_artifact(*, repo_root: Path, output_path: Path, samples: int, seed: int) -> Dict[str, Any]:
    base_design = load_default_capsule_design()
    design_errors = validate_capsule_design(base_design)
    if design_errors:
        return {"status": "FAIL", "errors": design_errors, "row_count": 0, "artifact_sha256": None}

    rows: List[Dict[str, Any]] = []
    for target in TARGETS:
        for horizon in TIME_HORIZONS:
            for velocity in VELOCITY_PROFILES:
                for profile in CAPSULE_PROFILES:
                    rows.append(
                        _build_row(
                            base_design=base_design,
                            target=target,
                            velocity=velocity,
                            horizon=horizon,
                            profile=profile,
                            samples=samples,
                            seed=seed,
                        )
                    )
    rows.sort(
        key=lambda row: (
            0
            if row["targetId"] == "reference-black-hole"
            and row["timeId"] == "ballistic-arrival"
            and row["velocityId"] == "conditional-45"
            and row["capsuleId"] == "baseline-stack"
            else 1,
            str(row["rowId"]),
        )
    )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generator": "scripts/build_capsule_survivability_artifact.py",
        "engine": {
            "samples_per_row": samples,
            "seed": seed,
            "formula_policy": "reduced_order_hazard_integration",
        },
        "public_scope": "artifact_backed_capsule_interaction",
        "non_certification_notice": True,
        "source_paths": {
            "capsuleDesign": str(DEFAULT_CAPSULE_DESIGN),
            "environmentBrief": str(DEFAULT_ENVIRONMENT_BRIEF),
            "missionSpec": str(DEFAULT_SPEC),
        },
        "source_artifacts": _source_artifacts(
            repo_root,
            [DEFAULT_CAPSULE_DESIGN, DEFAULT_ENVIRONMENT_BRIEF, DEFAULT_SPEC],
        ),
        "source_index": list(SOURCE_INDEX),
        "source_data": list(SOURCE_DATA),
        "capsule_design": {
            "design_id": base_design["design_id"],
            "schema_version": base_design["schema_version"],
            "mass_budget": summarize_mass_budget(base_design),
            "layers": base_design["layers"],
            "materials": base_design["materials"],
            "survivability_model_inputs": base_design["survivability_model_inputs"],
            "survivability_uncertainty_bounds": base_design["survivability_uncertainty_bounds"],
        },
        "controls": {
            "targets": [_option(target) for target in TARGETS],
            "timeHorizons": [_option(horizon) for horizon in TIME_HORIZONS],
            "velocityBands": [_option(velocity) for velocity in VELOCITY_PROFILES],
            "capsuleProfiles": [_option(profile) for profile in CAPSULE_PROFILES],
        },
        "target_metadata": [
            {
                "id": target["id"],
                "targetClass": target["targetClass"],
                "distanceLy": target["distanceLy"],
                "sourceIds": target["sourceIds"],
                "environmentProfile": target["environmentProfile"],
            }
            for target in TARGETS
        ],
        "velocity_metadata": [
            {
                "id": velocity["id"],
                "velocityKmS": velocity["velocityKmS"],
                "fractionOfC": float(velocity["velocityKmS"]) * 1000.0 / C_MPS,
                "sourceIds": velocity["sourceIds"],
            }
            for velocity in VELOCITY_PROFILES
        ],
        "time_horizon_metadata": [
            {
                "id": horizon["id"],
                "mode": horizon["mode"],
                "years": horizon.get("years"),
            }
            for horizon in TIME_HORIZONS
        ],
        "model_coefficients": run_survivability_analysis(
            capsule_design=base_design,
            target=_target_payload(TARGETS[0]),
            trajectory=_trajectory_payload(VELOCITY_PROFILES[0], CAPSULE_PROFILES[0]),
            flight_years=1.0,
            environment=_environment_payload(TARGETS[0]),
            uncertainty_bands=[],
            samples=1,
            seed=seed,
        )["model_coefficients"],
        "rows": rows,
    }

    errors = validate_capsule_survivability_artifact(payload)
    if errors:
        return {"status": "FAIL", "errors": errors, "row_count": len(rows), "artifact_sha256": None}

    output_abs = repo_root / output_path
    write_json(output_abs, payload)
    artifact_sha256 = hashlib.sha256(output_abs.read_bytes()).hexdigest()
    return {
        "status": "PASS",
        "errors": [],
        "row_count": len(rows),
        "artifact_sha256": artifact_sha256,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--seed", type=int, default=9001)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    result = build_capsule_survivability_artifact(
        repo_root=repo_root,
        output_path=Path(args.output),
        samples=args.samples,
        seed=args.seed,
    )
    if args.format == "json":
        print(render_json(result))
    else:
        print(f"{result['status']}: capsule survivability artifact")
        print(f"- row_count: {result['row_count']}")
        if result["artifact_sha256"]:
            print(f"- artifact_sha256: {result['artifact_sha256']}")
        for error in result["errors"]:
            print(f"  - {error}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
