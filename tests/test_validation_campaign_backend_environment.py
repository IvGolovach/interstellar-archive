from __future__ import annotations

import copy
from importlib import import_module
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _validation_campaign_module():
    try:
        return import_module("mission.validation_campaign")
    except ModuleNotFoundError as exc:
        raise AssertionError("mission.validation_campaign must expose backend/environment builders") from exc


class ValidationCampaignBackendEnvironmentTests(unittest.TestCase):
    def test_independent_backend_execution_plan_keeps_external_backend_open(self) -> None:
        campaign = _validation_campaign_module()
        payload = campaign.build_independent_backend_execution_plan(REPO_ROOT)

        self.assertEqual("validation_campaign_independent_backend_execution.v1", payload["schema_version"])
        self.assertEqual([], campaign.validate_independent_backend_execution_plan(payload, repo_root=REPO_ROOT))
        self.assertEqual(payload, campaign.build_independent_backend_execution_plan(REPO_ROOT))
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(
            "repo_native_plan_ready_external_backend_not_complete",
            payload["execution_plan_status"],
        )
        self.assertEqual(6, payload["module_execution_count"])
        self.assertTrue(
            all(row["execution_status"] == "external_required" for row in payload["module_execution_rows"])
        )
        self.assertFalse(payload["rollup"]["independent_external_backend_complete"])
        self.assertFalse(payload["rollup"]["independent_physics_backend_validated"])
        self.assertFalse(payload["rollup"]["high_fidelity_state_trace_complete"])
        self.assertFalse(payload["rollup"]["external_validation_completed"])
        self.assertIn("independent physics backend validated", payload["blocked_claims"])
        self.assertIn("certified", payload["blocked_claims"])

    def test_line_of_sight_environment_model_separates_source_anchors_from_assumption_tails(self) -> None:
        campaign = _validation_campaign_module()
        payload = campaign.build_line_of_sight_environment_model(REPO_ROOT)

        self.assertEqual("validation_campaign_line_of_sight_environment.v1", payload["schema_version"])
        self.assertEqual([], campaign.validate_line_of_sight_environment_model(payload, repo_root=REPO_ROOT))
        self.assertEqual(payload, campaign.build_line_of_sight_environment_model(REPO_ROOT))
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(
            "repo_native_line_of_sight_environment_model_open",
            payload["environment_model_status"],
        )
        self.assertEqual(
            {"source_backed_anchor"},
            {anchor["evidence_class"] for anchor in payload["source_backed_anchors"]},
        )
        self.assertEqual(
            {"assumption_bound"},
            {tail["evidence_class"] for tail in payload["assumption_bound_tails"]},
        )
        self.assertTrue({"target", "dust", "plasma"}.issubset(payload["assumption_tail_categories"]))
        self.assertEqual(3, payload["line_of_sight_target_count"])
        self.assertTrue(
            all(
                row["environment_validation_status"] == "line_of_sight_evidence_required"
                for row in payload["line_of_sight_rows"]
            )
        )
        self.assertFalse(payload["rollup"]["line_of_sight_environment_validated"])
        self.assertFalse(payload["rollup"]["fixed_mm_cm_dust_truth_claimed"])
        self.assertFalse(payload["rollup"]["target_region_plasma_validated"])
        self.assertIn("fixed mm/cm dust truth", payload["blocked_claims"])

    def test_backend_validator_rejects_external_or_backend_validation_overclaims(self) -> None:
        campaign = _validation_campaign_module()
        payload = campaign.build_independent_backend_execution_plan(REPO_ROOT)
        cases = [
            (
                "independent_external_backend_complete",
                lambda item: item["rollup"].update({"independent_external_backend_complete": True}),
            ),
            (
                "independent_physics_backend_validated",
                lambda item: item["rollup"].update({"independent_physics_backend_validated": True}),
            ),
            (
                "high_fidelity_state_trace_complete",
                lambda item: item["rollup"].update({"high_fidelity_state_trace_complete": True}),
            ),
            (
                "external_validation_completed",
                lambda item: item["rollup"].update({"external_validation_completed": True}),
            ),
            ("blocked_claims", lambda item: item.update({"blocked_claims": ["review planned"]})),
        ]

        for expected, mutate in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = campaign.validate_independent_backend_execution_plan(broken, repo_root=REPO_ROOT)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_environment_validator_rejects_dust_truth_and_plasma_overclaims(self) -> None:
        campaign = _validation_campaign_module()
        payload = campaign.build_line_of_sight_environment_model(REPO_ROOT)
        cases = [
            (
                "fixed_mm_cm_dust_truth_claimed",
                lambda item: item["rollup"].update({"fixed_mm_cm_dust_truth_claimed": True}),
            ),
            (
                "target_region_plasma_validated",
                lambda item: item["rollup"].update({"target_region_plasma_validated": True}),
            ),
            (
                "line_of_sight_environment_validated",
                lambda item: item["rollup"].update({"line_of_sight_environment_validated": True}),
            ),
            (
                "assumption_bound_tails",
                lambda item: item["assumption_bound_tails"][0].update({"evidence_class": "source_backed_anchor"}),
            ),
            (
                "fixed_truth_claimed",
                lambda item: item["assumption_bound_tails"][1].update({"fixed_truth_claimed": True}),
            ),
            ("blocked_claims", lambda item: item.update({"blocked_claims": ["environment work planned"]})),
        ]

        for expected, mutate in cases:
            with self.subTest(expected=expected):
                broken = copy.deepcopy(payload)
                mutate(broken)

                errors = campaign.validate_line_of_sight_environment_model(broken, repo_root=REPO_ROOT)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
