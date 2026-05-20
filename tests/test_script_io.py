from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from script_io import load_json, render_json, render_output, write_json, write_text


MIGRATED_FILES = [
    Path("scripts/build_browser_dataset_artifact.py"),
    Path("scripts/build_failure_surface_artifacts.py"),
    Path("scripts/build_objective_artifacts.py"),
    Path("scripts/build_optimization_frontier.py"),
    Path("scripts/build_parameter_drilldown_artifacts.py"),
    Path("scripts/build_parameter_dynamic_trace_index.py"),
    Path("scripts/optimization_guard.py"),
    Path("scripts/run_mission_dag.py"),
    Path("scripts/run_optimization.py"),
    Path("scripts/benchmark_compare.py"),
    Path("scripts/benchmark_drift_guard.py"),
    Path("scripts/build_evidence_status.py"),
    Path("scripts/build_research_signals.py"),
    Path("scripts/ci/browser_dataset_validate.py"),
    Path("scripts/ci/artifact_determinism_validate.py"),
    Path("scripts/ci/defensibility_validate.py"),
    Path("scripts/ci/dag_dependency_graph.py"),
    Path("scripts/ci/evidence_validate.py"),
    Path("scripts/ci/evidence_sync_validate.py"),
    Path("scripts/ci/failure_surface_validate.py"),
    Path("scripts/ci/governance_check.py"),
    Path("scripts/ci/mission_dag_validate.py"),
    Path("scripts/ci/objective_contract_validate.py"),
    Path("scripts/ci/evidence_coverage.py"),
    Path("scripts/ci/governance_coverage.py"),
    Path("scripts/ci/mission_dag_coverage.py"),
    Path("scripts/ci/optimization_coverage.py"),
    Path("scripts/ci/optimization_frontier_validate.py"),
    Path("scripts/ci/parameter_dynamic_static_check.py"),
    Path("scripts/ci/parameter_domain_guard.py"),
    Path("scripts/ci/parameter_evidence_validate.py"),
    Path("scripts/ci/parameter_literal_scan.py"),
    Path("scripts/ci/parameter_registry_validate.py"),
    Path("scripts/ci/parameter_sensitivity_report.py"),
    Path("scripts/ci/remote_branch_web_validate.py"),
    Path("scripts/ci/remote_ci_web_validate.py"),
    Path("scripts/ci/remote_proof_aggregate.py"),
    Path("scripts/ci/remote_proof_contract.py"),
    Path("scripts/ci/repo_root_guard.py"),
    Path("scripts/ci/risk_envelope_validate.py"),
    Path("scripts/ci/version_contract_validate.py"),
]


class ScriptIoTests(unittest.TestCase):
    def test_write_json_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "nested" / "payload.json"
            payload = {"b": 2, "a": [1, 2, 3]}

            write_json(path, payload)

            self.assertEqual(payload, load_json(path))
            self.assertTrue(path.read_text(encoding="utf-8").endswith("\n"))

    def test_render_output_switches_between_json_and_text(self) -> None:
        payload = {"status": "PASS", "value": 1}

        rendered_json = render_output(payload, output_format="json", text_renderer=lambda _: "text")
        rendered_text = render_output(payload, output_format="text", text_renderer=lambda item: item["status"])

        self.assertEqual(payload, json.loads(rendered_json))
        self.assertEqual("PASS", rendered_text)

    def test_write_text_adds_trailing_newline_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "report.txt"

            write_text(path, "hello")
            self.assertEqual("hello\n", path.read_text(encoding="utf-8"))

            write_text(path, "hello\n")
            self.assertEqual("hello\n", path.read_text(encoding="utf-8"))

    def test_render_json_matches_expected_shape(self) -> None:
        rendered = render_json({"b": 1, "a": 2})
        self.assertEqual({"a": 2, "b": 1}, json.loads(rendered))

    def test_migrated_scripts_do_not_define_local_json_helpers(self) -> None:
        offenders: list[str] = []
        for rel_path in MIGRATED_FILES:
            text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            if "def _load_json(" in text or "def _write_json(" in text:
                offenders.append(str(rel_path))

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
