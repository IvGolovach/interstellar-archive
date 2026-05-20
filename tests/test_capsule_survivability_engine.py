from __future__ import annotations

import math
import unittest

from mission.survivability.engine import (
    ProvenancedValue,
    UncertaintyBand,
    run_survivability_analysis,
)


def _validated(value: float, *, units: str, source_id: str) -> ProvenancedValue:
    return ProvenancedValue(
        value=value,
        units=units,
        provenance="validated_source",
        source_ids=(source_id,),
    )


def _proxy(value: float, *, units: str, source_id: str) -> ProvenancedValue:
    return ProvenancedValue(
        value=value,
        units=units,
        provenance="proxy",
        source_ids=(source_id,),
    )


def _assumption(value: float, *, units: str) -> ProvenancedValue:
    return ProvenancedValue(
        value=value,
        units=units,
        provenance="assumption",
        source_ids=("SRC-ASSUME-005",),
    )


class CapsuleSurvivabilityEngineTests(unittest.TestCase):
    def _capsule_design(self) -> dict:
        return {
            "mass_kg": _validated(206.0, units="kg", source_id="SRC-CAPSULE-008"),
            "frontal_area_m2": _validated(1.81, units="m^2", source_id="SRC-CAPSULE-008"),
            "shield_areal_density_kg_m2": _assumption(32.0, units="kg/m^2"),
            "data_media_survival_margin": _assumption(0.82, units="fraction"),
            "material_degradation_mu_1_per_year": _assumption(2.2e-4, units="1/year"),
        }

    def _target(self) -> dict:
        return {
            "radiation_reference_w_m2": _validated(
                20_000_000.0,
                units="W/m^2",
                source_id="SRC-MISSION-002",
            ),
            "plasma_reference_m3": _proxy(
                80_000_000_000.0,
                units="1/m^3",
                source_id="SRC-ENV-003",
            ),
            "dust_reference_scale": _proxy(3.0, units="scale", source_id="SRC-ENV-003"),
        }

    def _trajectory(self) -> dict:
        return {
            "encounter_velocity_km_s": _assumption(22.0, units="km/s"),
            "exposure_fraction": _assumption(1.0, units="fraction"),
            "shield_orientation_factor": _assumption(0.9, units="factor"),
        }

    def _environment(self) -> dict:
        return {
            "radiative_flux_w_m2": _proxy(
                12_000_000.0,
                units="W/m^2",
                source_id="SRC-ENV-003",
            ),
            "plasma_density_proxy_m3": _proxy(
                50_000_000_000.0,
                units="1/m^3",
                source_id="SRC-ENV-003",
            ),
            "dust_flux_scale": _proxy(1.4, units="scale", source_id="SRC-ENV-003"),
        }

    def test_flight_years_is_explicit_and_integrates_hazards_over_years(self) -> None:
        short = run_survivability_analysis(
            capsule_design=self._capsule_design(),
            target=self._target(),
            trajectory=self._trajectory(),
            flight_years=100.0,
            environment=self._environment(),
            uncertainty_bands=[],
            samples=1,
            seed=7,
        )
        long = run_survivability_analysis(
            capsule_design=self._capsule_design(),
            target=self._target(),
            trajectory=self._trajectory(),
            flight_years=1000.0,
            environment=self._environment(),
            uncertainty_bands=[],
            samples=1,
            seed=7,
        )

        self.assertEqual(100.0, short["flight_years"])
        self.assertEqual(1000.0, long["flight_years"])
        self.assertGreater(
            long["nominal"]["integrated_hazards"]["structure"],
            short["nominal"]["integrated_hazards"]["structure"],
        )
        self.assertAlmostEqual(
            10.0,
            long["nominal"]["integrated_hazards"]["structure"]
            / short["nominal"]["integrated_hazards"]["structure"],
            places=12,
        )
        self.assertGreater(
            short["nominal"]["structure_survival"],
            long["nominal"]["structure_survival"],
        )
        self.assertEqual(
            "exp(-annual_hazard_1_per_year * flight_years * exposure_fraction)",
            short["formulas"]["hazard_integration"],
        )

    def test_deterministic_bands_use_only_bounded_uncertainty_samples(self) -> None:
        bands = [
            UncertaintyBand(
                name="material_degradation",
                target="capsule.material_degradation_mu_1_per_year",
                low=1.0e-4,
                high=4.0e-4,
                provenance="assumption",
            ),
            UncertaintyBand(
                name="dust_flux",
                target="environment.dust_flux_scale",
                low=0.8,
                high=2.4,
                provenance="proxy",
            ),
            UncertaintyBand(
                name="media_margin",
                target="capsule.data_media_survival_margin",
                low=0.74,
                high=0.9,
                provenance="assumption",
            ),
        ]

        first = run_survivability_analysis(
            capsule_design=self._capsule_design(),
            target=self._target(),
            trajectory=self._trajectory(),
            flight_years=250.0,
            environment=self._environment(),
            uncertainty_bands=bands,
            samples=16,
            seed=1234,
        )
        second = run_survivability_analysis(
            capsule_design=self._capsule_design(),
            target=self._target(),
            trajectory=self._trajectory(),
            flight_years=250.0,
            environment=self._environment(),
            uncertainty_bands=bands,
            samples=16,
            seed=1234,
        )

        self.assertEqual(first, second)
        self.assertEqual(16, first["sample_count"])
        self.assertEqual(16, len(first["samples"]))

        for sample in first["samples"]:
            draws = sample["uncertainty_draws"]
            self.assertGreaterEqual(draws["material_degradation"], 1.0e-4)
            self.assertLessEqual(draws["material_degradation"], 4.0e-4)
            self.assertGreaterEqual(draws["dust_flux"], 0.8)
            self.assertLessEqual(draws["dust_flux"], 2.4)
            self.assertGreaterEqual(draws["media_margin"], 0.74)
            self.assertLessEqual(draws["media_margin"], 0.9)

        structure_values = [item["structure_survival"] for item in first["samples"]]
        media_values = [item["media_integrity"] for item in first["samples"]]
        total_values = [item["total_capsule_survival"] for item in first["samples"]]
        self.assertEqual(min(structure_values), first["scenario_bands"]["structure_survival"]["min"])
        self.assertEqual(max(structure_values), first["scenario_bands"]["structure_survival"]["max"])
        self.assertEqual(min(media_values), first["scenario_bands"]["media_integrity"]["min"])
        self.assertEqual(max(total_values), first["scenario_bands"]["total_capsule_survival"]["max"])

    def test_provenance_report_separates_validated_proxy_and_assumption_values(self) -> None:
        result = run_survivability_analysis(
            capsule_design=self._capsule_design(),
            target=self._target(),
            trajectory=self._trajectory(),
            flight_years=50.0,
            environment=self._environment(),
            uncertainty_bands=[],
            samples=1,
            seed=5,
        )

        provenance = result["input_provenance"]
        self.assertEqual(
            "validated_source",
            provenance["capsule.mass_kg"]["provenance"],
        )
        self.assertTrue(provenance["capsule.mass_kg"]["source_backed"])
        self.assertEqual(
            "proxy",
            provenance["environment.plasma_density_proxy_m3"]["provenance"],
        )
        self.assertFalse(provenance["environment.plasma_density_proxy_m3"]["source_backed"])
        self.assertEqual(
            "assumption",
            provenance["capsule.material_degradation_mu_1_per_year"]["provenance"],
        )
        self.assertFalse(
            provenance["capsule.material_degradation_mu_1_per_year"]["source_backed"]
        )
        self.assertEqual(
            ["capsule.frontal_area_m2", "capsule.mass_kg", "target.radiation_reference_w_m2"],
            result["provenance_summary"]["validated_source_inputs"],
        )
        self.assertIn(
            "environment.radiative_flux_w_m2",
            result["provenance_summary"]["proxy_inputs"],
        )
        self.assertIn(
            "capsule.shield_areal_density_kg_m2",
            result["provenance_summary"]["assumption_inputs"],
        )
        self.assertIn("structure_dust_base_hazard_1_per_year", result["model_coefficients"])
        self.assertEqual(
            "assumption",
            result["model_coefficients"]["structure_dust_base_hazard_1_per_year"]["provenance"],
        )

    def test_public_capsule_design_loader_shape_is_consumed_directly(self) -> None:
        from mission.capsule.design import load_default_capsule_design

        result = run_survivability_analysis(
            capsule_design=load_default_capsule_design(),
            target=self._target(),
            trajectory=self._trajectory(),
            flight_years=10_000_000.0,
            environment=self._environment(),
            uncertainty_bands=[],
            samples=1,
            seed=8,
        )

        self.assertEqual(10_000_000.0, result["flight_years"])
        self.assertEqual("proxy", result["input_provenance"]["capsule.mass_kg"]["provenance"])
        self.assertEqual(
            "assumption",
            result["input_provenance"]["capsule.material_degradation_mu_1_per_year"]["provenance"],
        )
        self.assertTrue(0.0 <= result["nominal"]["total_capsule_survival"] <= 1.0)

    def test_total_capsule_survival_is_structure_times_media_integrity(self) -> None:
        result = run_survivability_analysis(
            capsule_design=self._capsule_design(),
            target=self._target(),
            trajectory=self._trajectory(),
            flight_years=10.0,
            environment=self._environment(),
            uncertainty_bands=[],
            samples=1,
            seed=1,
        )
        nominal = result["nominal"]

        self.assertTrue(0.0 <= nominal["structure_survival"] <= 1.0)
        self.assertTrue(0.0 <= nominal["media_integrity"] <= 1.0)
        self.assertAlmostEqual(
            nominal["structure_survival"] * nominal["media_integrity"],
            nominal["total_capsule_survival"],
            places=12,
        )
        self.assertEqual(
            "structure_survival * media_integrity",
            result["formulas"]["total_capsule_survival"],
        )

    def test_invalid_inputs_fail_before_producing_bands(self) -> None:
        with self.assertRaisesRegex(ValueError, "flight_years must be > 0"):
            run_survivability_analysis(
                capsule_design=self._capsule_design(),
                target=self._target(),
                trajectory=self._trajectory(),
                flight_years=0.0,
                environment=self._environment(),
                uncertainty_bands=[],
                samples=1,
                seed=1,
            )

        with self.assertRaisesRegex(ValueError, "uncertainty band .* must satisfy low < high"):
            run_survivability_analysis(
                capsule_design=self._capsule_design(),
                target=self._target(),
                trajectory=self._trajectory(),
                flight_years=10.0,
                environment=self._environment(),
                uncertainty_bands=[
                    UncertaintyBand(
                        name="bad",
                        target="environment.dust_flux_scale",
                        low=2.0,
                        high=2.0,
                        provenance="proxy",
                    )
                ],
                samples=4,
                seed=1,
            )

        bad_design = self._capsule_design()
        bad_design["mass_kg"] = ProvenancedValue(
            value=206.0,
            units="kg",
            provenance="validated_source",
            source_ids=(),
        )
        with self.assertRaisesRegex(
            ValueError,
            "validated_source input capsule.mass_kg requires source_ids",
        ):
            run_survivability_analysis(
                capsule_design=bad_design,
                target=self._target(),
                trajectory=self._trajectory(),
                flight_years=10.0,
                environment=self._environment(),
                uncertainty_bands=[],
                samples=1,
                seed=1,
            )

    def test_extreme_hazards_remain_finite_probabilities(self) -> None:
        environment = self._environment()
        environment["radiative_flux_w_m2"] = _proxy(
            2.0e8,
            units="W/m^2",
            source_id="SRC-ENV-003",
        )
        result = run_survivability_analysis(
            capsule_design=self._capsule_design(),
            target=self._target(),
            trajectory=self._trajectory(),
            flight_years=1_000_000.0,
            environment=environment,
            uncertainty_bands=[],
            samples=1,
            seed=2,
        )

        for key in ("structure_survival", "media_integrity", "total_capsule_survival"):
            self.assertTrue(math.isfinite(result["nominal"][key]))
            self.assertGreaterEqual(result["nominal"][key], 0.0)
            self.assertLessEqual(result["nominal"][key], 1.0)


if __name__ == "__main__":
    unittest.main()
