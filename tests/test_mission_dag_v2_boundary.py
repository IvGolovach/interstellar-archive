from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts import build_mission_dag_v2_boundary_artifact
from scripts.ci.mission_dag_v2_boundary_validate import validate


REPO_ROOT = Path(__file__).resolve().parents[1]


class MissionDagV2BoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads((REPO_ROOT / "artifacts/mission_dag_v2_boundary.v1.json").read_text())

    def test_valid_payload_passes(self) -> None:
        result = validate(payload=self.payload, repo_root=REPO_ROOT)

        self.assertEqual("PASS", result["status"], msg=str(result["errors"]))
        self.assertEqual(0, result["error_count"])
        self.assertEqual(6, result["module_count"])

    def test_builder_matches_committed_artifact(self) -> None:
        built = build_mission_dag_v2_boundary_artifact.build_payload(repo_root=REPO_ROOT)

        self.assertEqual(self.payload, built)

    def test_backend_overclaim_fails(self) -> None:
        bad = copy.deepcopy(self.payload)
        bad["rollup"]["independent_backend_complete"] = True
        bad["blocked_claims"].remove("independent physics backend validated")

        result = validate(payload=bad, repo_root=REPO_ROOT)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("independent_backend_complete" in error for error in result["errors"]))
        self.assertTrue(any("blocked_claims" in error for error in result["errors"]))

    def test_missing_module_requirement_fails(self) -> None:
        bad = copy.deepcopy(self.payload)
        bad["module_boundaries"][0]["v2_boundary_requirements"].remove("state trace hash")

        result = validate(payload=bad, repo_root=REPO_ROOT)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("v2_boundary_requirements" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
