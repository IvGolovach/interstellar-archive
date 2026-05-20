from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import build_optimization_frontier
from scripts.ci.optimization_frontier_validate import validate


REPO_ROOT = Path(__file__).resolve().parents[1]


class OptimizationFrontierValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract_path = Path("mission/objectives/objective_contract.v1.json")
        self.risk_spec_path = Path("mission/objectives/risk_envelope.v1.json")
        self.search_space_path = Path("artifacts/optimization_search_space.v1.json")
        self.frontier_path = Path("artifacts/optimization_frontier_realistic.v1.json")

        self.contract = self._load_json(self.contract_path)
        self.risk_spec = self._load_json(self.risk_spec_path)
        self.parameter_registry = self._load_json("parameters/registry/parameter_registry.v1.json")
        self.parameter_claims = self._load_json("parameters/registry/parameter_claims.v1.json")
        self.search_space = self._load_json(self.search_space_path)
        self.frontier = self._load_json(self.frontier_path)

    def _load_json(self, relative_path: str | Path):
        return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))

    def _validate(self, *, parameter_registry=None, claims=None, search_space=None, frontier=None):
        return validate(
            contract=self.contract,
            parameter_registry=parameter_registry if parameter_registry is not None else self.parameter_registry,
            parameter_claims=claims if claims is not None else self.parameter_claims,
            risk_spec=self.risk_spec,
            search_space=search_space if search_space is not None else self.search_space,
            frontier=frontier if frontier is not None else self.frontier,
            objective_contract_path=self.contract_path,
            risk_spec_path=self.risk_spec_path,
            search_space_path=self.search_space_path,
        )

    def test_valid_frontier_passes(self) -> None:
        result = self._validate()
        self.assertEqual("PASS", result["status"], msg=str(result["errors"]))
        self.assertEqual(0, result["error_count"])

    def test_d_grade_parameter_in_realistic_search_space_fails(self) -> None:
        target_parameter = self.search_space["parameters_considered"][0]["parameter_id"]
        bad_claims = copy.deepcopy(self.parameter_claims)
        for claim in bad_claims["claims"]:
            if claim.get("parameter_id") == target_parameter:
                claim["trust_grade"] = "D"
                claim["mode"] = "realistic"
                break

        result = self._validate(claims=bad_claims)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("trust" in error for error in result["errors"]),
            msg=str(result["errors"]),
        )

    def test_missing_objective_contract_reference_fails(self) -> None:
        bad_frontier = copy.deepcopy(self.frontier)
        bad_frontier["objective_contract_ref"] = "mission/objectives/missing_contract.json"

        result = self._validate(frontier=bad_frontier)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("objective_contract_ref" in error for error in result["errors"]),
            msg=str(result["errors"]),
        )

    def test_parameter_outside_bounds_fails(self) -> None:
        bad_frontier = copy.deepcopy(self.frontier)
        target_parameter = self.search_space["parameters_considered"][0]["parameter_id"]
        high_bound = float(self.search_space["parameters_considered"][0]["bounds"][1])
        bad_frontier["points"][0]["parameters"][target_parameter] = high_bound + 1.0

        result = self._validate(frontier=bad_frontier)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("outside bounds" in error for error in result["errors"]),
            msg=str(result["errors"]),
        )

    def test_internal_code_literal_in_excluded_parameters_fails(self) -> None:
        bad_search_space = copy.deepcopy(self.search_space)
        bad_search_space["excluded_parameters"].append(
            {
                "parameter_id": "code_literal.synthetic.module.literal_0",
                "exclusion_reason": ["synthetic"],
                "trust_grade": "C",
                "domain": "realistic",
            }
        )

        result = self._validate(search_space=bad_search_space)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("must not publish internal code literal" in error for error in result["errors"]),
            msg=str(result["errors"]),
        )

    def test_registry_internal_parameter_in_search_space_fails_without_prefix_dependency(self) -> None:
        target_parameter = self.search_space["parameters_considered"][0]["parameter_id"]
        bad_registry = copy.deepcopy(self.parameter_registry)
        for entry in bad_registry["parameters"]:
            if entry.get("parameter_id") == target_parameter:
                entry["visibility"] = "internal"
                entry["public_surfaces"] = []
                entry["audit_scope"] = "code_literal"
                break

        result = self._validate(parameter_registry=bad_registry)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("registry visibility" in error for error in result["errors"]),
            msg=str(result["errors"]),
        )

    def test_search_space_builder_excludes_registry_internal_parameter_without_prefix_dependency(self) -> None:
        registry = {
            "parameters": [
                {
                    "parameter_id": "mission_public.value",
                    "visibility": "public",
                    "public_surfaces": ["browser", "optimization"],
                    "audit_scope": "mission_parameter",
                    "affects_core_probability": True,
                    "domain": "realistic",
                    "bounds": [0.0, 2.0],
                },
                {
                    "parameter_id": "mission_internal.value",
                    "visibility": "internal",
                    "public_surfaces": [],
                    "audit_scope": "code_literal",
                    "affects_core_probability": True,
                    "domain": "realistic",
                    "bounds": [0.0, 2.0],
                },
            ]
        }
        claims = {
            "claims": [
                {"parameter_id": "mission_public.value", "trust_grade": "A", "mode": "realistic"},
                {"parameter_id": "mission_internal.value", "trust_grade": "A", "mode": "realistic"},
            ]
        }
        baseline = {
            "mission_public": {"value": 1.0},
            "mission_internal": {"value": 1.0},
        }

        search_space = build_optimization_frontier._search_space(
            baseline=baseline,
            parameter_registry=registry,
            parameter_claims=claims,
            mode="realistic",
            seed=1,
        )

        self.assertEqual(
            ["mission_public.value"],
            [item["parameter_id"] for item in search_space["parameters_considered"]],
        )
        self.assertEqual([], search_space["excluded_parameters"])
        self.assertEqual(1, search_space["excluded_internal_parameter_count"])

    def test_frontier_order_tamper_fails_determinism_check(self) -> None:
        bad_frontier = copy.deepcopy(self.frontier)
        bad_frontier["points"] = list(reversed(bad_frontier["points"]))

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
            json.dump(bad_frontier, handle, indent=2, sort_keys=True)
            handle.write("\n")
            bad_path = Path(handle.name)

        try:
            process = subprocess.run(
                [
                    sys.executable,
                    "scripts/ci/optimization_frontier_validate.py",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--strict",
                    "--frontier",
                    str(bad_path),
                    "--format",
                    "text",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(2, process.returncode, msg=process.stdout + process.stderr)
            self.assertIn("determinism mismatch", process.stdout)
        finally:
            bad_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
