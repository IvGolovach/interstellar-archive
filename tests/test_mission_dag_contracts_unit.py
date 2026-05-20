from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from mission.dag import contracts


REPO_ROOT = Path(__file__).resolve().parents[1]


class MissionDagContractsUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = contracts.load_json(REPO_ROOT / "mission/dag/registry/module_registry.v1.json")
        self.taxonomy = contracts.load_json(REPO_ROOT / "mission/dag/registry/failure_taxonomy.v1.json")
        self.scenario = contracts.load_json(REPO_ROOT / "mission/dag/scenarios/mission_dag_baseline.v1.json")

    def test_failure_taxonomy_validation_rejects_invalid_shape(self) -> None:
        bad = copy.deepcopy(self.taxonomy)
        bad["failure_modes"][0]["stage"] = "S9"
        bad["failure_modes"][0]["severity"] = "fatal"
        errors = contracts.validate_failure_taxonomy(bad)
        self.assertTrue(errors)

    def test_failure_taxonomy_requires_non_empty_list(self) -> None:
        bad = {"taxonomy_version": "v1", "failure_modes": []}
        errors = contracts.validate_failure_taxonomy(bad)
        self.assertTrue(any("non-empty list" in item for item in errors))

    def test_module_registry_validation_rejects_invalid_entrypoint(self) -> None:
        bad = copy.deepcopy(self.registry)
        bad["modules"][0]["implemented_by"]["python_entrypoint"] = "missing_file.py:run"
        errors = contracts.validate_module_registry(bad, repo_root=REPO_ROOT)
        self.assertTrue(any("file missing" in item for item in errors), msg=str(errors))

    def test_module_registry_validation_rejects_invalid_core_fields(self) -> None:
        bad = copy.deepcopy(self.registry)
        bad["modules"][0]["module_type"] = "BadModule"
        bad["modules"][0]["module_version"] = "v2"
        bad["modules"][0]["domain"] = "both"
        bad["modules"][0]["implemented_by"]["python_entrypoint"] = "entrypoint"
        errors = contracts.validate_module_registry(bad, repo_root=REPO_ROOT)
        self.assertTrue(any("module_type" in item for item in errors), msg=str(errors))
        self.assertTrue(any("module_version" in item for item in errors), msg=str(errors))
        self.assertTrue(any("domain" in item for item in errors), msg=str(errors))
        self.assertTrue(any("python_entrypoint" in item for item in errors), msg=str(errors))

    def test_module_registry_requires_list(self) -> None:
        bad = {"registry_version": "v1", "modules": {}}
        errors = contracts.validate_module_registry(bad, repo_root=REPO_ROOT)
        self.assertTrue(any("must be a non-empty list" in item for item in errors), msg=str(errors))

    def test_scenario_validation_rejects_missing_dependency(self) -> None:
        bad = copy.deepcopy(self.scenario)
        bad["modules"][1]["depends_on"] = ["missing-node"]
        errors = contracts.validate_scenario_dag(bad, self.registry)
        self.assertTrue(any("missing node" in item for item in errors), msg=str(errors))

    def test_module_output_validation_rejects_unknown_failure_mode(self) -> None:
        taxonomy_by_id = contracts.taxonomy_map(self.taxonomy)
        payload = {
            "module_id": "traj.baseline.v1",
            "module_type": "TrajectoryModule",
            "module_version": "v1",
            "mode": "realistic",
            "inputs_hash": "0" * 64,
            "outputs_hash": "0" * 64,
            "event_clock_domain": "event",
            "wall_clock_recorded": True,
            "outputs": {"x": 1},
            "failure": {
                "status": "FAIL",
                "failure_mode": "UNKNOWN",
                "failure_stage": "S1",
                "dominant_driver_parameter_ids": ["a"],
                "notes": "forced",
            },
        }
        errors = contracts.validate_module_output(payload, taxonomy_by_id)
        self.assertTrue(any("unknown failure_mode" in item for item in errors), msg=str(errors))

    def test_module_output_validation_rejects_invalid_failure_block(self) -> None:
        taxonomy_by_id = contracts.taxonomy_map(self.taxonomy)
        payload = {
            "module_id": "traj.baseline.v1",
            "module_type": "TrajectoryModule",
            "module_version": "v1",
            "mode": "realistic",
            "inputs_hash": "0" * 64,
            "outputs_hash": "0" * 64,
            "event_clock_domain": "event",
            "wall_clock_recorded": True,
            "outputs": {"x": 1},
            "failure": [],
        }
        errors = contracts.validate_module_output(payload, taxonomy_by_id)
        self.assertTrue(any("failure must be object" in item for item in errors), msg=str(errors))

    def test_module_output_validation_reports_missing_fields(self) -> None:
        taxonomy_by_id = contracts.taxonomy_map(self.taxonomy)
        errors = contracts.validate_module_output({}, taxonomy_by_id)
        self.assertTrue(any("missing field: module_id" in item for item in errors), msg=str(errors))

    def test_module_output_validation_rejects_invalid_status_and_notes(self) -> None:
        taxonomy_by_id = contracts.taxonomy_map(self.taxonomy)
        outputs = {"x": 1}
        payload = {
            "module_id": "env.baseline.v1",
            "module_type": "EnvironmentModule",
            "module_version": "v1",
            "mode": "realistic",
            "inputs_hash": "7" * 64,
            "outputs_hash": contracts.sha256_hex(contracts.canonical_json(outputs)),
            "event_clock_domain": "event",
            "wall_clock_recorded": True,
            "outputs": outputs,
            "failure": {
                "status": "BROKEN",
                "failure_mode": None,
                "failure_stage": None,
                "dominant_driver_parameter_ids": "bad",
                "notes": 123,
            },
        }
        errors = contracts.validate_module_output(payload, taxonomy_by_id)
        self.assertTrue(any("failure.status" in item for item in errors), msg=str(errors))
        self.assertTrue(any("dominant_driver_parameter_ids" in item for item in errors), msg=str(errors))
        self.assertTrue(any("notes must be string" in item for item in errors), msg=str(errors))

    def test_module_output_validation_checks_pass_constraints(self) -> None:
        taxonomy_by_id = contracts.taxonomy_map(self.taxonomy)
        outputs = {"x": 1}
        payload = {
            "module_id": "traj.baseline.v1",
            "module_type": "TrajectoryModule",
            "module_version": "v1",
            "mode": "realistic",
            "inputs_hash": "0" * 64,
            "outputs_hash": contracts.sha256_hex(contracts.canonical_json(outputs)),
            "event_clock_domain": "event",
            "wall_clock_recorded": True,
            "outputs": outputs,
            "failure": {
                "status": "PASS",
                "failure_mode": "MISS_DISTANCE_EXCEEDS_R_INT",
                "failure_stage": "S1",
                "dominant_driver_parameter_ids": [],
                "notes": "bad",
            },
        }
        errors = contracts.validate_module_output(payload, taxonomy_by_id)
        self.assertTrue(any("must be null when status=PASS" in item for item in errors), msg=str(errors))

    def test_module_output_validation_rejects_stage_mismatch(self) -> None:
        taxonomy_by_id = contracts.taxonomy_map(self.taxonomy)
        outputs = {"x": 1}
        payload = {
            "module_id": "thermal.baseline.v1",
            "module_type": "ThermalModule",
            "module_version": "v1",
            "mode": "speculative",
            "inputs_hash": "1" * 64,
            "outputs_hash": contracts.sha256_hex(contracts.canonical_json(outputs)),
            "event_clock_domain": "event",
            "wall_clock_recorded": True,
            "outputs": outputs,
            "failure": {
                "status": "WARN",
                "failure_mode": "TPS_FAIL_DELAMINATION",
                "failure_stage": "S1",
                "dominant_driver_parameter_ids": ["environment_model.radiative_flux_w_m2"],
                "notes": "warn",
            },
        }
        errors = contracts.validate_module_output(payload, taxonomy_by_id)
        self.assertTrue(any("mismatch" in item for item in errors), msg=str(errors))

    def test_module_output_validation_rejects_outputs_hash_mismatch(self) -> None:
        taxonomy_by_id = contracts.taxonomy_map(self.taxonomy)
        payload = {
            "module_id": "data.baseline.v1",
            "module_type": "DataIntegrityModule",
            "module_version": "v1",
            "mode": "realistic",
            "inputs_hash": "2" * 64,
            "outputs_hash": "3" * 64,
            "event_clock_domain": "event",
            "wall_clock_recorded": True,
            "outputs": {"p_data_intact": 0.5},
            "failure": {
                "status": "FAIL",
                "failure_mode": "DATA_CORRUPTION_RADIATION",
                "failure_stage": "S3",
                "dominant_driver_parameter_ids": ["capsule_model.data_media_survival_margin"],
                "notes": "fail",
            },
        }
        errors = contracts.validate_module_output(payload, taxonomy_by_id)
        self.assertTrue(any("outputs_hash mismatch" in item for item in errors), msg=str(errors))

    def test_module_output_validation_rejects_taxonomy_module_mismatch(self) -> None:
        taxonomy_by_id = contracts.taxonomy_map(self.taxonomy)
        outputs = {"x": 1}
        payload = {
            "module_id": "env.baseline.v1",
            "module_type": "EnvironmentModule",
            "module_version": "v1",
            "mode": "realistic",
            "inputs_hash": "4" * 64,
            "outputs_hash": contracts.sha256_hex(contracts.canonical_json(outputs)),
            "event_clock_domain": "event",
            "wall_clock_recorded": True,
            "outputs": outputs,
            "failure": {
                "status": "WARN",
                "failure_mode": "DATA_CORRUPTION_RADIATION",
                "failure_stage": "S3",
                "dominant_driver_parameter_ids": ["x"],
                "notes": "mismatch",
            },
        }
        errors = contracts.validate_module_output(payload, taxonomy_by_id)
        self.assertTrue(any("does not apply" in item for item in errors), msg=str(errors))

    def test_module_output_validation_rejects_missing_outputs_mapping(self) -> None:
        taxonomy_by_id = contracts.taxonomy_map(self.taxonomy)
        payload = {
            "module_id": "env.baseline.v1",
            "module_type": "EnvironmentModule",
            "module_version": "v1",
            "mode": "realistic",
            "inputs_hash": "5" * 64,
            "outputs_hash": "6" * 64,
            "event_clock_domain": "event",
            "wall_clock_recorded": True,
            "outputs": [],
            "failure": {
                "status": "PASS",
                "failure_mode": None,
                "failure_stage": None,
                "dominant_driver_parameter_ids": [],
                "notes": "pass",
            },
        }
        errors = contracts.validate_module_output(payload, taxonomy_by_id)
        self.assertTrue(any("outputs must be object" in item for item in errors), msg=str(errors))

    def test_topological_order_reports_cycle_nodes(self) -> None:
        cycle = {
            "modules": [
                {"node_id": "a", "depends_on": ["c"]},
                {"node_id": "b", "depends_on": ["a"]},
                {"node_id": "c", "depends_on": ["b"]},
            ]
        }
        order, cycle_nodes = contracts.scenario_topological_order(cycle)
        self.assertEqual([], order)
        self.assertEqual(["a", "b", "c"], cycle_nodes)

    def test_scenario_validation_rejects_bad_top_level_fields(self) -> None:
        bad = {
            "scenario_id": "",
            "scenario_version": "v2",
            "mode": "broken",
            "seed": True,
            "modules": [],
            "outputs": {},
        }
        errors = contracts.validate_scenario_dag(bad, self.registry)
        self.assertTrue(any("scenario_version" in item for item in errors), msg=str(errors))
        self.assertTrue(any("mode" in item for item in errors), msg=str(errors))
        self.assertTrue(any("seed" in item for item in errors), msg=str(errors))

    def test_scenario_validation_rejects_non_object_outputs(self) -> None:
        bad = copy.deepcopy(self.scenario)
        bad["outputs"] = []
        errors = contracts.validate_scenario_dag(bad, self.registry)
        self.assertTrue(any("outputs must be object" in item for item in errors), msg=str(errors))

    def test_manifest_hash_is_stable(self) -> None:
        first = contracts.manifest_hash({"a": "1", "b": "2"})
        second = contracts.manifest_hash({"b": "2", "a": "1"})
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
