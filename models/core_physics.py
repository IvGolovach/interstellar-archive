"""Core physics helpers for claim verification."""

from __future__ import annotations

import math

from models.constants import (
    AU_M,
    GRAVITATIONAL_CONSTANT_M3_KG_S2,
    LIGHT_YEAR_M,
    PU238_HALF_LIFE_YEARS,
    SECONDS_PER_JULIAN_YEAR,
    SOLAR_CONSTANT_W_M2,
    SOLAR_MU_M3_S2,
    SPEED_OF_LIGHT_M_S,
)


def schwarzschild_radius_m(mass_kg: float) -> float:
    """Return Schwarzschild radius in meters for a non-rotating mass."""
    if mass_kg <= 0:
        raise ValueError("mass_kg must be positive")
    return (2.0 * GRAVITATIONAL_CONSTANT_M3_KG_S2 * mass_kg) / (SPEED_OF_LIGHT_M_S**2)


def solar_flux_w_m2(distance_au: float, solar_constant_w_m2: float = SOLAR_CONSTANT_W_M2) -> float:
    """Return inverse-square solar irradiance at the given heliocentric distance."""
    if distance_au <= 0:
        raise ValueError("distance_au must be positive")
    return solar_constant_w_m2 / (distance_au**2)


def perihelion_speed_m_s(q_au: float, inbound_vinf_m_s: float = 0.0) -> float:
    """Return perihelion speed before burn under two-body approximation."""
    if q_au <= 0:
        raise ValueError("q_au must be positive")
    if inbound_vinf_m_s < 0:
        raise ValueError("inbound_vinf_m_s must be non-negative")
    q_m = q_au * AU_M
    return math.sqrt((inbound_vinf_m_s**2) + (2.0 * SOLAR_MU_M3_S2 / q_m))


def oberth_asymptotic_speed_m_s(
    q_au: float,
    delta_v_m_s: float,
    inbound_vinf_m_s: float = 0.0,
) -> float:
    """Return outgoing asymptotic speed after a prograde perihelion impulse."""
    if delta_v_m_s < 0:
        raise ValueError("delta_v_m_s must be non-negative")
    q_m = q_au * AU_M
    v_perihelion_pre = perihelion_speed_m_s(q_au=q_au, inbound_vinf_m_s=inbound_vinf_m_s)
    v_perihelion_post = v_perihelion_pre + delta_v_m_s
    argument = (v_perihelion_post**2) - (2.0 * SOLAR_MU_M3_S2 / q_m)
    return math.sqrt(max(argument, 0.0))


def transverse_delta_v_required_m_s(vinf_m_s: float, r_int_au: float, distance_ly: float) -> float:
    """Linearized cross-track correction scale for large-distance targeting."""
    if vinf_m_s <= 0:
        raise ValueError("vinf_m_s must be positive")
    if r_int_au <= 0:
        raise ValueError("r_int_au must be positive")
    if distance_ly <= 0:
        raise ValueError("distance_ly must be positive")
    distance_au = (distance_ly * LIGHT_YEAR_M) / AU_M
    return vinf_m_s * (r_int_au / distance_au)


def time_of_flight_years(distance_ly: float, speed_m_s: float) -> float:
    """Return ballistic time of flight in Julian years."""
    if distance_ly <= 0:
        raise ValueError("distance_ly must be positive")
    if speed_m_s <= 0:
        raise ValueError("speed_m_s must be positive")
    return (distance_ly * LIGHT_YEAR_M / speed_m_s) / SECONDS_PER_JULIAN_YEAR


def rtg_power_fraction(years_elapsed: float, half_life_years: float = PU238_HALF_LIFE_YEARS) -> float:
    """Return remaining RTG thermal power fraction from radioactive decay only."""
    if years_elapsed < 0:
        raise ValueError("years_elapsed must be non-negative")
    if half_life_years <= 0:
        raise ValueError("half_life_years must be positive")
    return 2.0 ** (-years_elapsed / half_life_years)

