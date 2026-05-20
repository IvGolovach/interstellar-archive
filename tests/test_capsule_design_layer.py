from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_LAYER_IDS = [
    "c_c_sic_tps",
    "al_li_bumper",
    "stand_off_gap",
    "b4c_ta_rear_wall",
    "ti_vault",
    "data_media_package",
    "redundancy_margin",
]


class CapsuleDesignLayerTests(unittest.TestCase):
    def _design_module(self):
        try:
            return importlib.import_module("mission.capsule.design")
        except ModuleNotFoundError as exc:
            self.fail(f"missing capsule design loader: {exc}")

    def test_default_design_loads_expected_v1_stack(self) -> None:
        design_module = self._design_module()

        design = design_module.load_default_capsule_design()

        self.assertEqual("capsule_design.v1", design["schema_version"])
        self.assertEqual(EXPECTED_LAYER_IDS, [layer["layer_id"] for layer in design["layers"]])
        self.assertEqual(206.0, design["mass_budget"]["configured_capsule_mass_kg"])
        self.assertEqual(0.25, design["mass_budget"]["declared_margin_kg"])

        materials = {material["material_id"]: material for material in design["materials"]}
        self.assertEqual("C/C-SiC TPS", materials["c_c_sic"]["name"])
        self.assertEqual("Al-Li alloy bumper", materials["al_li"]["name"])
        self.assertEqual("Open stand-off gap", materials["stand_off_gap"]["name"])
        self.assertEqual("B4C/Ta rear wall", materials["b4c_ta"]["name"])
        self.assertEqual("Titanium vault", materials["ti_vault"]["name"])
        self.assertEqual("Data media package", materials["data_media"]["name"])

    def test_default_design_validates_and_closes_mass_budget(self) -> None:
        design_module = self._design_module()
        design = design_module.load_default_capsule_design()

        errors = design_module.validate_capsule_design(design)
        summary = design_module.summarize_mass_budget(design)

        self.assertEqual([], errors)
        self.assertEqual(EXPECTED_LAYER_IDS, summary["layer_ids"])
        self.assertAlmostEqual(206.0, summary["component_mass_kg"], places=9)
        self.assertAlmostEqual(0.0, summary["closure_delta_kg"], places=9)
        self.assertLessEqual(abs(summary["closure_delta_kg"]), summary["declared_margin_kg"])

    def test_layer_and_material_assumptions_are_bounded(self) -> None:
        design_module = self._design_module()
        design = design_module.load_default_capsule_design()

        for material in design["materials"]:
            density = material.get("density_kg_m3")
            if density is None:
                continue
            low, high = material["bounds"]["density_kg_m3"]
            self.assertLessEqual(low, density, material["material_id"])
            self.assertLessEqual(density, high, material["material_id"])

        for layer in design["layers"]:
            mass_low, mass_high = layer["bounds"]["mass_kg"]
            self.assertLessEqual(mass_low, layer["mass_kg"], layer["layer_id"])
            self.assertLessEqual(layer["mass_kg"], mass_high, layer["layer_id"])

        gap = next(layer for layer in design["layers"] if layer["layer_id"] == "stand_off_gap")
        self.assertEqual(0.0, gap["mass_kg"])
        self.assertEqual([0.15, 0.45], gap["bounds"]["stand_off_gap_m"])
        self.assertEqual(0.25, gap["stand_off_gap_m"])

    def test_validator_reports_mass_closure_and_stack_errors(self) -> None:
        design_module = self._design_module()
        design = design_module.load_default_capsule_design()

        bad_mass = copy.deepcopy(design)
        bad_mass["layers"][0]["mass_kg"] += 1.0
        mass_errors = design_module.validate_capsule_design(bad_mass)
        self.assertTrue(any("mass closure" in error for error in mass_errors), mass_errors)

        missing_rear_wall = copy.deepcopy(design)
        missing_rear_wall["layers"] = [
            layer for layer in missing_rear_wall["layers"] if layer["layer_id"] != "b4c_ta_rear_wall"
        ]
        stack_errors = design_module.validate_capsule_design(missing_rear_wall)
        self.assertTrue(any("required stack" in error for error in stack_errors), stack_errors)

    def test_validator_rejects_stale_declared_mass_and_radial_order(self) -> None:
        design_module = self._design_module()
        design = design_module.load_default_capsule_design()

        stale_declared_mass = copy.deepcopy(design)
        stale_declared_mass["mass_budget"]["component_mass_kg"] = 205.0
        mass_errors = design_module.validate_capsule_design(stale_declared_mass)
        self.assertTrue(any("component_mass_kg" in error for error in mass_errors), mass_errors)

        stale_radial_order = copy.deepcopy(design)
        stale_radial_order["layers"][2]["radial_order"] = 99
        order_errors = design_module.validate_capsule_design(stale_radial_order)
        self.assertTrue(any("radial_order" in error for error in order_errors), order_errors)

    def test_survivability_model_inputs_are_explicit_and_bounded(self) -> None:
        design_module = self._design_module()
        design = design_module.load_default_capsule_design()
        inputs = design["survivability_model_inputs"]

        self.assertIn("frontal_area_m2", inputs)
        self.assertIn("shield_areal_density_kg_m2", inputs)
        self.assertIn("data_media_survival_margin", inputs)
        self.assertIn("material_degradation_mu_1_per_year", inputs)
        self.assertEqual("assumption", inputs["material_degradation_mu_1_per_year"]["provenance"])
        self.assertEqual([1e-09, 2e-07], design["survivability_uncertainty_bounds"]["material_degradation_mu_1_per_year"])

    def test_capsule_design_data_is_registered_as_required_path(self) -> None:
        manifest = json.loads((REPO_ROOT / "docs" / "required_paths.v1.json").read_text(encoding="utf-8"))
        paths = {
            path
            for group in manifest["groups"]
            for path in group["paths"]
        }

        self.assertIn("mission/capsule/capsule_design.v1.json", paths)

    def test_loader_source_has_no_network_dependency(self) -> None:
        design_module = self._design_module()
        source = Path(design_module.__file__).read_text(encoding="utf-8")

        for forbidden in ("urllib", "requests", "http.client", "socket"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
