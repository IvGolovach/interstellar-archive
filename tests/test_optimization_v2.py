from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts import build_optimization_v2_artifact
from scripts.ci.optimization_v2_validate import validate


REPO_ROOT = Path(__file__).resolve().parents[1]


class OptimizationV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads((REPO_ROOT / "artifacts/optimization_v2_frontier.v1.json").read_text())

    def test_valid_payload_passes(self) -> None:
        result = validate(payload=self.payload, repo_root=REPO_ROOT)

        self.assertEqual("PASS", result["status"], msg=str(result["errors"]))
        self.assertEqual(0, result["error_count"])

    def test_builder_matches_committed_artifact(self) -> None:
        built = build_optimization_v2_artifact.build_payload(repo_root=REPO_ROOT)

        self.assertEqual(self.payload, built)

    def test_pareto_tamper_fails(self) -> None:
        bad = copy.deepcopy(self.payload)
        bad["pareto_frontier_candidate_ids"] = []

        result = validate(payload=bad, repo_root=REPO_ROOT)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("pareto_frontier_candidate_ids" in error for error in result["errors"]))

    def test_cost_proxy_missing_fails(self) -> None:
        bad = copy.deepcopy(self.payload)
        bad["candidates"][0]["scores"].pop("cost_proxy")

        result = validate(payload=bad, repo_root=REPO_ROOT)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("cost_proxy" in error for error in result["errors"]))

    def test_internal_dominant_driver_fails(self) -> None:
        bad = copy.deepcopy(self.payload)
        bad["candidates"][0]["dominant_drivers"]["parameter_ids"].append("code_literal.synthetic")

        result = validate(payload=bad, repo_root=REPO_ROOT)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("dominant_drivers leaks internal" in error for error in result["errors"]))

    def test_overclaim_drift_fails(self) -> None:
        bad = copy.deepcopy(self.payload)
        bad["rollup"]["qualification_complete"] = True
        bad["blocked_claims"].remove("qualification complete")
        bad["blocked_claims"].remove("flight-ready design selected")

        result = validate(payload=bad, repo_root=REPO_ROOT)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("qualification" in error for error in result["errors"]))
        self.assertTrue(any("flight-ready" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
