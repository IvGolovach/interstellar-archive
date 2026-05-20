from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
import unittest

from mission.user_runs.catalog import (
    SCHEMA_VERSION,
    build_user_mission_run_catalog,
    build_user_run_pack,
    validate_user_mission_run_catalog,
    validate_user_run_summary,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class UserMissionRunCatalogTests(unittest.TestCase):
    def test_committed_catalog_validates_and_exposes_default_run(self) -> None:
        payload = json.loads((REPO_ROOT / "artifacts" / "user_mission_run_catalog.v1.json").read_text(encoding="utf-8"))

        self.assertEqual([], validate_user_mission_run_catalog(payload))
        self.assertEqual(SCHEMA_VERSION, payload["schema_version"])
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(15, payload["run_count"])
        self.assertTrue(payload["default_run_id"].startswith("umr-reference-black-hole-conditional-45-"))

        default_row = next(row for row in payload["run_rows"] if row["run_id"] == payload["default_run_id"])
        self.assertEqual("reference-black-hole", default_row["selection"]["target_id"])
        self.assertEqual("conditional-45", default_row["selection"]["velocity_id"])
        self.assertEqual("scripts/run_user_mission_scenario.py", default_row["runtime_pack_template"]["script"])
        self.assertFalse(default_row["runtime_pack_template"]["writes_tracked_files"])
        self.assertIn("flight ready", default_row["blocked_claims"])

    def test_builder_is_deterministic(self) -> None:
        first = build_user_mission_run_catalog(REPO_ROOT)
        second = build_user_mission_run_catalog(REPO_ROOT)

        self.assertEqual(first, second)
        self.assertEqual([], validate_user_mission_run_catalog(first))

    def test_validator_rejects_contract_breaks(self) -> None:
        payload = build_user_mission_run_catalog(REPO_ROOT)
        cases = [
            ("non_certification_notice", lambda item: item.update({"non_certification_notice": False})),
            ("run_rows", lambda item: item.update({"run_rows": item["run_rows"][:-1]})),
            ("default_run_id", lambda item: item.update({"default_run_id": "umr-not-the-default"})),
            ("blocked_claims", lambda item: item["run_rows"][0].update({"blocked_claims": []})),
            (
                "runtime_pack_template",
                lambda item: item["run_rows"][0]["runtime_pack_template"].update({"writes_tracked_files": True}),
            ),
        ]
        for expected, mutate in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = validate_user_mission_run_catalog(broken)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_build_user_run_pack_executes_dag_and_validates_summary(self) -> None:
        payload = build_user_mission_run_catalog(REPO_ROOT)
        default_row = next(row for row in payload["run_rows"] if row["run_id"] == payload["default_run_id"])
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = build_user_run_pack(
                repo_root=REPO_ROOT,
                target_id=default_row["selection"]["target_id"],
                velocity_id=default_row["selection"]["velocity_id"],
                run_id="unit-user-mission-run-v1",
                mode="dual",
                seed=1,
                output_dir=Path(tmp_dir) / "unit-user-mission-run-v1",
            )

            summary = result["summary"]
            self.assertEqual([], validate_user_run_summary(summary))
            self.assertEqual("PASS", summary["dag_execution"]["status"])
            self.assertEqual("PASS", summary["dag_execution"]["hashchain_status"])
            self.assertEqual("PASS", summary["dag_execution"]["determinism_verdict"])
            self.assertEqual(12, summary["dag_execution"]["module_artifact_count"])
            self.assertTrue((Path(result["output_dir"]) / "COMPILED_MISSION_SCENARIO.json").exists())
            self.assertTrue((Path(result["output_dir"]) / "mission_dag" / "manifest.json").exists())
            self.assertEqual(
                {
                    "COMPILED_MISSION_SCENARIO.json",
                    "DAG_RUN_SUMMARY.json",
                    "RUN_REPORT.md",
                    "SOURCE_MANIFEST.json",
                    "USER_RUN_SUMMARY.json",
                    "meta.json",
                },
                {path.name for path in Path(result["output_dir"]).iterdir() if path.is_file()},
            )
            source_manifest = json.loads((Path(result["output_dir"]) / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
            source_paths = {entry["path"] for entry in source_manifest["source_manifest"]}
            self.assertIn("scripts/run_user_mission_scenario.py", source_paths)
            self.assertIn("scripts/ci/user_mission_run_pack_validate.py", source_paths)
            self.assertIn("mission/MISSION_SCHEMA_v1.json", source_paths)


if __name__ == "__main__":
    unittest.main()
