from __future__ import annotations

import copy
import unittest
from pathlib import Path

from scripts.ci.failure_surface_validate import (
    _manifest_ids,
    _taxonomy_ids,
    validate_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class FailureSurfaceValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = self._load_json("artifacts/failure_surface_baseline.v1.json")
        self.taxonomy = self._load_json("mission/dag/registry/failure_taxonomy.v1.json")
        self.manifest = self._load_json("artifacts/parameter_drilldown_manifest.json")
        self.taxonomy_ids = _taxonomy_ids(self.taxonomy)
        self.manifest_ids = _manifest_ids(self.manifest)

    def _load_json(self, relative_path: str):
        import json

        return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))

    def test_valid_artifact_passes(self) -> None:
        result = validate_contract(
            artifact=self.artifact,
            taxonomy_ids=self.taxonomy_ids,
            manifest_parameter_ids=self.manifest_ids,
        )
        self.assertEqual("PASS", result["status"], msg=str(result["errors"]))
        self.assertEqual(0, result["error_count"])

    def test_unknown_failure_mode_fails(self) -> None:
        bad = copy.deepcopy(self.artifact)
        bad["outcome"]["failure_mode"] = "UNKNOWN_FAILURE"
        bad["outcome"]["failure_stage"] = "S2"
        bad["outcome"]["outcome_class"] = "FAIL"

        result = validate_contract(
            artifact=bad,
            taxonomy_ids=self.taxonomy_ids,
            manifest_parameter_ids=self.manifest_ids,
        )
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("unknown taxonomy id" in error for error in result["errors"]),
            msg=str(result["errors"]),
        )

    def test_unknown_driver_parameter_fails(self) -> None:
        bad = copy.deepcopy(self.artifact)
        bad["dominant_drivers"]["top3"][0]["parameter_id"] = "unknown.parameter"
        bad["dominant_drivers"]["top3"][0]["evidence_ref"] = (
            "artifacts/parameter_evidence_index.json#unknown.parameter"
        )

        result = validate_contract(
            artifact=bad,
            taxonomy_ids=self.taxonomy_ids,
            manifest_parameter_ids=self.manifest_ids,
        )
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("unknown parameter_id" in error for error in result["errors"]),
            msg=str(result["errors"]),
        )

    def test_baseline_s3_failure_uses_data_integrity_drivers(self) -> None:
        outcome = self.artifact["outcome"]
        self.assertEqual("DATA_CORRUPTION_RADIATION", outcome["failure_mode"])
        driver_ids = [item["parameter_id"] for item in self.artifact["dominant_drivers"]["top3"]]
        self.assertEqual(
            [
                "capsule_model.data_media_survival_margin",
                "capsule_model.material_degradation_mu_1_per_year",
                "environment_model.radiative_flux_w_m2",
            ],
            driver_ids,
        )

    def test_ops_reference_fails(self) -> None:
        bad = copy.deepcopy(self.artifact)
        bad["engine"]["scenario_ref"] = "ops/reports/example.json"

        result = validate_contract(
            artifact=bad,
            taxonomy_ids=self.taxonomy_ids,
            manifest_parameter_ids=self.manifest_ids,
        )
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("must not reference ops" in error for error in result["errors"]),
            msg=str(result["errors"]),
        )


if __name__ == "__main__":
    unittest.main()
