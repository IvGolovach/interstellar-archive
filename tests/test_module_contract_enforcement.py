from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mission.dag import contracts
from mission.dag.runner_v1 import RunnerConfig, execute


REPO_ROOT = Path(__file__).resolve().parents[1]


class ModuleContractEnforcementTests(unittest.TestCase):
    def test_all_module_outputs_validate_against_contract(self) -> None:
        taxonomy = contracts.load_json(REPO_ROOT / "mission/dag/registry/failure_taxonomy.v1.json")
        taxonomy_by_id = contracts.taxonomy_map(taxonomy)

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
                )
            )
            run_dir = Path(tmp_dir) / "run"
            for rel_path in run["primary"]["module_artifacts"]:
                payload = json.loads((run_dir / rel_path).read_text(encoding="utf-8"))
                errors = contracts.validate_module_output(payload, taxonomy_by_id)
                self.assertEqual([], errors, msg=f"{rel_path}: {errors}")


if __name__ == "__main__":
    unittest.main()
