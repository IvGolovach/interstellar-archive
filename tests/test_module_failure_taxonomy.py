from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mission.dag.runner_v1 import RunnerConfig, execute


REPO_ROOT = Path(__file__).resolve().parents[1]


class ModuleFailureTaxonomyTests(unittest.TestCase):
    def test_forced_failure_uses_known_taxonomy_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run = execute(
                RunnerConfig(
                    repo_root=REPO_ROOT,
                    dag_scenario_path=REPO_ROOT / "mission/dag/scenarios/mission_dag_baseline.v1.json",
                    mission_scenario_path=REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json",
                    mode="dual",
                    seed=1,
                    output_dir=Path(tmp_dir) / "run",
                    verify_deterministic=False,
                    forced_failures={"thermal": "TPS_FAIL_DELAMINATION"},
                )
            )
            thermal_payload = json.loads(
                (Path(tmp_dir) / "run" / "modules" / "realistic" / "thermal.json").read_text(encoding="utf-8")
            )

        self.assertEqual("FAIL", thermal_payload["failure"]["status"])
        self.assertEqual("TPS_FAIL_DELAMINATION", thermal_payload["failure"]["failure_mode"])
        self.assertEqual("PASS", run["primary"]["failure_taxonomy_coverage"]["status"])

    def test_invalid_forced_failure_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                execute(
                    RunnerConfig(
                        repo_root=REPO_ROOT,
                        dag_scenario_path=REPO_ROOT / "mission/dag/scenarios/mission_dag_baseline.v1.json",
                        mission_scenario_path=REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json",
                        mode="dual",
                        seed=1,
                        output_dir=Path(tmp_dir) / "run",
                        verify_deterministic=False,
                        forced_failures={"thermal": "MISS_DISTANCE_EXCEEDS_R_INT"},
                    )
                )


if __name__ == "__main__":
    unittest.main()
