from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from mission.architecture.feasibility import (
    SCHEMA_VERSION,
    build_cost_procurement_architecture_feasibility,
    validate_cost_procurement_architecture_feasibility,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class CostProcurementArchitectureFeasibilityTests(unittest.TestCase):
    def test_committed_artifact_validates_and_keeps_procurement_external(self) -> None:
        payload = json.loads(
            (REPO_ROOT / "artifacts/cost_procurement_architecture_feasibility.v1.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual([], validate_cost_procurement_architecture_feasibility(payload, repo_root=REPO_ROOT))
        self.assertEqual(SCHEMA_VERSION, payload["schema_version"])
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(15, payload["architecture_row_count"])
        self.assertFalse(payload["rollup"]["procurement_grade_estimate_available"])
        self.assertFalse(payload["rollup"]["vendor_quote_count"])
        self.assertFalse(payload["rollup"]["launch_vehicle_selected"])
        self.assertFalse(payload["rollup"]["architecture_selected_for_flight"])
        self.assertTrue(payload["rollup"]["all_rows_review_required"])
        self.assertIn("procurement-grade cost estimate", payload["blocked_claims"])
        self.assertIn("flight-ready architecture selected", payload["blocked_claims"])

        default_row = next(row for row in payload["architecture_rows"] if row["is_default_reference"])
        self.assertEqual("reference-black-hole", default_row["target_id"])
        self.assertEqual("conditional-45", default_row["velocity_id"])
        self.assertEqual("external_required", default_row["procurement_status"])
        self.assertIn(default_row["architecture_feasibility_status"], {"review_required", "blocked_external_evidence"})

    def test_builder_is_deterministic(self) -> None:
        committed = json.loads(
            (REPO_ROOT / "artifacts/cost_procurement_architecture_feasibility.v1.json").read_text(
                encoding="utf-8"
            )
        )
        built = build_cost_procurement_architecture_feasibility(REPO_ROOT)

        self.assertEqual(committed, built)
        self.assertEqual([], validate_cost_procurement_architecture_feasibility(built, repo_root=REPO_ROOT))

    def test_validator_rejects_procurement_and_architecture_overclaims(self) -> None:
        payload = build_cost_procurement_architecture_feasibility(REPO_ROOT)
        cases = [
            ("non_certification_notice", lambda item: item.update({"non_certification_notice": False})),
            (
                "procurement_grade_estimate_available",
                lambda item: item["rollup"].update({"procurement_grade_estimate_available": True}),
            ),
            ("vendor_quote_count", lambda item: item["rollup"].update({"vendor_quote_count": 1})),
            ("launch_vehicle_selected", lambda item: item["rollup"].update({"launch_vehicle_selected": True})),
            (
                "architecture_selected_for_flight",
                lambda item: item["rollup"].update({"architecture_selected_for_flight": True}),
            ),
            (
                "procurement_status",
                lambda item: item["architecture_rows"][0].update({"procurement_status": "vendor_quoted"}),
            ),
            (
                "blocked_claims",
                lambda item: item.update({"blocked_claims": ["mission feasible"]}),
            ),
        ]
        for expected, mutate in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = validate_cost_procurement_architecture_feasibility(broken, repo_root=REPO_ROOT)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
