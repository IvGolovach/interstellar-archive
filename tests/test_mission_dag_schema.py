from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci import mission_dag_validate


REPO_ROOT = Path(__file__).resolve().parents[1]


class MissionDagSchemaTests(unittest.TestCase):
    def test_default_contracts_validate(self) -> None:
        result = mission_dag_validate.run_validation(
            repo_root=REPO_ROOT,
            scenario_path=Path("mission/dag/scenarios/mission_dag_baseline.v1.json"),
            module_registry_path=Path("mission/dag/registry/module_registry.v1.json"),
            failure_taxonomy_path=Path("mission/dag/registry/failure_taxonomy.v1.json"),
            artifacts_dir=None,
        )
        self.assertEqual("PASS", result["status"]) 

    def test_cycle_is_rejected(self) -> None:
        scenario_path = REPO_ROOT / "mission/dag/scenarios/mission_dag_baseline.v1.json"
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(scenario)

        for node in mutated["modules"]:
            if node["node_id"] == "traj":
                node["depends_on"] = ["data"]
                break

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "scenario.json"
            path.write_text(json.dumps(mutated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = mission_dag_validate.run_validation(
                repo_root=REPO_ROOT,
                scenario_path=path,
                module_registry_path=Path("mission/dag/registry/module_registry.v1.json"),
                failure_taxonomy_path=Path("mission/dag/registry/failure_taxonomy.v1.json"),
                artifacts_dir=None,
            )

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("cycle" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
