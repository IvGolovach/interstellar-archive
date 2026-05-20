from __future__ import annotations

import json
from pathlib import Path
import unittest

from mission.guards import run_guard, validate_plan


REPO_ROOT = Path(__file__).resolve().parents[1]


class MissionGuardsTests(unittest.TestCase):
    def test_parameter_domain_guard_public_api_passes(self) -> None:
        result = run_guard(
            repo_root=REPO_ROOT,
            parameter_registry_path=Path("parameters/registry/parameter_registry.v1.json"),
            parameter_claims_path=Path("parameters/registry/parameter_claims.v1.json"),
            scenario_path=Path("mission/BASELINE_SCENARIO_v1.json"),
            mission_script_path=Path("scripts/mission_baseline_check.py"),
            divergence_threshold=20.0,
        )
        self.assertEqual("PASS", result["status"], result)
        self.assertTrue(result["realistic_mode_verified"])
        self.assertTrue(result["speculative_mode_enabled"])

    def test_optimization_guard_public_api_passes(self) -> None:
        plan = json.loads((REPO_ROOT / "mission/OPTIMIZATION_PLAN_v1.json").read_text(encoding="utf-8"))
        registry = json.loads((REPO_ROOT / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))
        claims = json.loads((REPO_ROOT / "parameters/registry/parameter_claims.v1.json").read_text(encoding="utf-8"))
        result = validate_plan(plan, registry, claims)
        self.assertEqual("PASS", result["status"], result)


if __name__ == "__main__":
    unittest.main()
