from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from mission.dag.runner_v1 import RunnerConfig, execute


REPO_ROOT = Path(__file__).resolve().parents[1]


class MissionDagModeIsolationTests(unittest.TestCase):
    def test_realistic_result_is_isolated_from_speculative_knobs(self) -> None:
        baseline_scenario = json.loads((REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json").read_text(encoding="utf-8"))
        speculative_scenario = copy.deepcopy(baseline_scenario)
        speculative_scenario["trajectory_model"]["non_physical_capture_bias"] = 0.2
        speculative_scenario["environment_model"]["non_physical_safety_multiplier"] = 1.25

        with tempfile.TemporaryDirectory() as tmp_dir:
            baseline_path = Path(tmp_dir) / "baseline.json"
            baseline_path.write_text(json.dumps(baseline_scenario, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            speculative_path = Path(tmp_dir) / "speculative.json"
            speculative_path.write_text(json.dumps(speculative_scenario, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            run_base = execute(
                RunnerConfig(
                    repo_root=REPO_ROOT,
                    dag_scenario_path=REPO_ROOT / "mission/dag/scenarios/mission_dag_baseline.v1.json",
                    mission_scenario_path=baseline_path,
                    mode="dual",
                    seed=1,
                    output_dir=Path(tmp_dir) / "run-base",
                    verify_deterministic=False,
                )
            )
            run_spec = execute(
                RunnerConfig(
                    repo_root=REPO_ROOT,
                    dag_scenario_path=REPO_ROOT / "mission/dag/scenarios/mission_dag_baseline.v1.json",
                    mission_scenario_path=speculative_path,
                    mode="dual",
                    seed=1,
                    output_dir=Path(tmp_dir) / "run-spec",
                    verify_deterministic=False,
                )
            )

        base_real = run_base["primary"]["mode_summaries"]["realistic"]["final_metrics"]["p_success"]
        spec_real = run_spec["primary"]["mode_summaries"]["realistic"]["final_metrics"]["p_success"]
        self.assertEqual(base_real, spec_real)

        base_spec = run_base["primary"]["mode_summaries"]["speculative"]["final_metrics"]["p_success"]
        spec_spec = run_spec["primary"]["mode_summaries"]["speculative"]["final_metrics"]["p_success"]
        self.assertNotEqual(base_spec, spec_spec)


if __name__ == "__main__":
    unittest.main()
