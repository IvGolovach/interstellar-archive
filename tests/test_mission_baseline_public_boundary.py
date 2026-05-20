from __future__ import annotations

import ast
import json
import subprocess
import unittest
from pathlib import Path

from mission.baseline import REQUIRED_OUTPUTS, build_output, load_claims_map


REPO_ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_SCAN_ROOTS = ("mission", "scripts", "tests")
BOUNDARY_SCAN_EXCLUDED = {
    Path("scripts/mission_baseline_check.py"),
    Path("tests/test_mission_baseline_public_boundary.py"),
}


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in BOUNDARY_SCAN_ROOTS:
        for path in (REPO_ROOT / root).rglob("*.py"):
            rel_path = path.relative_to(REPO_ROOT)
            if rel_path in BOUNDARY_SCAN_EXCLUDED:
                continue
            files.append(path)
    return sorted(files)


def _find_cli_import_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"mission_baseline_check", "scripts.mission_baseline_check"}:
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "scripts" and any(alias.name == "mission_baseline_check" for alias in node.names):
                violations.append("from scripts import mission_baseline_check")
            if node.module == "scripts.mission_baseline_check":
                violations.append("from scripts.mission_baseline_check import ...")
    return violations


class MissionBaselinePublicBoundaryTests(unittest.TestCase):
    def test_public_baseline_api_builds_required_outputs(self) -> None:
        scenario = json.loads((REPO_ROOT / "mission/BASELINE_SCENARIO_v1.json").read_text(encoding="utf-8"))
        claims_map = load_claims_map(REPO_ROOT)

        output = build_output(scenario, mode="realistic", claims_map=claims_map)

        self.assertTrue(REQUIRED_OUTPUTS.issubset(output.keys()))
        self.assertEqual([], output.get("speculative_parameters_used"))

    def test_repo_modules_do_not_import_cli_wrapper(self) -> None:
        violations: list[str] = []
        for path in _iter_python_files():
            found = _find_cli_import_violations(path)
            violations.extend(f"{path.relative_to(REPO_ROOT)}: {item}" for item in found)

        self.assertEqual([], violations)

    def test_cli_wrapper_still_executes_validate_only(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/mission_baseline_check.py", "--validate-only"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("PASS: mission schema and baseline scenario validation", result.stdout)


if __name__ == "__main__":
    unittest.main()
