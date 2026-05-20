from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from scripts.parameter_drilldown_builder import _public_parameter_registry, build_artifacts


REPO_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ParameterDrilldownBuilderTests(unittest.TestCase):
    def test_public_parameter_registry_uses_visibility_metadata_with_prefix_guard(self) -> None:
        registry = {
            "schema_version": "parameter_registry.v1",
            "parameters": [
                {
                    "parameter_id": "mission_public.value",
                    "visibility": "public",
                    "public_surfaces": ["browser", "optimization"],
                },
                {
                    "parameter_id": "mission_internal.value",
                    "visibility": "internal",
                    "public_surfaces": [],
                },
                {
                    "parameter_id": "code_literal.synthetic.module.literal_0",
                    "visibility": "public",
                    "public_surfaces": ["browser", "optimization"],
                },
            ],
        }

        filtered = _public_parameter_registry(registry)

        self.assertEqual(
            ["mission_public.value"],
            [item["parameter_id"] for item in filtered["parameters"]],
        )

    def test_build_artifacts_writes_deterministic_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            static_graph = tmp / "static.json"
            evidence_index = tmp / "evidence.json"
            manifest = tmp / "manifest.json"
            p_success = tmp / "p_success.json"

            result = build_artifacts(
                repo_root=REPO_ROOT,
                parameter_registry_path=Path("parameters/registry/parameter_registry.v1.json"),
                parameter_claims_path=Path("parameters/registry/parameter_claims.v1.json"),
                evidence_sources_path=Path("parameters/registry/evidence_sources.v1.json"),
                uncertainty_model_path=Path("mission/UNCERTAINTY_MODEL_v1.json"),
                module_registry_path=Path("mission/dag/registry/module_registry.v1.json"),
                failure_taxonomy_path=Path("mission/dag/registry/failure_taxonomy.v1.json"),
                runner_path=Path("mission/dag/runner_v1.py"),
                static_graph_path=static_graph,
                evidence_index_path=evidence_index,
                manifest_path=manifest,
                p_success_defensibility_path=p_success,
                sensitivity_results_path=Path("artifacts/parameter_sensitivity_summary.json"),
            )

            self.assertEqual("PASS", result["status"], result)
            self.assertGreater(result["parameter_count"], 0)
            self.assertGreater(result["excluded_internal_parameter_count"], 0)
            self.assertEqual(result["static_graph_sha256"], _sha256(static_graph))
            self.assertEqual(result["evidence_index_sha256"], _sha256(evidence_index))
            self.assertEqual(result["p_success_defensibility_sha256"], _sha256(p_success))
            self.assertEqual(result["manifest_sha256"], _sha256(manifest))

            manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual("public_mission_parameters_only", manifest_payload["public_scope"])
            self.assertEqual("mission_design_environment_only", manifest_payload["ui_scope"])
            self.assertTrue(
                all(
                    not str(item.get("parameter_id", "")).startswith("code_literal.")
                    for item in manifest_payload["parameters"]
                )
            )

            static_payload = json.loads(static_graph.read_text(encoding="utf-8"))
            evidence_payload = json.loads(evidence_index.read_text(encoding="utf-8"))
            self.assertTrue(all(not key.startswith("code_literal.") for key in static_payload))
            self.assertTrue(all(not key.startswith("code_literal.") for key in evidence_payload))

            self.assertEqual(
                result,
                build_artifacts(
                    repo_root=REPO_ROOT,
                    parameter_registry_path=Path("parameters/registry/parameter_registry.v1.json"),
                    parameter_claims_path=Path("parameters/registry/parameter_claims.v1.json"),
                    evidence_sources_path=Path("parameters/registry/evidence_sources.v1.json"),
                    uncertainty_model_path=Path("mission/UNCERTAINTY_MODEL_v1.json"),
                    module_registry_path=Path("mission/dag/registry/module_registry.v1.json"),
                    failure_taxonomy_path=Path("mission/dag/registry/failure_taxonomy.v1.json"),
                    runner_path=Path("mission/dag/runner_v1.py"),
                    static_graph_path=static_graph,
                    evidence_index_path=evidence_index,
                    manifest_path=manifest,
                    p_success_defensibility_path=p_success,
                    sensitivity_results_path=Path("artifacts/parameter_sensitivity_summary.json"),
                ),
            )

    def test_cli_entrypoint_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            static_graph = tmp / "static.json"
            evidence_index = tmp / "evidence.json"
            manifest = tmp / "manifest.json"
            p_success = tmp / "p_success.json"

            proc = subprocess.run(
                [
                    sys.executable,
                    "scripts/build_parameter_drilldown_artifacts.py",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--static-graph",
                    str(static_graph),
                    "--evidence-index",
                    str(evidence_index),
                    "--manifest",
                    str(manifest),
                    "--p-success-defensibility",
                    str(p_success),
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, proc.returncode, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual("PASS", payload["status"], payload)
            self.assertTrue(static_graph.exists())
            self.assertTrue(evidence_index.exists())
            self.assertTrue(manifest.exists())
            self.assertTrue(p_success.exists())


if __name__ == "__main__":
    unittest.main()
