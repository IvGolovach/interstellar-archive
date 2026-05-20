from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from mission.baseline import build_output, load_claims_map, schwarzschild_radius_m
from mission.dag import contracts
from mission.dag.runner_v1 import (
    ModuleContext,
    RunnerConfig,
    execute,
    run_data_integrity_module,
    run_trajectory_module,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class MissionDagRunnerBranchTests(unittest.TestCase):
    def _run_with_scenario(self, scenario_payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scenario_path = Path(tmp_dir) / "scenario.json"
            scenario_path.write_text(json.dumps(scenario_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = execute(
                RunnerConfig(
                    repo_root=REPO_ROOT,
                    dag_scenario_path=REPO_ROOT / "mission/dag/scenarios/mission_dag_baseline.v1.json",
                    mission_scenario_path=scenario_path,
                    mode="realistic",
                    seed=1,
                    output_dir=Path(tmp_dir) / "run",
                    verify_deterministic=False,
                )
            )
            self.assertIn("primary", result)
            return result

    def test_trajectory_failure_path(self) -> None:
        scenario = json.loads((REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json").read_text(encoding="utf-8"))
        r_s = schwarzschild_radius_m(float(scenario["bh_parameters"]["mass_kg"]))
        scenario["bh_parameters"]["periapsis_distance_m"] = float(r_s * 1.01)
        claims_map = load_claims_map(REPO_ROOT)
        mission_output = build_output(
            scenario,
            mode="realistic",
            claims_map=claims_map,
        )
        taxonomy = contracts.load_json(REPO_ROOT / "mission/dag/registry/failure_taxonomy.v1.json")
        taxonomy_by_id = contracts.taxonomy_map(taxonomy)
        outputs, failure = run_trajectory_module(
            ModuleContext(
                node_id="traj",
                module_id="traj.baseline.v1",
                module_type="TrajectoryModule",
                mode="realistic",
                seed=1,
                mission_scenario=scenario,
                mission_output=mission_output,
                upstream_outputs={},
            ),
            taxonomy_by_id,
        )
        self.assertFalse(outputs["crossing_condition_met"])
        self.assertEqual("FAIL", failure["status"])
        self.assertEqual("MISS_DISTANCE_EXCEEDS_R_INT", failure["failure_mode"])

    def test_environment_and_thermal_failure_paths(self) -> None:
        scenario = json.loads((REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json").read_text(encoding="utf-8"))
        scenario["environment_model"]["radiative_flux_w_m2"] = scenario["bh_parameters"]["max_radiative_flux_w_m2"] * 2.0
        scenario["environment_model"]["plasma_density_proxy_m3"] = scenario["bh_parameters"]["max_plasma_density_proxy_m3"] * 2.0
        result = self._run_with_scenario(scenario)
        used = result["primary"]["failure_taxonomy_coverage"]["used_failure_ids"]
        self.assertIn("PLASMA_ENVIRONMENT_DISQUALIFIED", used)
        self.assertIn("TPS_FAIL_DELAMINATION", used)

    def test_control_window_failure_path(self) -> None:
        scenario = json.loads((REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json").read_text(encoding="utf-8"))
        scenario["correction_window"]["guidance_sigma_rad"] = 0.1
        scenario["correction_window"]["delta_v_budget_mps"] = 0.01
        result = self._run_with_scenario(scenario)
        used = result["primary"]["failure_taxonomy_coverage"]["used_failure_ids"]
        self.assertIn("CONTROL_AUTHORITY_COLLAPSE", used)

    def test_data_integrity_failure_path(self) -> None:
        scenario = json.loads((REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json").read_text(encoding="utf-8"))
        scenario["capsule_model"]["data_media_survival_margin"] = 0.05
        scenario["environment_model"]["radiative_flux_w_m2"] = scenario["bh_parameters"]["max_radiative_flux_w_m2"]
        result = self._run_with_scenario(scenario)
        used = result["primary"]["failure_taxonomy_coverage"]["used_failure_ids"]
        self.assertIn("DATA_CORRUPTION_RADIATION", used)

    def test_data_integrity_module_reports_degradation_driver(self) -> None:
        scenario = json.loads((REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json").read_text(encoding="utf-8"))
        scenario["capsule_model"]["data_media_survival_margin"] = 0.05
        scenario["environment_model"]["radiative_flux_w_m2"] = scenario["bh_parameters"]["max_radiative_flux_w_m2"]
        claims_map = load_claims_map(REPO_ROOT)
        mission_output = build_output(
            scenario,
            mode="realistic",
            claims_map=claims_map,
        )
        taxonomy = contracts.load_json(REPO_ROOT / "mission/dag/registry/failure_taxonomy.v1.json")
        taxonomy_by_id = contracts.taxonomy_map(taxonomy)
        outputs, failure = run_data_integrity_module(
            ModuleContext(
                node_id="data",
                module_id="data.baseline.v1",
                module_type="DataIntegrityModule",
                mode="realistic",
                seed=1,
                mission_scenario=scenario,
                mission_output=mission_output,
                upstream_outputs={},
            ),
            taxonomy_by_id,
        )
        self.assertLess(outputs["p_data_intact"], 0.5)
        self.assertEqual("FAIL", failure["status"])
        self.assertEqual("DATA_CORRUPTION_RADIATION", failure["failure_mode"])
        self.assertEqual(
            [
                "capsule_model.data_media_survival_margin",
                "capsule_model.material_degradation_mu_1_per_year",
                "environment_model.radiative_flux_w_m2",
            ],
            failure["dominant_driver_parameter_ids"],
        )


if __name__ == "__main__":
    unittest.main()
