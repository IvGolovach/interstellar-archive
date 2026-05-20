"""Computed values for quantitative claims in the whitepaper."""

from __future__ import annotations

from typing import Dict

from models.constants import PU238_HALF_LIFE_YEARS, SOLAR_MASS_KG
from models.core_physics import (
    oberth_asymptotic_speed_m_s,
    rtg_power_fraction,
    schwarzschild_radius_m,
    solar_flux_w_m2,
    time_of_flight_years,
    transverse_delta_v_required_m_s,
)


REFERENCE_DISTANCE_LY = 1560.0


def _km_s(value_m_s: float) -> float:
    return value_m_s / 1_000.0


def _mw_m2(value_w_m2: float) -> float:
    return value_w_m2 / 1_000_000.0


def compute_claim_values() -> Dict[str, Dict[str, float]]:
    """Return deterministic values keyed by claim ID."""
    baseline_speeds_km_s = sorted(
        _km_s(
            oberth_asymptotic_speed_m_s(
                q_au=q_au,
                delta_v_m_s=delta_v_m_s,
                inbound_vinf_m_s=0.0,
            )
        )
        for q_au in (0.05, 0.10)
        for delta_v_m_s in (2_000.0, 3_000.0)
    )

    conditional_speeds_km_s = sorted(
        _km_s(
            oberth_asymptotic_speed_m_s(
                q_au=0.05,
                delta_v_m_s=3_000.0,
                inbound_vinf_m_s=inbound_vinf_km_s * 1_000.0,
            )
        )
        for inbound_vinf_km_s in (10.0, 20.0, 30.0)
    )

    dv_1000_au = sorted(
        transverse_delta_v_required_m_s(
            vinf_m_s=vinf_km_s * 1_000.0,
            r_int_au=1_000.0,
            distance_ly=REFERENCE_DISTANCE_LY,
        )
        for vinf_km_s in (23.0, 45.0)
    )
    dv_100_au = sorted(
        transverse_delta_v_required_m_s(
            vinf_m_s=vinf_km_s * 1_000.0,
            r_int_au=100.0,
            distance_ly=REFERENCE_DISTANCE_LY,
        )
        for vinf_km_s in (23.0, 45.0)
    )

    tof_baseline_myr = sorted(
        time_of_flight_years(distance_ly=REFERENCE_DISTANCE_LY, speed_m_s=vinf_km_s * 1_000.0)
        / 1_000_000.0
        for vinf_km_s in (34.0, 23.0)
    )
    tof_conditional_myr = sorted(
        time_of_flight_years(distance_ly=REFERENCE_DISTANCE_LY, speed_m_s=vinf_km_s * 1_000.0)
        / 1_000_000.0
        for vinf_km_s in (45.0, 35.0)
    )

    return {
        "C-001": {
            "r_s_km": schwarzschild_radius_m(10.0 * SOLAR_MASS_KG) / 1_000.0,
        },
        "C-002": {
            "flux_0p10_au_mw_m2": _mw_m2(solar_flux_w_m2(0.10)),
            "flux_0p05_au_mw_m2": _mw_m2(solar_flux_w_m2(0.05)),
        },
        "C-003": {
            "vinf_baseline_min_km_s": baseline_speeds_km_s[0],
            "vinf_baseline_max_km_s": baseline_speeds_km_s[-1],
        },
        "C-004": {
            "vinf_conditional_min_km_s": conditional_speeds_km_s[0],
            "vinf_conditional_max_km_s": conditional_speeds_km_s[-1],
        },
        "C-005": {
            "delta_v_1000_au_min_m_s": dv_1000_au[0],
            "delta_v_1000_au_max_m_s": dv_1000_au[-1],
            "delta_v_100_au_min_m_s": dv_100_au[0],
            "delta_v_100_au_max_m_s": dv_100_au[-1],
        },
        "C-006": {
            "tof_baseline_min_myr": tof_baseline_myr[0],
            "tof_baseline_max_myr": tof_baseline_myr[-1],
            "tof_conditional_min_myr": tof_conditional_myr[0],
            "tof_conditional_max_myr": tof_conditional_myr[-1],
        },
        "C-007": {
            "rtg_fraction_10y": rtg_power_fraction(10.0),
            "rtg_fraction_50y": rtg_power_fraction(50.0),
            "rtg_fraction_half_life": rtg_power_fraction(PU238_HALF_LIFE_YEARS),
            "rtg_fraction_1000y": rtg_power_fraction(1_000.0),
        },
        "C-008": {},
        "C-009": {
            "archive_cost_anchor_usd": 100_000_000.0,
            "flagship_cost_anchor_usd": 1_000_000_000.0,
            "cost_anchor_ratio": 10.0,
        },
    }
