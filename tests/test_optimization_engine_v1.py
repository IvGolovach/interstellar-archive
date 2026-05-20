from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from mission.optimization.engine_v1 import OptimizationConfig
from mission.optimization import runner


REPO_ROOT = Path(__file__).resolve().parents[1]


class OptimizationEngineV1Tests(unittest.TestCase):
    def _context(
        self,
        *,
        scenario: Path | None = None,
        plan: Path | None = None,
        registry: Path | None = None,
        claims: Path | None = None,
    ) -> runner.RunContext:
        return runner.RunContext(
            repo_root=REPO_ROOT,
            scenario_path=scenario or (REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json"),
            plan_path=plan or (REPO_ROOT / "mission/OPTIMIZATION_PLAN_v1.json"),
            parameter_registry_path=registry or (REPO_ROOT / "parameters/registry/parameter_registry.v1.json"),
            parameter_claims_path=claims or (REPO_ROOT / "parameters/registry/parameter_claims.v1.json"),
        )

    def _config(self, seed: int = 42) -> OptimizationConfig:
        return OptimizationConfig(mode="realistic", samples=24, seed=seed, refine_top_k=4, refine_steps=2)

    def test_execute_and_write_produces_required_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "opt"
            result = runner.execute_and_write(
                context=self._context(),
                config=self._config(seed=42),
                output_dir=output_dir,
                run_id="test-run",
                verify_deterministic=True,
            )

            self.assertEqual("PASS", result["meta"]["verdict"], result)
            self.assertFalse(result["meta"]["speculative_used"])
            self.assertTrue(result["meta"]["domain_verified"])
            self.assertEqual("PASS", result["determinism"]["verdict"])
            self.assertEqual("PASS", result["negative_proof"]["verdict"])

            for name in runner.REQUIRED_ARTIFACT_FILES:
                self.assertTrue((output_dir / name).exists(), f"missing {name}")
            self.assertTrue((output_dir / "NEGATIVE_PROOF.md").exists())

    def test_same_seed_produces_identical_hash(self) -> None:
        result_a = runner._evaluate_once(self._context(), self._config(seed=42))  # pylint: disable=protected-access
        result_b = runner._evaluate_once(self._context(), self._config(seed=42))  # pylint: disable=protected-access
        self.assertEqual(result_a.pack_hash, result_b.pack_hash)

    def test_different_seed_changes_hash(self) -> None:
        result_a = runner._evaluate_once(self._context(), self._config(seed=42))  # pylint: disable=protected-access
        result_b = runner._evaluate_once(self._context(), self._config(seed=43))  # pylint: disable=protected-access
        self.assertNotEqual(result_a.pack_hash, result_b.pack_hash)

    def test_speculative_parameter_in_plan_is_rejected(self) -> None:
        plan = json.loads((REPO_ROOT / "mission/OPTIMIZATION_PLAN_v1.json").read_text(encoding="utf-8"))
        plan["tuned_parameters"] = list(plan.get("tuned_parameters", [])) + ["trajectory_model.non_physical_capture_bias"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            plan_path = Path(tmp_dir) / "bad_plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "optimization_guard failed"):
                runner._evaluate_once(self._context(plan=plan_path), self._config())  # pylint: disable=protected-access

    def test_d_grade_parameter_is_rejected(self) -> None:
        claims = json.loads((REPO_ROOT / "parameters/registry/parameter_claims.v1.json").read_text(encoding="utf-8"))
        target = "bh_parameters.mass_kg"
        for claim in claims["claims"]:
            if claim.get("parameter_id") == target:
                claim["trust_grade"] = "D"
                claim["mode"] = "realistic"
                break

        with tempfile.TemporaryDirectory() as tmp_dir:
            claims_path = Path(tmp_dir) / "claims.json"
            claims_path.write_text(json.dumps(claims), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "optimization_guard failed"):
                runner._evaluate_once(self._context(claims=claims_path), self._config())  # pylint: disable=protected-access


if __name__ == "__main__":
    unittest.main()
