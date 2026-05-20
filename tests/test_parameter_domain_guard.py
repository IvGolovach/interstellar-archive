from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
import unittest

from scripts.ci import parameter_domain_guard


REPO_ROOT = Path(__file__).resolve().parents[1]


class ParameterDomainGuardTests(unittest.TestCase):
    def test_current_domain_guard_passes(self) -> None:
        result = parameter_domain_guard.run_guard(
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

    def test_trust_d_on_realistic_domain_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            for rel in [
                "parameters/registry/parameter_registry.v1.json",
                "parameters/registry/parameter_claims.v1.json",
                "mission/BASELINE_SCENARIO_v1.json",
                "mission/baseline/__init__.py",
                "mission/baseline/core.py",
                "scripts/mission_baseline_check.py",
            ]:
                src = REPO_ROOT / rel
                dst = tmp / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)

            registry_path = tmp / "parameters/registry/parameter_registry.v1.json"
            claims_path = tmp / "parameters/registry/parameter_claims.v1.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            claims = json.loads(claims_path.read_text(encoding="utf-8"))

            target_id = "bh_parameters.mass_kg"
            for item in registry["parameters"]:
                if item["parameter_id"] == target_id:
                    item["domain"] = "realistic"
                    break
            for claim in claims["claims"]:
                if claim["parameter_id"] == target_id:
                    claim["trust_grade"] = "D"
                    claim["mode"] = "realistic"
                    break

            registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            result = parameter_domain_guard.run_guard(
                repo_root=tmp,
                parameter_registry_path=Path("parameters/registry/parameter_registry.v1.json"),
                parameter_claims_path=Path("parameters/registry/parameter_claims.v1.json"),
                scenario_path=Path("mission/BASELINE_SCENARIO_v1.json"),
                mission_script_path=Path("scripts/mission_baseline_check.py"),
                divergence_threshold=20.0,
            )
            self.assertEqual("FAIL", result["status"])
            self.assertTrue(any("trust D" in err for err in result["errors"]))


if __name__ == "__main__":
    unittest.main()
