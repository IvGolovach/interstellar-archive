from __future__ import annotations

import unittest

from models.constants import SOLAR_MASS_KG
from models.core_physics import (
    oberth_asymptotic_speed_m_s,
    rtg_power_fraction,
    schwarzschild_radius_m,
    solar_flux_w_m2,
    time_of_flight_years,
    transverse_delta_v_required_m_s,
)


class CorePhysicsTests(unittest.TestCase):
    def test_schwarzschild_radius_reference_mass(self) -> None:
        radius_km = schwarzschild_radius_m(10.0 * SOLAR_MASS_KG) / 1_000.0
        self.assertGreater(radius_km, 29.0)
        self.assertLess(radius_km, 30.0)

    def test_solar_flux_inverse_square(self) -> None:
        flux_01 = solar_flux_w_m2(0.1) / 1_000_000.0
        flux_005 = solar_flux_w_m2(0.05) / 1_000_000.0
        self.assertAlmostEqual(flux_01, 0.1361, places=4)
        self.assertAlmostEqual(flux_005, 0.5444, places=4)

    def test_oberth_baseline_envelope(self) -> None:
        speeds = sorted(
            oberth_asymptotic_speed_m_s(q_au=q, delta_v_m_s=dv) / 1_000.0
            for q in (0.05, 0.10)
            for dv in (2_000.0, 3_000.0)
        )
        self.assertGreaterEqual(speeds[0], 23.0)
        self.assertLessEqual(speeds[-1], 34.0)

    def test_transverse_delta_v_leverage(self) -> None:
        dv_min = transverse_delta_v_required_m_s(23_000.0, 1_000.0, 1560.0)
        dv_max = transverse_delta_v_required_m_s(45_000.0, 1_000.0, 1560.0)
        self.assertAlmostEqual(dv_min, 0.233133122, places=6)
        self.assertAlmostEqual(dv_max, 0.456130022, places=6)

    def test_time_of_flight_and_decay(self) -> None:
        tof_myr = time_of_flight_years(distance_ly=1560.0, speed_m_s=23_000.0) / 1_000_000.0
        self.assertGreater(tof_myr, 20.0)
        self.assertLess(tof_myr, 20.8)

        self.assertAlmostEqual(rtg_power_fraction(87.7), 0.5, places=6)
        self.assertLess(rtg_power_fraction(1000.0), 0.001)

    def test_invalid_inputs_raise(self) -> None:
        with self.assertRaises(ValueError):
            solar_flux_w_m2(0.0)
        with self.assertRaises(ValueError):
            oberth_asymptotic_speed_m_s(q_au=0.1, delta_v_m_s=-1.0)
        with self.assertRaises(ValueError):
            transverse_delta_v_required_m_s(vinf_m_s=0.0, r_int_au=100.0, distance_ly=1560.0)


if __name__ == "__main__":
    unittest.main()

