"""Deterministic Capsule Risk Budget v2 helpers.

This module deliberately summarizes Monte Carlo draws into quantiles and driver
budgets. Raw samples are not persisted in the public artifact because the
browser contract needs stable, reviewable evidence, not a large runtime dataset.
"""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any, Dict, Iterable, List, Mapping, Sequence


SCHEMA_VERSION = "capsule_risk_budget.v1"
SOURCE_ARTIFACT_REF = "artifacts/capsule_survivability_lab.v1.json"
DEFAULT_ROW_ID = "cap-row-reference-black-hole-ballistic-arrival-conditional-45-baseline-stack"
DEFAULT_SAMPLE_COUNT = 4096
MINIMUM_SAMPLE_COUNT = 1024

REQUIRED_DIMENSION_IDS = {
    "dust",
    "radiation",
    "plasma",
    "media_margin",
    "material_degradation",
    "shield_areal_density",
    "exposure_fraction",
    "velocity",
    "target_distance",
    "time_horizon",
}

REQUIRED_ATTACK_MODE_IDS = {
    "nominal",
    "skeptical",
    "severe_dust",
    "media_decay",
    "radiation_stress",
}

UNCERTAINTY_DIMENSIONS: Sequence[Mapping[str, Any]] = (
    {
        "id": "dust",
        "label": "Interstellar dust density and large-particle tail",
        "targets": ["environment.dust_flux_scale", "trajectory.encounter_velocity_km_s"],
        "provenance": "proxy",
        "distribution": "deterministic_lognormal_proxy",
        "source_ids": ["SRC-ULYSSES-DUST-KRUEGER-2015"],
    },
    {
        "id": "radiation",
        "label": "Integrated radiative dose proxy",
        "targets": ["environment.radiative_flux_w_m2"],
        "provenance": "proxy",
        "distribution": "deterministic_lognormal_proxy",
        "source_ids": ["SRC-CAPSULE-MODEL-COEFFICIENTS-V1"],
    },
    {
        "id": "plasma",
        "label": "Plasma density and charging stress proxy",
        "targets": ["environment.plasma_density_proxy_m3"],
        "provenance": "proxy",
        "distribution": "deterministic_lognormal_proxy",
        "source_ids": ["SRC-VOYAGER-PLASMA-GURNETT-2013"],
    },
    {
        "id": "media_margin",
        "label": "Archive media persistence margin",
        "targets": ["capsule.data_media_survival_margin"],
        "provenance": "assumption",
        "distribution": "deterministic_uniform_proxy",
        "source_ids": ["SRC-CAPSULE-DEEP-TIME-PRIOR-V1"],
    },
    {
        "id": "material_degradation",
        "label": "Deep-time passive material degradation",
        "targets": ["capsule.material_degradation_mu_1_per_year"],
        "provenance": "assumption",
        "distribution": "deterministic_lognormal_proxy",
        "source_ids": ["SRC-CAPSULE-DEEP-TIME-PRIOR-V1"],
    },
    {
        "id": "shield_areal_density",
        "label": "Shield areal-density effectiveness",
        "targets": ["capsule.shield_areal_density_kg_m2"],
        "provenance": "assumption",
        "distribution": "deterministic_uniform_proxy",
        "source_ids": ["SRC-CAPSULE-DESIGN-V1"],
    },
    {
        "id": "exposure_fraction",
        "label": "Fraction of flight under damaging exposure",
        "targets": ["trajectory.exposure_fraction"],
        "provenance": "assumption",
        "distribution": "deterministic_uniform_proxy",
        "source_ids": ["SRC-CAPSULE-MODEL-COEFFICIENTS-V1"],
    },
    {
        "id": "velocity",
        "label": "Encounter velocity stress",
        "targets": ["trajectory.encounter_velocity_km_s"],
        "provenance": "proxy",
        "distribution": "deterministic_uniform_proxy",
        "source_ids": ["SRC-NIAC-SOLAR-OBERTH-2025", "SRC-HVIT-NASA-JSC"],
    },
    {
        "id": "target_distance",
        "label": "Target distance scaling",
        "targets": ["target.distance_ly"],
        "provenance": "proxy",
        "distribution": "deterministic_uniform_proxy",
        "source_ids": ["SRC-CAPSULE-DESIGN-V1"],
    },
    {
        "id": "time_horizon",
        "label": "Selected flight horizon",
        "targets": ["row.flightYears"],
        "provenance": "proxy",
        "distribution": "deterministic_uniform_proxy",
        "source_ids": ["SRC-CAPSULE-DESIGN-V1"],
    },
)

ATTACK_MODES: Sequence[Mapping[str, Any]] = (
    {
        "id": "nominal",
        "label": "Nominal evidence",
        "description": "Uses the committed Capsule Lab v1 row without additional stress multipliers.",
        "multipliers": {
            "dust": 1.0,
            "radiation": 1.0,
            "plasma": 1.0,
            "media_margin": 1.0,
            "material_degradation": 1.0,
            "shield_areal_density": 1.0,
            "exposure_fraction": 1.0,
            "velocity": 1.0,
            "target_distance": 1.0,
            "time_horizon": 1.0,
        },
    },
    {
        "id": "skeptical",
        "label": "Skeptical evidence",
        "description": "Broad conservative posture across assumption-bound material, media, and environment terms.",
        "multipliers": {
            "dust": 1.45,
            "radiation": 1.25,
            "plasma": 1.2,
            "media_margin": 1.35,
            "material_degradation": 1.8,
            "shield_areal_density": 0.86,
            "exposure_fraction": 1.1,
            "velocity": 1.04,
            "target_distance": 1.0,
            "time_horizon": 1.0,
        },
    },
    {
        "id": "severe_dust",
        "label": "Severe dust",
        "description": "Stress case for interstellar dust density, velocity coupling, and shielding extrapolation.",
        "multipliers": {
            "dust": 3.0,
            "radiation": 1.0,
            "plasma": 1.05,
            "media_margin": 1.0,
            "material_degradation": 1.15,
            "shield_areal_density": 0.72,
            "exposure_fraction": 1.0,
            "velocity": 1.18,
            "target_distance": 1.0,
            "time_horizon": 1.0,
        },
    },
    {
        "id": "media_decay",
        "label": "Media decay",
        "description": "Stress case where archive-media persistence dominates data-integrity loss.",
        "multipliers": {
            "dust": 1.0,
            "radiation": 1.15,
            "plasma": 1.0,
            "media_margin": 2.4,
            "material_degradation": 1.9,
            "shield_areal_density": 1.0,
            "exposure_fraction": 1.05,
            "velocity": 1.0,
            "target_distance": 1.0,
            "time_horizon": 1.0,
        },
    },
    {
        "id": "radiation_stress",
        "label": "Radiation stress",
        "description": "Stress case for radiative dose and plasma-coupled electronics/media damage.",
        "multipliers": {
            "dust": 1.0,
            "radiation": 3.0,
            "plasma": 1.55,
            "media_margin": 1.18,
            "material_degradation": 1.2,
            "shield_areal_density": 0.92,
            "exposure_fraction": 1.0,
            "velocity": 1.0,
            "target_distance": 1.0,
            "time_horizon": 1.0,
        },
    },
)

DRIVER_WEIGHTS = {
    "material_degradation": 0.34,
    "media_margin": 0.22,
    "dust": 0.18,
    "radiation": 0.10,
    "plasma": 0.07,
    "shield_areal_density": 0.06,
    "exposure_fraction": 0.03,
}

SOURCE_POLICY = {
    "classes": [
        {
            "class": "source_backed",
            "meaning": "Direct source or close reference environment supports the value.",
            "claim_boundary": "May anchor a local model input; does not certify a deep-time mission row.",
        },
        {
            "class": "proxy",
            "meaning": "A source-backed or heritage value is used with declared applicability limits.",
            "claim_boundary": "Must remain labeled as extrapolation, never as direct measurement of the selected mission.",
        },
        {
            "class": "assumption_bound",
            "meaning": "A bounded prior or reduced-order coefficient is used because direct evidence is absent.",
            "claim_boundary": "Requires visible evidence gaps and cannot support certification language.",
        },
        {
            "class": "mixed",
            "meaning": "The row or mode combines multiple evidence classes.",
            "claim_boundary": "Must expose the mix instead of collapsing it into a single confidence badge.",
        },
    ],
    "rules": [
        "Realistic rows must not depend on speculative or trust-D inputs.",
        "Proxy values must not be renamed as measured values.",
        "Assumption-bound values must remain visible in row evidence and blocking-claim fields.",
        "Rows with missing evidence must carry a blocking evidence gap instead of a stronger public claim.",
    ],
}

FAILURE_MODES = [
    {
        "id": "dust_impact_pressure",
        "label": "Dust and large-particle impact pressure",
        "model_status": "partially_modeled",
        "evidence_class": "proxy",
        "description": "Reduced-order dust-tail pressure derived from source-backed environment proxies and shield assumptions.",
    },
    {
        "id": "radiation_dose_pressure",
        "label": "Radiation dose pressure",
        "model_status": "partially_modeled",
        "evidence_class": "proxy",
        "description": "Dose stress hook over archive media and materials; not full radiation transport.",
    },
    {
        "id": "plasma_charging_pressure",
        "label": "Plasma and charging pressure",
        "model_status": "partially_modeled",
        "evidence_class": "proxy",
        "description": "Plasma density and charging stress are sampled as proxy drivers, not as validated multiphysics transport.",
    },
    {
        "id": "material_degradation_pressure",
        "label": "Deep-time material degradation",
        "model_status": "partially_modeled",
        "evidence_class": "assumption_bound",
        "description": "Long-horizon material persistence is represented by bounded priors pending qualification evidence.",
    },
    {
        "id": "media_integrity_loss",
        "label": "Archive media integrity loss",
        "model_status": "partially_modeled",
        "evidence_class": "assumption_bound",
        "description": "Media-retention margin and redundancy are sampled, but bit-level recoverability is not proven.",
    },
    {
        "id": "target_horizon_mismatch",
        "label": "Target and horizon mismatch",
        "model_status": "modeled_contract",
        "evidence_class": "mixed",
        "description": "Rows expose selected target and flight horizon so reviewers can reject hidden defaults.",
    },
    {
        "id": "full_multiphysics_transport",
        "label": "Full multiphysics transport",
        "model_status": "unmodeled",
        "evidence_class": "external_required",
        "description": "Radiation, plasma, thermal, and material coupling remain outside the v1 artifact.",
    },
    {
        "id": "stack_ballistic_limit_validation",
        "label": "Stack-level ballistic-limit validation",
        "model_status": "unmodeled",
        "evidence_class": "external_required",
        "description": "The artifact has no coupon or stack test data over the full velocity and angle envelope.",
    },
    {
        "id": "bit_recovery_validation",
        "label": "Bit-level archive recovery validation",
        "model_status": "unmodeled",
        "evidence_class": "external_required",
        "description": "ECC, physical media readout, and post-arrival decoding are not empirically validated here.",
    },
    {
        "id": "launch_and_operations_readiness",
        "label": "Launch and operations readiness",
        "model_status": "unmodeled",
        "evidence_class": "external_required",
        "description": "Launch provider, legal, regulatory, navigation, telemetry, and operations readiness are out of scope.",
    },
]

QUALIFICATION_ROADMAP = [
    {
        "id": "dust-tail-measurement-upgrade",
        "track": "Dust environment",
        "status": "external_required",
        "closes_failure_modes": ["dust_impact_pressure"],
        "acceptance_criteria": "Source-backed dust density and large-particle tail bounds for selected target corridors.",
    },
    {
        "id": "ballistic-limit-stack-test",
        "track": "Shield stack",
        "status": "external_required",
        "closes_failure_modes": ["dust_impact_pressure", "stack_ballistic_limit_validation"],
        "acceptance_criteria": "Coupon and stack impact evidence over relevant velocity, mass, and angle regimes.",
    },
    {
        "id": "radiation-transport-campaign",
        "track": "Radiation and plasma",
        "status": "external_required",
        "closes_failure_modes": ["radiation_dose_pressure", "plasma_charging_pressure", "full_multiphysics_transport"],
        "acceptance_criteria": "Material/media dose model tied to transport simulation or test-backed dose envelopes.",
    },
    {
        "id": "archive-media-aging-campaign",
        "track": "Archive media",
        "status": "external_required",
        "closes_failure_modes": ["media_integrity_loss", "material_degradation_pressure"],
        "acceptance_criteria": "Accelerated aging and redundancy evidence that can replace assumption-bound media priors.",
    },
    {
        "id": "bit-recovery-ecc-campaign",
        "track": "Recoverability",
        "status": "external_required",
        "closes_failure_modes": ["bit_recovery_validation"],
        "acceptance_criteria": "End-to-end encode, damage, readout, ECC, and decode tests under expected degradation.",
    },
    {
        "id": "independent-review-pack",
        "track": "External review",
        "status": "external_required",
        "closes_failure_modes": ["launch_and_operations_readiness", "target_horizon_mismatch"],
        "acceptance_criteria": "Independent review of assumptions, targetability, launch feasibility, and public claims.",
    },
]

BLOCKING_CLAIMS = [
    "certified hardware survivability",
    "qualified material stack",
    "proven flight readiness",
    "guaranteed archive recovery",
    "validated launch or operational approval",
]


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _u01(*, seed: int, row_id: str, mode_id: str, sample_index: int, dimension_id: str) -> float:
    payload = f"{seed}:{row_id}:{mode_id}:{sample_index}:{dimension_id}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    integer = int.from_bytes(digest[:8], "big")
    return (integer + 0.5) / 18446744073709551616.0


def _seed_state(*, seed: int, row_id: str, mode_id: str, sample_index: int) -> int:
    payload = f"{seed}:{row_id}:{mode_id}:{sample_index}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    state = int.from_bytes(digest[:8], "big")
    return state or 0x9E3779B97F4A7C15


def _next_u01(state: int) -> tuple[int, float]:
    state ^= (state << 13) & 0xFFFFFFFFFFFFFFFF
    state ^= state >> 7
    state ^= (state << 17) & 0xFFFFFFFFFFFFFFFF
    state &= 0xFFFFFFFFFFFFFFFF
    return state, (state + 0.5) / 18446744073709551616.0


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("quantile requires at least one value")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] + (ordered[high] - ordered[low]) * weight


def quantiles(values: Sequence[float]) -> Dict[str, float]:
    return {
        "p01": _round(_quantile(values, 0.01)),
        "p05": _round(_quantile(values, 0.05)),
        "p50": _round(_quantile(values, 0.50)),
        "p95": _round(_quantile(values, 0.95)),
        "p99": _round(_quantile(values, 0.99)),
    }


def _dimension_draw(*, seed: int, row_id: str, mode_id: str, sample_index: int, dimension_id: str) -> float:
    u = _u01(seed=seed, row_id=row_id, mode_id=mode_id, sample_index=sample_index, dimension_id=dimension_id)
    return _dimension_from_unit(dimension_id, u)


def _dimension_from_unit(dimension_id: str, u: float) -> float:
    if dimension_id in {"dust", "radiation", "plasma", "material_degradation"}:
        return math.exp((u - 0.5) * 1.3)
    if dimension_id == "media_margin":
        return 0.7 + (u * 0.8)
    if dimension_id == "shield_areal_density":
        return 0.78 + (u * 0.44)
    if dimension_id == "exposure_fraction":
        return 0.9 + (u * 0.2)
    if dimension_id == "velocity":
        return 0.94 + (u * 0.16)
    if dimension_id == "target_distance":
        return 0.98 + (u * 0.04)
    if dimension_id == "time_horizon":
        return 0.96 + (u * 0.08)
    return 1.0


def _attack_mode_ids(attack_modes: Any) -> List[str]:
    if isinstance(attack_modes, Mapping):
        modes = attack_modes.get("modes", [])
    else:
        modes = attack_modes
    if not isinstance(modes, list):
        return []
    mode_ids: List[str] = []
    for mode in modes:
        if not isinstance(mode, Mapping):
            continue
        mode_id = mode.get("id") or mode.get("attack_mode_id") or mode.get("mode_id")
        if isinstance(mode_id, str) and mode_id:
            mode_ids.append(mode_id)
    return mode_ids


def _non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def _driver_loss_shares(pressure_by_driver: Mapping[str, float]) -> List[Dict[str, Any]]:
    losses: Dict[str, float] = {}
    for driver, pressure in pressure_by_driver.items():
        if driver == "shield_areal_density":
            penalty = max(0.0, 1.0 - pressure)
        else:
            penalty = max(0.0, pressure - 1.0)
        losses[driver] = DRIVER_WEIGHTS.get(driver, 0.0) * penalty
    if sum(losses.values()) <= 0.0:
        losses = dict(DRIVER_WEIGHTS)
    total = sum(losses.values()) or 1.0
    ordered = sorted(losses.items(), key=lambda item: (-item[1], item[0]))
    return [
        {
            "driver": driver,
            "share": _round(value / total, 9),
        }
        for driver, value in ordered
        if value > 0.0
    ]


def _failure_mode_contributions(driver_shares: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_driver = {str(item["driver"]): float(item["share"]) for item in driver_shares}
    structure = by_driver.get("dust", 0.0) + by_driver.get("shield_areal_density", 0.0) + 0.5 * by_driver.get("plasma", 0.0)
    media = (
        by_driver.get("media_margin", 0.0)
        + by_driver.get("material_degradation", 0.0)
        + by_driver.get("radiation", 0.0)
        + 0.5 * by_driver.get("plasma", 0.0)
    )
    coupled = max(0.05, 1.0 - structure - media)
    raw = {
        "structure_loss": max(0.05, structure),
        "media_loss": max(0.05, media),
        "coupled_structure_media_loss": coupled,
    }
    total = sum(raw.values()) or 1.0
    return [
        {"mode": mode, "share": _round(value / total, 9)}
        for mode, value in raw.items()
    ]


def _required_improvement(p50: float) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for target in (0.5, 0.9):
        gap = max(0.0, target - p50)
        out.append(
            {
                "target_p50": target,
                "achieved": gap <= 0.0,
                "required_hazard_reduction_fraction": _round(gap / max(target, 1.0e-9), 9),
            }
        )
    return out


def _qualification_roadmap(driver_shares: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    top = [str(item["driver"]) for item in driver_shares[:3]]
    labels = {
        "dust": "Full-stack dust impact coupon campaign",
        "shield_areal_density": "Ballistic-limit validation for the shield stack",
        "material_degradation": "Deep-time material degradation surrogate test",
        "media_margin": "Archive media retention and redundancy aging campaign",
        "radiation": "Radiation transport and media dose test",
        "plasma": "Charging and plasma exposure analysis",
    }
    roadmap: List[Dict[str, Any]] = []
    for driver in top:
        roadmap.append(
            {
                "label": labels.get(driver, driver.replace("_", " ")),
                "status": "required",
            }
        )
    return roadmap


def _evidence_needed(driver_shares: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    metadata = {
        "dust": (
            "dust-tail-measurement-upgrade",
            "proxy",
            "Measured dust density and large-particle tail for the selected corridor.",
        ),
        "shield_areal_density": (
            "ballistic-limit-stack-test",
            "assumption_bound",
            "Stack-level ballistic-limit data at representative impact speeds and angles.",
        ),
        "material_degradation": (
            "archive-media-aging-campaign",
            "assumption_bound",
            "Deep-time material aging evidence that can replace bounded degradation priors.",
        ),
        "media_margin": (
            "bit-recovery-ecc-campaign",
            "assumption_bound",
            "Encode/readout/ECC recovery data under expected media damage states.",
        ),
        "radiation": (
            "radiation-transport-campaign",
            "proxy",
            "Radiation transport or test-backed dose envelopes for selected materials and media.",
        ),
        "plasma": (
            "radiation-transport-campaign",
            "proxy",
            "Plasma and charging environment bounds tied to the selected trajectory.",
        ),
        "exposure_fraction": (
            "independent-review-pack",
            "assumption_bound",
            "Independent review of exposure fraction and environment-contact assumptions.",
        ),
    }
    evidence: List[Dict[str, Any]] = []
    for item in driver_shares[:4]:
        driver = str(item.get("driver", "unknown"))
        gap_id, evidence_class, description = metadata.get(
            driver,
            (
                "independent-review-pack",
                "mixed",
                f"External evidence needed to reduce uncertainty for {driver.replace('_', ' ')}.",
            ),
        )
        evidence.append(
            {
                "evidence_gap_id": gap_id,
                "driver": driver,
                "evidence_class": evidence_class,
                "status": "external_required",
                "needed": description,
            }
        )
    return evidence


def _acceptance_criteria(*, row: Mapping[str, Any], mode_id: str, p50: float) -> List[Dict[str, Any]]:
    required_context = {
        "target_id": row.get("targetId"),
        "flight_years": row.get("flightYears"),
        "velocity_id": row.get("velocityId"),
        "capsule_id": row.get("capsuleId"),
        "attack_mode_id": mode_id,
    }
    return [
        {
            "id": "row-context-visible",
            "status": "met" if all(value not in (None, "") for value in required_context.values()) else "blocked",
            "criterion": "Target, horizon, velocity, capsule profile, and attack mode are explicit.",
        },
        {
            "id": "probability-band-visible",
            "status": "met" if 0.0 <= p50 <= 1.0 else "blocked",
            "criterion": "Probability bands are finite and bounded in [0, 1].",
        },
        {
            "id": "evidence-gaps-linked",
            "status": "external_required",
            "criterion": "External evidence gaps remain linked before any qualification claim is allowed.",
        },
        {
            "id": "non-certifying-claim-boundary",
            "status": "met",
            "criterion": "Row blocks certification, qualification, flight-readiness, and guaranteed-recovery claims.",
        },
    ]


def build_risk_budget_for_row(
    *,
    row: Mapping[str, Any],
    attack_mode: Mapping[str, Any],
    sample_count: int,
    seed: int,
) -> Dict[str, Any]:
    row_id = str(row["rowId"])
    mode_id = str(attack_mode["id"])
    output = row.get("output", {})
    if not isinstance(output, Mapping):
        output = {}
    base_p50 = _clamp_probability(float(output.get("survivalProbability", 0.0)))
    base_data = _clamp_probability(float(output.get("dataIntegrityProbability", base_p50)))
    base_structure = _clamp_probability(float(output.get("structureProbability", base_p50)))
    multipliers = attack_mode.get("multipliers", {})
    if not isinstance(multipliers, Mapping):
        multipliers = {}

    samples: List[float] = []
    data_samples: List[float] = []
    pressure_accumulator = {driver: 0.0 for driver in DRIVER_WEIGHTS}
    for sample_index in range(sample_count):
        pressure_by_driver: Dict[str, float] = {}
        state = _seed_state(seed=seed, row_id=row_id, mode_id=mode_id, sample_index=sample_index)
        for driver in DRIVER_WEIGHTS:
            state, u = _next_u01(state)
            draw = _dimension_from_unit(driver, u)
            pressure = draw * float(multipliers.get(driver, 1.0))
            pressure_by_driver[driver] = pressure
            pressure_accumulator[driver] += pressure

        state, u = _next_u01(state)
        target_pressure = _dimension_from_unit("target_distance", u) * float(multipliers.get("target_distance", 1.0))
        state, u = _next_u01(state)
        time_pressure = _dimension_from_unit("time_horizon", u) * float(multipliers.get("time_horizon", 1.0))
        state, u = _next_u01(state)
        velocity_pressure = _dimension_from_unit("velocity", u) * float(multipliers.get("velocity", 1.0))

        hazard_pressure = 0.0
        for driver, weight in DRIVER_WEIGHTS.items():
            pressure = pressure_by_driver[driver]
            if driver == "shield_areal_density":
                hazard_pressure += weight * (1.0 / max(pressure, 0.2))
            else:
                hazard_pressure += weight * pressure
        hazard_pressure *= target_pressure * time_pressure * (velocity_pressure**0.65)

        survival = base_p50 ** max(0.2, hazard_pressure)
        data_integrity = base_data ** max(0.2, 0.55 * hazard_pressure + 0.45 * pressure_by_driver["media_margin"])
        structure = base_structure ** max(0.2, 0.6 * hazard_pressure + 0.4 * pressure_by_driver["dust"])
        samples.append(_clamp_probability(survival))
        data_samples.append(_clamp_probability(data_integrity * math.sqrt(max(structure, 0.0))))

    qs = quantiles(samples)
    data_qs = quantiles(data_samples)
    average_pressure = {
        driver: value / float(sample_count)
        for driver, value in pressure_accumulator.items()
    }
    driver_shares = _driver_loss_shares(average_pressure)
    top_drivers = [
        {
            "driver": item["driver"],
            "sensitivity": _round(-float(item["share"]), 9),
            "contribution": float(item["share"]),
        }
        for item in driver_shares[:5]
    ]
    p50 = qs["p50"]
    status = "inside_budget" if p50 >= 0.5 else ("watch" if p50 >= 0.2 else "over_budget")
    evidence_needed = _evidence_needed(driver_shares)

    return {
        "row_id": row_id,
        "capsule_id": row.get("capsuleId"),
        "target_id": row.get("targetId"),
        "velocity_id": row.get("velocityId"),
        "time_id": row.get("timeId"),
        "flight_years": row.get("flightYears"),
        "attack_mode_id": mode_id,
        "quantiles": qs,
        "monte_carlo": {
            "p05": qs["p05"],
            "p50": qs["p50"],
            "p95": qs["p95"],
            "confidence_level": 0.9,
        },
        "risk_budget": {
            "status": status,
            "survival_probability": p50,
            "data_integrity_probability": data_qs["p50"],
            "loss_probability": _round(1.0 - p50),
            "margin": _round(p50 - 0.5),
        },
        "survival_loss_by_driver": driver_shares,
        "top_uncertainty_drivers": top_drivers,
        "failure_mode_contributions": _failure_mode_contributions(driver_shares),
        "required_improvement": _required_improvement(p50),
        "qualification_roadmap": _qualification_roadmap(driver_shares),
        "evidence_needed": evidence_needed,
        "evidence_gap_ids": sorted({item["evidence_gap_id"] for item in evidence_needed}),
        "acceptance_criteria": _acceptance_criteria(row=row, mode_id=mode_id, p50=p50),
        "blocking_claims": list(BLOCKING_CLAIMS),
    }


def attack_modes_payload(default_row_id: str = DEFAULT_ROW_ID) -> Dict[str, Any]:
    return {
        "default_row_id": default_row_id,
        "modes": [
            {
                "id": mode["id"],
                "attack_mode_id": mode["id"],
                "label": mode["label"],
                "description": mode["description"],
                "multipliers": copy.deepcopy(mode["multipliers"]),
            }
            for mode in ATTACK_MODES
        ],
    }


def validate_capsule_risk_budget_artifact(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("source_artifact_ref") != SOURCE_ARTIFACT_REF:
        errors.append("source_artifact_ref must match capsule survivability artifact")
    source_sha = payload.get("source_artifact_sha256")
    if not isinstance(source_sha, str) or len(source_sha) != 64:
        errors.append("source_artifact_sha256 must be a sha256 hex string")
    sample_count = payload.get("sample_count")
    if not isinstance(sample_count, int) or isinstance(sample_count, bool) or sample_count < MINIMUM_SAMPLE_COUNT:
        errors.append(f"sample_count must be >= {MINIMUM_SAMPLE_COUNT}")

    source_policy = payload.get("source_policy")
    if not isinstance(source_policy, Mapping):
        errors.append("source_policy must be an object")
    else:
        classes = source_policy.get("classes")
        if not isinstance(classes, list):
            errors.append("source_policy.classes must be a list")
            classes = []
        class_ids = {item.get("class") for item in classes if isinstance(item, Mapping)}
        for required_class in ("source_backed", "proxy", "assumption_bound", "mixed"):
            if required_class not in class_ids:
                errors.append(f"source_policy.classes missing {required_class}")
        if not _non_empty_list(source_policy.get("rules")):
            errors.append("source_policy.rules must be a non-empty list")

    failure_modes = payload.get("failure_modes")
    if not isinstance(failure_modes, list) or len(failure_modes) < 8:
        errors.append("failure_modes must contain at least 8 modeled and unmodeled entries")
        failure_modes = []
    else:
        statuses = {item.get("model_status") for item in failure_modes if isinstance(item, Mapping)}
        if "unmodeled" not in statuses:
            errors.append("failure_modes must include unmodeled external-required modes")
        if not ({"partially_modeled", "modeled_contract"} & statuses):
            errors.append("failure_modes must include modeled or partially modeled modes")

    top_level_roadmap = payload.get("qualification_roadmap")
    if not isinstance(top_level_roadmap, list) or len(top_level_roadmap) < 5:
        errors.append("qualification_roadmap must contain at least 5 external evidence tracks")
    else:
        for index, item in enumerate(top_level_roadmap):
            if not isinstance(item, Mapping):
                errors.append(f"qualification_roadmap[{index}] must be object")
                continue
            if not item.get("id") or not item.get("track") or not item.get("acceptance_criteria"):
                errors.append(f"qualification_roadmap[{index}] missing id, track, or acceptance_criteria")
            if item.get("status") != "external_required":
                errors.append(f"qualification_roadmap[{index}] status must be external_required")

    dimensions = payload.get("uncertainty_dimensions")
    if not isinstance(dimensions, list):
        errors.append("uncertainty_dimensions must be a list")
        dimensions = []
    dimension_ids = {item.get("id") for item in dimensions if isinstance(item, Mapping)}
    missing_dimensions = sorted(REQUIRED_DIMENSION_IDS - dimension_ids)
    if missing_dimensions:
        errors.append(f"uncertainty_dimensions missing required ids: {', '.join(missing_dimensions)}")
    for index, dimension in enumerate(dimensions):
        if not isinstance(dimension, Mapping):
            errors.append(f"uncertainty_dimensions[{index}] must be object")
            continue
        if not _non_empty_list(dimension.get("source_ids")):
            errors.append(f"uncertainty_dimensions[{index}] source_ids must be a non-empty list")

    risk_budgets = payload.get("risk_budgets")
    if not isinstance(risk_budgets, list) or not risk_budgets:
        errors.append("risk_budgets must be a non-empty list")
        risk_budgets = []
    elif len(risk_budgets) < 100:
        errors.append("risk_budgets must contain at least 100 rows")
    risk_budget_count = payload.get("risk_budget_count")
    if not isinstance(risk_budget_count, int) or isinstance(risk_budget_count, bool):
        errors.append("risk_budget_count must be an integer")
    elif isinstance(risk_budgets, list) and risk_budget_count != len(risk_budgets):
        errors.append("risk_budget_count must equal len(risk_budgets)")

    default_row_id = payload.get("default_row_id")
    if default_row_id != DEFAULT_ROW_ID:
        errors.append("default_row_id must match the Capsule Lab default row")
    row_ids = {item.get("row_id") or item.get("rowId") for item in risk_budgets if isinstance(item, Mapping)}
    if default_row_id not in row_ids:
        errors.append("default_row_id must reference a risk_budgets row")

    attack_mode_ids = set(_attack_mode_ids(payload.get("attack_modes")))
    missing_modes = sorted(REQUIRED_ATTACK_MODE_IDS - attack_mode_ids)
    if missing_modes:
        errors.append(f"attack_modes missing required ids: {', '.join(missing_modes)}")

    for index, budget in enumerate(risk_budgets):
        if not isinstance(budget, Mapping):
            errors.append(f"risk_budgets[{index}] must be object")
            continue
        row_id = budget.get("row_id") or budget.get("rowId") or f"index {index}"
        mode_id = budget.get("attack_mode_id") or budget.get("mode_id")
        for required_field in ("row_id", "attack_mode_id", "target_id", "flight_years", "velocity_id", "capsule_id"):
            if budget.get(required_field) in (None, ""):
                errors.append(f"risk_budgets[{index}] missing {required_field}")
        if mode_id and mode_id not in attack_mode_ids:
            errors.append(f"risk_budgets[{index}] references unknown attack mode {mode_id!r}")
        qs = budget.get("quantiles")
        if not isinstance(qs, Mapping):
            errors.append(f"risk_budgets[{index}] quantiles must be object")
        else:
            values: List[float] = []
            for key in ("p01", "p05", "p50", "p95", "p99"):
                value = qs.get(key)
                if not _is_number(value) or not 0.0 <= float(value) <= 1.0:
                    errors.append(f"risk_budgets[{index}] quantiles.{key} must be probability")
                else:
                    values.append(float(value))
            if len(values) == 5 and values != sorted(values):
                errors.append(f"risk_budgets[{index}] quantiles must be ordered")
        driver_losses = budget.get("survival_loss_by_driver")
        if not isinstance(driver_losses, list) or len(driver_losses) < 3:
            errors.append(f"risk_budgets[{index}] survival_loss_by_driver must contain at least 3 entries")
        top_drivers = budget.get("top_uncertainty_drivers") or budget.get("uncertainty_drivers")
        if not isinstance(top_drivers, list) or len(top_drivers) < 2:
            errors.append(f"risk_budgets[{index}] top_uncertainty_drivers must contain at least 2 entries")
        failure_modes = budget.get("failure_mode_contributions")
        if not isinstance(failure_modes, list) or len(failure_modes) < 3:
            errors.append(f"risk_budgets[{index}] failure_mode_contributions must contain at least 3 entries")
        else:
            shares = [float(item.get("share", 0.0)) for item in failure_modes if isinstance(item, Mapping)]
            if len(shares) == len(failure_modes) and abs(sum(shares) - 1.0) > 1.0e-6:
                errors.append(f"risk_budgets[{index}] failure_mode_contributions shares must sum to 1")
        improvements = budget.get("required_improvement") or budget.get("required_improvements")
        if not isinstance(improvements, list):
            errors.append(f"risk_budgets[{index}] required_improvement must be list")
        else:
            targets = {str(item.get("target_p50")) for item in improvements if isinstance(item, Mapping)}
            if not {"0.5", "0.9"}.issubset(targets):
                errors.append(f"risk_budgets[{index}] required_improvement missing p50 targets")
        row_roadmap = budget.get("qualification_roadmap")
        if not _non_empty_list(row_roadmap):
            errors.append(f"risk_budgets[{index}] qualification_roadmap must be a non-empty list")
        evidence_needed = budget.get("evidence_needed")
        if not _non_empty_list(evidence_needed):
            errors.append(f"risk_budgets[{index}] evidence_needed must be a non-empty list")
        else:
            for evidence_index, evidence in enumerate(evidence_needed):
                if not isinstance(evidence, Mapping):
                    errors.append(f"risk_budgets[{index}] evidence_needed[{evidence_index}] must be object")
                    continue
                if not evidence.get("evidence_gap_id") or evidence.get("status") != "external_required":
                    errors.append(
                        f"risk_budgets[{index}] evidence_needed[{evidence_index}] must expose external evidence gap"
                    )
        evidence_gap_ids = budget.get("evidence_gap_ids")
        if not _non_empty_list(evidence_gap_ids):
            errors.append(f"risk_budgets[{index}] evidence_gap_ids must be a non-empty list")
        acceptance_criteria = budget.get("acceptance_criteria")
        if not _non_empty_list(acceptance_criteria):
            errors.append(f"risk_budgets[{index}] acceptance_criteria must be a non-empty list")
        blocking_claims = budget.get("blocking_claims")
        if not _non_empty_list(blocking_claims) or not any("certified" in str(claim) for claim in blocking_claims):
            errors.append(f"risk_budgets[{index}] blocking_claims must block certified claims")
        if row_id == DEFAULT_ROW_ID and budget.get("attack_mode_id") == "nominal":
            p50 = float((budget.get("quantiles") or {}).get("p50", -1.0))
            if not 0.02 <= p50 <= 0.9:
                errors.append("default nominal risk budget p50 outside expected review range")

    return errors
