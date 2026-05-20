from __future__ import annotations

import unittest

from models.claim_calculations import compute_claim_values
from models.evidence_io import load_claims, value_at_path


class ClaimCalculationTests(unittest.TestCase):
    def test_all_registry_claims_are_computed(self) -> None:
        registry = load_claims()
        values = compute_claim_values()
        for claim in registry["claims"]:
            self.assertIn(claim["id"], values)

    def test_registry_ranges_match_calculated_values(self) -> None:
        registry = load_claims()
        values = compute_claim_values()
        for claim in registry["claims"]:
            claim_values = values[claim["id"]]
            for check in claim["checks"]:
                value = float(value_at_path(claim_values, check["path"]))
                self.assertGreaterEqual(value, float(check["min"]), msg=f"{claim['id']}:{check['path']}")
                self.assertLessEqual(value, float(check["max"]), msg=f"{claim['id']}:{check['path']}")


if __name__ == "__main__":
    unittest.main()

