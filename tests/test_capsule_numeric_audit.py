from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CapsuleNumericAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = _load_json(REPO_ROOT / "mission" / "BASELINE_SCENARIO_v1.json")
        self.schema = _load_json(REPO_ROOT / "mission" / "MISSION_SCHEMA_v1.json")
        self.registry = _load_json(REPO_ROOT / "parameters" / "registry" / "parameter_registry.v1.json")
        self.claims = _load_json(REPO_ROOT / "parameters" / "registry" / "parameter_claims.v1.json")
        self.sources = _load_json(REPO_ROOT / "parameters" / "registry" / "evidence_sources.v1.json")

    def _registry_entry(self, parameter_id: str) -> dict:
        for entry in self.registry["parameters"]:
            if entry["parameter_id"] == parameter_id:
                return entry
        self.fail(f"missing registry entry for {parameter_id}")

    def _claim_entry(self, parameter_id: str) -> dict:
        for claim in self.claims["claims"]:
            if claim["parameter_id"] == parameter_id:
                return claim
        self.fail(f"missing claim for {parameter_id}")

    def test_baseline_capsule_heritage_pair_is_consistent(self) -> None:
        capsule = self.scenario["capsule_model"]
        self.assertEqual(206, capsule["mass_kg"])
        self.assertAlmostEqual(1.81, capsule["frontal_area_m2"], places=6)

    def test_mass_and_area_use_genesis_heritage_source(self) -> None:
        mass_claim = self._claim_entry("capsule_model.mass_kg")
        area_claim = self._claim_entry("capsule_model.frontal_area_m2")

        self.assertEqual("B", mass_claim["trust_grade"])
        self.assertEqual("B", area_claim["trust_grade"])
        self.assertEqual(["SRC-CAPSULE-008", "SRC-ASSUME-005"], mass_claim["evidence_source_ids"])
        self.assertEqual(["SRC-CAPSULE-008", "SRC-ASSUME-005"], area_claim["evidence_source_ids"])

    def test_non_core_capsule_parameters_are_not_marked_as_p_success_drivers(self) -> None:
        for parameter_id in (
            "capsule_model.mass_kg",
            "capsule_model.frontal_area_m2",
            "capsule_model.shield_areal_density_kg_m2",
        ):
            entry = self._registry_entry(parameter_id)
            self.assertFalse(entry["affects_core_probability"], parameter_id)
            self.assertEqual(["mission_validation"], entry["used_in"], parameter_id)

    def test_capsule_prior_bounds_match_audit_contract(self) -> None:
        data_media = self._registry_entry("capsule_model.data_media_survival_margin")
        degradation = self._registry_entry("capsule_model.material_degradation_mu_1_per_year")

        self.assertEqual([0.4, 0.98], data_media["bounds"])
        self.assertEqual([0.0001, 0.0004], degradation["bounds"])
        self.assertEqual(
            ["SRC-CAPSULE-009", "SRC-ASSUME-005"],
            degradation["distribution"]["evidence_source_ids"],
        )

    def test_schema_bounds_match_capsule_audit_envelopes(self) -> None:
        capsule_properties = self.schema["properties"]["capsule_model"]["properties"]
        self.assertEqual(0.4, capsule_properties["data_media_survival_margin"]["minimum"])
        self.assertEqual(0.98, capsule_properties["data_media_survival_margin"]["maximum"])
        self.assertEqual(0.0001, capsule_properties["material_degradation_mu_1_per_year"]["minimum"])
        self.assertEqual(0.0004, capsule_properties["material_degradation_mu_1_per_year"]["maximum"])

    def test_capsule_sources_include_explicit_public_urls(self) -> None:
        source_map = {item["source_id"]: item for item in self.sources["sources"]}
        self.assertEqual("https://ntrs.nasa.gov/citations/20070014646", source_map["SRC-CAPSULE-008"]["url"])
        self.assertEqual("https://ntrs.nasa.gov/citations/20070031961", source_map["SRC-CAPSULE-009"]["url"])


if __name__ == "__main__":
    unittest.main()
