from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mission.dag.runner_v1 import RunnerConfig, execute
from scripts.ci import mission_dag_validate


REPO_ROOT = Path(__file__).resolve().parents[1]


class MissionDagDeterminismTests(unittest.TestCase):
    def test_verify_deterministic_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = execute(
                RunnerConfig(
                    repo_root=REPO_ROOT,
                    dag_scenario_path=REPO_ROOT / "mission/dag/scenarios/mission_dag_baseline.v1.json",
                    mission_scenario_path=REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json",
                    mode="dual",
                    seed=1,
                    output_dir=Path(tmp_dir) / "run-a",
                    verify_deterministic=True,
                )
            )

        self.assertEqual("PASS", result["status"])
        self.assertEqual("PASS", result["determinism"]["verdict"])
        self.assertTrue(result["determinism"]["same_seed_match"])
        self.assertTrue(result["determinism"]["different_seed_differs"])

    def test_different_seed_changes_manifest_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_a = execute(
                RunnerConfig(
                    repo_root=REPO_ROOT,
                    dag_scenario_path=REPO_ROOT / "mission/dag/scenarios/mission_dag_baseline.v1.json",
                    mission_scenario_path=REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json",
                    mode="dual",
                    seed=4,
                    output_dir=Path(tmp_dir) / "run-a",
                    verify_deterministic=False,
                )
            )
            run_b = execute(
                RunnerConfig(
                    repo_root=REPO_ROOT,
                    dag_scenario_path=REPO_ROOT / "mission/dag/scenarios/mission_dag_baseline.v1.json",
                    mission_scenario_path=REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json",
                    mode="dual",
                    seed=5,
                    output_dir=Path(tmp_dir) / "run-b",
                    verify_deterministic=False,
                )
            )

        hash_a = run_a["primary"]["manifest"]["manifest_hash"]
        hash_b = run_b["primary"]["manifest"]["manifest_hash"]
        self.assertNotEqual(hash_a, hash_b)

    def test_hashchain_tamper_is_detected(self) -> None:
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
            first_rel = run["primary"]["module_artifacts"][0]
            module_path = run_dir / first_rel
            payload = json.loads(module_path.read_text(encoding="utf-8"))
            payload["outputs"]["tampered"] = True
            module_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            validation = mission_dag_validate.run_validation(
                repo_root=REPO_ROOT,
                scenario_path=Path("mission/dag/scenarios/mission_dag_baseline.v1.json"),
                module_registry_path=Path("mission/dag/registry/module_registry.v1.json"),
                failure_taxonomy_path=Path("mission/dag/registry/failure_taxonomy.v1.json"),
                artifacts_dir=run_dir,
            )

        self.assertEqual("FAIL", validation["status"])
        self.assertTrue(
            any("hash" in error for error in validation["errors"]),
            msg=str(validation["errors"]),
        )


if __name__ == "__main__":
    unittest.main()
