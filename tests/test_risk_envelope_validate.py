from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.risk_envelope_validate import validate


REPO_ROOT = Path(__file__).resolve().parents[1]


class RiskEnvelopeValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract_path = Path("mission/objectives/objective_contract.v1.json")
        self.risk_spec_path = Path("mission/objectives/risk_envelope.v1.json")
        self.uncertainty_model_path = Path("mission/UNCERTAINTY_MODEL_v1.json")
        self.parameter_registry_path = Path("parameters/registry/parameter_registry.v1.json")
        self.parameter_claims_path = Path("parameters/registry/parameter_claims.v1.json")
        self.scenario_path = Path("mission/BASELINE_SCENARIO_v1.json")
        self.evidence_sources_path = Path("parameters/registry/evidence_sources.v1.json")
        self.failure_surface_path = Path("artifacts/failure_surface_baseline.v1.json")
        self.determinism_status_path = Path("artifacts/determinism_status.json")
        self.search_space_path = Path("artifacts/optimization_search_space.v1.json")
        self.frontier_path = Path("artifacts/optimization_frontier_realistic.v1.json")

    def _load_json(self, path: Path):
        return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))

    def _write_temp_json(self, payload: object) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            delete=False,
        )
        with handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return Path(handle.name)

    def _run(self, *, risk_spec_path: Path | None = None, parameter_claims_path: Path | None = None, frontier_path: Path | None = None):
        return validate(
            repo_root=REPO_ROOT,
            objective_contract_path=self.contract_path,
            risk_spec_path=risk_spec_path or self.risk_spec_path,
            uncertainty_model_path=self.uncertainty_model_path,
            parameter_registry_path=self.parameter_registry_path,
            parameter_claims_path=parameter_claims_path or self.parameter_claims_path,
            baseline_scenario_path=self.scenario_path,
            evidence_sources_path=self.evidence_sources_path,
            failure_surface_path=self.failure_surface_path,
            determinism_status_path=self.determinism_status_path,
            search_space_path=self.search_space_path,
            frontier_path=frontier_path or self.frontier_path,
        )

    def test_valid_payload_passes(self) -> None:
        result = self._run()
        self.assertEqual("PASS", result["status"], msg=str(result["errors"]))
        self.assertEqual(0, result["error_count"])

    def test_missing_risk_envelope_fails(self) -> None:
        frontier = self._load_json(self.frontier_path)
        frontier["points"][0]["scores"].pop("risk_envelope", None)
        bad_frontier_path = self._write_temp_json(frontier)
        self.addCleanup(lambda: bad_frontier_path.unlink(missing_ok=True))

        result = self._run(frontier_path=bad_frontier_path)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("risk_envelope" in item for item in result["errors"]))

    def test_seed_mismatch_fails(self) -> None:
        risk_spec = self._load_json(self.risk_spec_path)
        risk_spec["deterministic_seed"] = int(risk_spec["deterministic_seed"]) + 11
        bad_risk_path = self._write_temp_json(risk_spec)
        self.addCleanup(lambda: bad_risk_path.unlink(missing_ok=True))

        result = self._run(risk_spec_path=bad_risk_path)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("deterministic_seed" in item for item in result["errors"]))

    def test_pareto_index_reorder_fails(self) -> None:
        frontier = self._load_json(self.frontier_path)
        frontier["pareto_frontier_indices"] = []
        bad_frontier_path = self._write_temp_json(frontier)
        self.addCleanup(lambda: bad_frontier_path.unlink(missing_ok=True))

        result = self._run(frontier_path=bad_frontier_path)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("pareto_frontier_indices mismatch" in item for item in result["errors"]))

    def test_d_grade_in_search_space_fails(self) -> None:
        claims = self._load_json(self.parameter_claims_path)
        target = self._load_json(self.search_space_path)["parameters_considered"][0]["parameter_id"]
        for item in claims["claims"]:
            if item.get("parameter_id") == target:
                item["trust_grade"] = "D"
                item["mode"] = "realistic"
                break
        bad_claims_path = self._write_temp_json(claims)
        self.addCleanup(lambda: bad_claims_path.unlink(missing_ok=True))

        result = self._run(parameter_claims_path=bad_claims_path)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("trust='D'" in item or "trust 'D'" in item or "trust" in item for item in result["errors"]),
            msg=str(result["errors"]),
        )


if __name__ == "__main__":
    unittest.main()
