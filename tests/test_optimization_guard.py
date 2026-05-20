from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import optimization_guard


REPO_ROOT = Path(__file__).resolve().parents[1]


class OptimizationGuardTests(unittest.TestCase):
    def _load(self) -> tuple[dict, dict, dict]:
        plan = json.loads((REPO_ROOT / "mission/OPTIMIZATION_PLAN_v1.json").read_text(encoding="utf-8"))
        registry = json.loads((REPO_ROOT / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))
        claims = json.loads((REPO_ROOT / "parameters/registry/parameter_claims.v1.json").read_text(encoding="utf-8"))
        return plan, registry, claims

    def test_current_plan_passes(self) -> None:
        plan, registry, claims = self._load()
        result = optimization_guard.validate_plan(plan, registry, claims)
        self.assertEqual("PASS", result["status"], result)

    def test_speculative_parameter_in_plan_fails(self) -> None:
        plan, registry, claims = self._load()
        plan["tuned_parameters"] = ["trajectory_model.non_physical_capture_bias"]
        result = optimization_guard.validate_plan(plan, registry, claims)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("realistic domain" in err for err in result["errors"]))


if __name__ == "__main__":
    unittest.main()
