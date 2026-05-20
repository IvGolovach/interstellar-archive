from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.ci import parameter_evidence_validate as evidence_validate


REPO_ROOT = Path(__file__).resolve().parents[1]


class ParameterEvidenceContractTests(unittest.TestCase):
    def _load(self) -> tuple[dict, dict, dict]:
        registry = json.loads((REPO_ROOT / "parameters/registry/parameter_registry.v1.json").read_text(encoding="utf-8"))
        sources = json.loads((REPO_ROOT / "parameters/registry/evidence_sources.v1.json").read_text(encoding="utf-8"))
        claims = json.loads((REPO_ROOT / "parameters/registry/parameter_claims.v1.json").read_text(encoding="utf-8"))
        return registry, sources, claims

    def test_current_contract_passes(self) -> None:
        registry, sources, claims = self._load()
        result = evidence_validate.validate(registry, sources, claims)
        self.assertEqual("PASS", result["status"], result)
        self.assertEqual(0, result["missing_evidence_count"])
        self.assertEqual(0, result["realistic_D_violations"])

    def test_realistic_d_violation_fails(self) -> None:
        registry, sources, claims = self._load()
        target = next(item for item in claims["claims"] if item["mode"] == "realistic")
        target["trust_grade"] = "D"
        result = evidence_validate.validate(registry, sources, claims)
        self.assertEqual("FAIL", result["status"])
        self.assertGreater(result["realistic_D_violations"], 0)

    def test_missing_evidence_source_fails(self) -> None:
        registry, sources, claims = self._load()
        claims["claims"][0]["evidence_source_ids"] = ["SRC-NOT-FOUND"]
        result = evidence_validate.validate(registry, sources, claims)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("unknown source" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
