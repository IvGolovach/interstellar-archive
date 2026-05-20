from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from scripts.ci import parameter_registry_validate as registry_validate


REPO_ROOT = Path(__file__).resolve().parents[1]


class ParameterRegistryContractTests(unittest.TestCase):
    def test_current_registry_passes_strict_contract(self) -> None:
        registry = json.loads((REPO_ROOT / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))
        uncertainty = json.loads((REPO_ROOT / "mission/UNCERTAINTY_MODEL_v1.json").read_text(encoding="utf-8"))
        result = registry_validate.validate(registry, uncertainty)
        self.assertEqual("PASS", result["status"], result)
        self.assertEqual(0, len(result["errors"]), result["errors"])

    def test_current_registry_declares_surface_visibility_metadata(self) -> None:
        registry = json.loads((REPO_ROOT / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))

        code_literal_entries = [
            item for item in registry["parameters"] if str(item.get("parameter_id", "")).startswith("code_literal.")
        ]
        public_entries = [
            item for item in registry["parameters"] if not str(item.get("parameter_id", "")).startswith("code_literal.")
        ]

        self.assertGreater(len(code_literal_entries), 0)
        self.assertGreater(len(public_entries), 0)
        for entry in code_literal_entries:
            self.assertEqual("internal", entry.get("visibility"), entry["parameter_id"])
            self.assertEqual([], entry.get("public_surfaces"), entry["parameter_id"])
            self.assertEqual("code_literal", entry.get("audit_scope"), entry["parameter_id"])
        for entry in public_entries:
            self.assertEqual("public", entry.get("visibility"), entry["parameter_id"])
            self.assertEqual(["browser", "optimization"], entry.get("public_surfaces"), entry["parameter_id"])
            self.assertEqual("mission_parameter", entry.get("audit_scope"), entry["parameter_id"])

    def test_invalid_bounds_fail(self) -> None:
        registry = json.loads((REPO_ROOT / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))
        uncertainty = json.loads((REPO_ROOT / "mission/UNCERTAINTY_MODEL_v1.json").read_text(encoding="utf-8"))

        registry["parameters"][0]["bounds"] = [10, 1]
        result = registry_validate.validate(registry, uncertainty)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("min <= max" in error for error in result["errors"]))

    def test_distribution_without_evidence_source_ids_fails(self) -> None:
        registry = json.loads((REPO_ROOT / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))
        uncertainty = json.loads((REPO_ROOT / "mission/UNCERTAINTY_MODEL_v1.json").read_text(encoding="utf-8"))

        target = next(item for item in registry["parameters"] if item["type"] == "distribution")
        target["distribution"]["evidence_source_ids"] = []
        result = registry_validate.validate(registry, uncertainty)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("evidence_source_ids" in error for error in result["errors"]))

    def test_schema_requires_surface_visibility_metadata(self) -> None:
        schema = json.loads((REPO_ROOT / "parameters/schema/parameter_registry.schema.v1.json").read_text(encoding="utf-8"))
        parameter_schema = schema["properties"]["parameters"]["items"]

        required = set(parameter_schema["required"])
        self.assertTrue({"visibility", "public_surfaces", "audit_scope"}.issubset(required))
        self.assertEqual(["public", "internal"], parameter_schema["properties"]["visibility"]["enum"])
        self.assertEqual(
            ["browser", "optimization"],
            parameter_schema["properties"]["public_surfaces"]["items"]["enum"],
        )
        self.assertEqual(["mission_parameter", "code_literal"], parameter_schema["properties"]["audit_scope"]["enum"])

    def test_public_visibility_requires_public_surface_and_mission_audit_scope(self) -> None:
        registry = json.loads((REPO_ROOT / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))
        uncertainty = json.loads((REPO_ROOT / "mission/UNCERTAINTY_MODEL_v1.json").read_text(encoding="utf-8"))

        target = next(item for item in registry["parameters"] if item["visibility"] == "public")
        target["public_surfaces"] = []
        target["audit_scope"] = "code_literal"
        result = registry_validate.validate(registry, uncertainty)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("public visibility" in error for error in result["errors"]))

    def test_code_literal_visibility_must_remain_internal_audit_only(self) -> None:
        registry = json.loads((REPO_ROOT / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))
        uncertainty = json.loads((REPO_ROOT / "mission/UNCERTAINTY_MODEL_v1.json").read_text(encoding="utf-8"))

        target = next(item for item in registry["parameters"] if str(item.get("parameter_id", "")).startswith("code_literal."))
        target["visibility"] = "public"
        target["public_surfaces"] = ["browser"]
        target["audit_scope"] = "mission_parameter"
        result = registry_validate.validate(registry, uncertainty)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("code_literal" in error and "internal" in error for error in result["errors"]))

    def test_legacy_line_based_code_literal_id_fails(self) -> None:
        registry = json.loads((REPO_ROOT / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))
        uncertainty = json.loads((REPO_ROOT / "mission/UNCERTAINTY_MODEL_v1.json").read_text(encoding="utf-8"))

        target = next(item for item in registry["parameters"] if str(item.get("parameter_id", "")).startswith("code_literal."))
        target["parameter_id"] = "code_literal.scripts_mission_baseline_check_py_14_4"
        result = registry_validate.validate(registry, uncertainty)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("legacy line-based" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
