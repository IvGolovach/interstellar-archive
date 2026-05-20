"""Physical constants used by the interstellar archive proof pack.

Source IDs referenced in ``evidence/sources.json``:
- S-003: SI exact speed of light.
- S-004: Solar irradiance baseline for engineering envelope.
- S-005: Gravitational constants for Schwarzschild radius scaling.
- S-006: Solar gravitational parameter for Oberth scale checks.
- S-007: Astronomical unit and light-year conversion factors.
- S-008: Pu-238 half-life used for RTG decay first-order estimate.
"""

SPEED_OF_LIGHT_M_S = 299_792_458.0
GRAVITATIONAL_CONSTANT_M3_KG_S2 = 6.67430e-11
SOLAR_MASS_KG = 1.98847e30
SOLAR_MU_M3_S2 = 1.32712440018e20

AU_M = 149_597_870_700.0
LIGHT_YEAR_M = 9.4607304725808e15
SECONDS_PER_JULIAN_YEAR = 31_557_600.0

SOLAR_CONSTANT_W_M2 = 1361.0
PU238_HALF_LIFE_YEARS = 87.7

