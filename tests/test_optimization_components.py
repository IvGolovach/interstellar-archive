from __future__ import annotations

import json
from pathlib import Path
import unittest

from mission.optimization import constraints, scoring
from mission.optimization.search_space import resolve_search_space, apply_parameter_values


REPO_ROOT = Path(__file__).resolve().parents[1]


class OptimizationComponentsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = json.loads((REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json").read_text(encoding="utf-8"))
        self.registry = json.loads((REPO_ROOT / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))
        self.claims = json.loads((REPO_ROOT / "parameters/registry/parameter_claims.v1.json").read_text(encoding="utf-8"))

    def test_resolve_search_space_accepts_realistic_candidates(self) -> None:
        result = resolve_search_space(
            scenario=self.scenario,
            parameter_registry=self.registry,
            parameter_claims=self.claims,
            mode="realistic",
            candidate_ids=["bh_parameters.mass_kg", "bh_parameters.periapsis_distance_m"],
        )
        self.assertEqual("realistic", result.mode)
        self.assertEqual(2, len(result.parameters))
        self.assertEqual([], [item.to_dict() for item in result.rejected])

    def test_resolve_search_space_requires_realistic_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "mode=realistic"):
            resolve_search_space(
                scenario=self.scenario,
                parameter_registry=self.registry,
                parameter_claims=self.claims,
                mode="speculative",
                candidate_ids=["bh_parameters.mass_kg"],
            )

    def test_resolve_search_space_rejects_missing_neutral(self) -> None:
        registry = json.loads(json.dumps(self.registry))
        for item in registry["parameters"]:
            if item.get("parameter_id") == "bh_parameters.mass_kg":
                item["realistic_neutral_value"] = None
                break

        with self.assertRaisesRegex(ValueError, "empty"):
            resolve_search_space(
                scenario=self.scenario,
                parameter_registry=registry,
                parameter_claims=self.claims,
                mode="realistic",
                candidate_ids=["bh_parameters.mass_kg"],
            )

    def test_resolve_search_space_rejects_bad_dependencies(self) -> None:
        registry = json.loads(json.dumps(self.registry))
        for item in registry["parameters"]:
            if item.get("parameter_id") == "bh_parameters.mass_kg":
                item["dependencies"] = ["trajectory_model.non_physical_capture_bias"]
                break

        with self.assertRaisesRegex(ValueError, "empty"):
            resolve_search_space(
                scenario=self.scenario,
                parameter_registry=registry,
                parameter_claims=self.claims,
                mode="realistic",
                candidate_ids=["bh_parameters.mass_kg"],
            )

    def test_apply_parameter_values_updates_scenario(self) -> None:
        updated = apply_parameter_values(self.scenario, {"bh_parameters.mass_kg": 1.23e31})
        self.assertNotEqual(self.scenario["bh_parameters"]["mass_kg"], updated["bh_parameters"]["mass_kg"])
        self.assertEqual(1.23e31, updated["bh_parameters"]["mass_kg"])

    def test_constraints_and_scoring(self) -> None:
        scenario = json.loads(json.dumps(self.scenario))
        output = {
            "crossing_condition_met": False,
            "environment_acceptable": False,
            "p_survive": 0.7,
            "p_data_intact": 0.8,
        }
        hard = constraints.evaluate_hard_constraints(scenario, output)
        self.assertIn("horizon_crossing_not_met", hard)
        self.assertIn("environment_filter_rejected", hard)

        scenario["correction_window"]["end_year"] = scenario["correction_window"]["start_year"] + scenario["correction_window"]["max_duration_years"] + 1
        soft = constraints.evaluate_soft_constraints(
            baseline_scenario=self.scenario,
            scenario=scenario,
            output={"p_survive": 0.8, "p_data_intact": 0.9},
        )
        self.assertGreaterEqual(float(soft["penalty"]), 0.0)

        summary = constraints.summarize_constraint_violations(
            [
                {"hard_violations": ["horizon_crossing_not_met"], "soft_violations": ["power_above_baseline"]},
                {"hard_violations": ["horizon_crossing_not_met"], "soft_violations": []},
            ]
        )
        self.assertEqual(2, summary["hard"]["horizon_crossing_not_met"])

        candidate = {
            "candidate_id": "x",
            "hard_feasible": True,
            "core_probability": 0.3,
            "trust_weighted_score": 0.2,
            "risk_metric": 0.1,
            "penalty": 0.05,
        }
        self.assertIsInstance(scoring.composite_score(candidate), float)
        self.assertEqual("x", scoring.ranking_record(candidate)["candidate_id"])


if __name__ == "__main__":
    unittest.main()
