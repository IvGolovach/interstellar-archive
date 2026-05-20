from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.ci.objective_contract_validate import validate_contract


REPO_ROOT = Path(__file__).resolve().parents[1]


class ObjectiveContractValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = self._load_json("mission/objectives/objective_contract.v1.json")
        self.artifact = self._load_json("artifacts/objective_score_baseline.v1.json")

    def _load_json(self, relative_path: str):
        return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))

    def _validate(self, contract, artifact):
        return validate_contract(
            contract=contract,
            artifact=artifact,
            contract_path=Path("mission/objectives/objective_contract.v1.json"),
            p_success_defensibility_path=Path("artifacts/p_success_defensibility.json"),
            risk_spec_path=Path("mission/objectives/risk_envelope.v1.json"),
        )

    def test_valid_contract_passes(self) -> None:
        result = self._validate(self.contract, self.artifact)
        self.assertEqual("PASS", result["status"], msg=str(result["errors"]))
        self.assertEqual(0, result["error_count"])

    def test_realistic_forbidden_metric_fails(self) -> None:
        bad_contract = copy.deepcopy(self.contract)
        bad_contract["objective_sets"]["realistic"]["secondary"].append(
            {
                "metric": "trust_weighted_score",
                "maximize": True,
                "aggregation": "weighted",
            }
        )
        bad_contract["objective_sets"]["realistic"]["aggregation"]["dimensions"].append("trust_weighted_score")

        result = self._validate(bad_contract, self.artifact)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("forbidden metric" in error for error in result["errors"]),
            msg=str(result["errors"]),
        )

    def test_missing_p_success_ref_fails(self) -> None:
        bad_contract = copy.deepcopy(self.contract)
        bad_contract["definitions"]["p_success"]["source"] = "artifacts/missing_p_success_defensibility.json"

        result = self._validate(bad_contract, self.artifact)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("definitions.p_success.source" in error for error in result["errors"]),
            msg=str(result["errors"]),
        )

    def test_na_metric_in_objective_vector_fails(self) -> None:
        bad_artifact = copy.deepcopy(self.artifact)
        bad_artifact["scores"]["realistic"]["objective_vector"] = [
            bad_artifact["scores"]["realistic"]["p_success"],
            bad_artifact["scores"]["realistic"]["risk_envelope"],
            0.123,
        ]

        result = self._validate(self.contract, bad_artifact)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("objective_vector length mismatch" in error for error in result["errors"]),
            msg=str(result["errors"]),
        )


if __name__ == "__main__":
    unittest.main()
