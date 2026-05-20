from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from mission.survivability.risk_budget import (
    DEFAULT_ROW_ID,
    DEFAULT_SAMPLE_COUNT,
    FAILURE_MODES,
    MINIMUM_SAMPLE_COUNT,
    QUALIFICATION_ROADMAP,
    SCHEMA_VERSION,
    SOURCE_POLICY,
    SOURCE_ARTIFACT_REF,
    validate_capsule_risk_budget_artifact,
)
from scripts.build_capsule_risk_budget_artifact import build_capsule_risk_budget_artifact


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIMENSIONS = {
    "dust",
    "radiation",
    "plasma",
    "media_margin",
    "material_degradation",
    "shield_areal_density",
    "exposure_fraction",
    "velocity",
    "target_distance",
    "time_horizon",
}
REQUIRED_ATTACK_MODES = {
    "nominal",
    "skeptical",
    "severe_dust",
    "media_decay",
    "radiation_stress",
}


def _minimal_valid_payload() -> dict:
    risk_budget_row = {
        "row_id": DEFAULT_ROW_ID,
        "capsule_id": "baseline-stack",
        "profile_id": "baseline-stack",
        "target_id": "reference-black-hole",
        "velocity_id": "conditional-45",
        "time_id": "ballistic-arrival",
        "flight_years": 10_319_422.649603,
        "attack_mode_id": "nominal",
        "quantiles": {
            "p01": 0.01,
            "p05": 0.05,
            "p50": 0.5,
            "p95": 0.95,
            "p99": 0.99,
        },
        "survival_loss_by_driver": [
            {"driver": "material_degradation", "share": 0.65, "survival_loss_equivalent": 0.4},
            {"driver": "dust", "share": 0.15, "survival_loss_equivalent": 0.1},
            {"driver": "radiation", "share": 0.1, "survival_loss_equivalent": 0.08},
            {"driver": "plasma", "share": 0.05, "survival_loss_equivalent": 0.04},
            {"driver": "media_margin", "share": 0.05, "survival_loss_equivalent": 0.04},
        ],
        "top_uncertainty_drivers": [
            {"driver": "material_degradation", "sensitivity": -0.9},
            {"driver": "media_margin", "sensitivity": 0.3},
        ],
        "failure_mode_contributions": [
            {"mode": "structure_loss", "share": 0.35},
            {"mode": "media_loss", "share": 0.45},
            {"mode": "coupled_structure_media_loss", "share": 0.2},
        ],
        "required_improvement": [
            {"target_p50": 0.5, "achieved": True, "required_hazard_reduction_fraction": 0.0},
            {"target_p50": 0.9, "achieved": False, "required_hazard_reduction_fraction": 0.75},
        ],
        "qualification_roadmap": [{"label": "Archive media retention campaign", "status": "required"}],
        "evidence_needed": [
            {
                "evidence_gap_id": "archive-media-aging-campaign",
                "driver": "material_degradation",
                "evidence_class": "assumption_bound",
                "status": "external_required",
                "needed": "Material aging evidence.",
            }
        ],
        "evidence_gap_ids": ["archive-media-aging-campaign"],
        "acceptance_criteria": [
            {
                "id": "row-context-visible",
                "status": "met",
                "criterion": "Target, horizon, velocity, capsule profile, and attack mode are explicit.",
            }
        ],
        "blocking_claims": ["certified hardware survivability"],
    }
    risk_budgets = [copy.deepcopy(risk_budget_row) for _ in range(100)]
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": "tests",
        "source_artifact_ref": SOURCE_ARTIFACT_REF,
        "source_artifact_sha256": "0" * 64,
        "non_certification_notice": True,
        "sample_count": MINIMUM_SAMPLE_COUNT,
        "seed": 11,
        "default_row_id": DEFAULT_ROW_ID,
        "risk_budget_count": len(risk_budgets),
        "source_policy": copy.deepcopy(SOURCE_POLICY),
        "failure_modes": copy.deepcopy(FAILURE_MODES),
        "qualification_roadmap": copy.deepcopy(QUALIFICATION_ROADMAP),
        "uncertainty_dimensions": [
            {
                "id": dimension,
                "label": dimension.replace("_", " "),
                "targets": ["environment.dust_flux_scale"],
                "provenance": "proxy",
                "distribution": "deterministic_uniform",
                "source_ids": ["SRC-TEST"],
            }
            for dimension in sorted(REQUIRED_DIMENSIONS)
        ],
        "risk_budgets": risk_budgets,
        "attack_modes": {
            "default_row_id": DEFAULT_ROW_ID,
            "modes": [
                {
                    "id": mode,
                    "total_capsule_survival": 0.4,
                    "structure_survival": 0.7,
                    "media_integrity": 0.571428571429,
                    "integrated_hazards": {"structure": 0.35, "media": 0.56},
                }
                for mode in sorted(REQUIRED_ATTACK_MODES)
            ],
        },
    }


def _assert_quantiles_ordered(test_case: unittest.TestCase, quantiles: dict) -> None:
    values = [float(quantiles[key]) for key in ("p01", "p05", "p50", "p95", "p99")]
    test_case.assertEqual(values, sorted(values))
    for value in values:
        test_case.assertGreaterEqual(value, 0.0)
        test_case.assertLessEqual(value, 1.0)


class CapsuleRiskBudgetTests(unittest.TestCase):
    def test_committed_artifact_validates_and_exposes_default_budget(self) -> None:
        payload = json.loads((REPO_ROOT / "artifacts" / "capsule_risk_budget.v1.json").read_text(encoding="utf-8"))

        self.assertEqual([], validate_capsule_risk_budget_artifact(payload))
        self.assertEqual(SCHEMA_VERSION, payload["schema_version"])
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual(SOURCE_ARTIFACT_REF, payload["source_artifact_ref"])
        self.assertEqual(DEFAULT_SAMPLE_COUNT, payload["sample_count"])
        self.assertEqual(DEFAULT_ROW_ID, payload["default_row_id"])
        self.assertEqual(payload["risk_budget_count"], len(payload["risk_budgets"]))
        self.assertGreaterEqual(len(payload["risk_budgets"]), 100)
        self.assertIn("source_policy", payload)
        self.assertIn("failure_modes", payload)
        self.assertIn("qualification_roadmap", payload)
        self.assertGreaterEqual(len(payload["failure_modes"]), 8)
        self.assertGreaterEqual(len(payload["qualification_roadmap"]), 5)

        dimensions = {item["id"] for item in payload["uncertainty_dimensions"]}
        self.assertTrue(REQUIRED_DIMENSIONS.issubset(dimensions))
        for dimension in payload["uncertainty_dimensions"]:
            self.assertTrue(dimension["source_ids"])

        default_budget = next(item for item in payload["risk_budgets"] if item["row_id"] == DEFAULT_ROW_ID)
        _assert_quantiles_ordered(self, default_budget["quantiles"])
        self.assertEqual({"0.5", "0.9"}, {str(item["target_p50"]) for item in default_budget["required_improvement"]})
        self.assertTrue(default_budget["evidence_needed"])
        self.assertTrue(default_budget["evidence_gap_ids"])
        self.assertTrue(default_budget["acceptance_criteria"])
        self.assertTrue(any("certified" in claim for claim in default_budget["blocking_claims"]))

        loss_drivers = {item["driver"] for item in default_budget["survival_loss_by_driver"]}
        self.assertTrue({"material_degradation", "dust", "radiation", "plasma", "media_margin"}.issubset(loss_drivers))
        self.assertGreaterEqual(len(default_budget["top_uncertainty_drivers"]), 3)
        failure_share = sum(float(item["share"]) for item in default_budget["failure_mode_contributions"])
        self.assertAlmostEqual(1.0, failure_share, places=6)

        attack_modes = payload["attack_modes"]
        self.assertEqual(DEFAULT_ROW_ID, attack_modes["default_row_id"])
        mode_ids = {item["id"] for item in attack_modes["modes"]}
        self.assertTrue(REQUIRED_ATTACK_MODES.issubset(mode_ids))
        for mode in attack_modes["modes"]:
            self.assertGreaterEqual(mode["total_capsule_survival"], 0.0)
            self.assertLessEqual(mode["total_capsule_survival"], 1.0)

    def test_builder_is_deterministic_for_same_seed_and_source_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first_output = Path(temp_dir) / "first.json"
            second_output = Path(temp_dir) / "second.json"

            first = build_capsule_risk_budget_artifact(
                repo_root=REPO_ROOT,
                output_path=first_output,
                sample_count=MINIMUM_SAMPLE_COUNT,
                seed=20240509,
            )
            second = build_capsule_risk_budget_artifact(
                repo_root=REPO_ROOT,
                output_path=second_output,
                sample_count=MINIMUM_SAMPLE_COUNT,
                seed=20240509,
            )

            self.assertEqual("PASS", first["status"])
            self.assertEqual("PASS", second["status"])
            self.assertEqual(first["artifact_sha256"], second["artifact_sha256"])
            self.assertEqual(first["risk_budget_count"], second["risk_budget_count"])
            self.assertEqual(DEFAULT_ROW_ID, first["default_row_id"])

            payload = json.loads(first_output.read_text(encoding="utf-8"))
            self.assertEqual([], validate_capsule_risk_budget_artifact(payload))
            self.assertEqual(SOURCE_ARTIFACT_REF, payload["source_artifact_ref"])

    def test_validator_rejects_required_contract_breaks(self) -> None:
        cases = [
            ("non_certification_notice", lambda payload: payload.update({"non_certification_notice": False})),
            ("source_artifact_ref", lambda payload: payload.pop("source_artifact_ref")),
            ("sample_count", lambda payload: payload.update({"sample_count": MINIMUM_SAMPLE_COUNT - 1})),
            ("source_policy", lambda payload: payload.pop("source_policy")),
            ("failure_modes", lambda payload: payload.update({"failure_modes": []})),
            ("qualification_roadmap", lambda payload: payload.update({"qualification_roadmap": []})),
            ("default_row_id", lambda payload: payload.update({"default_row_id": "missing-row"})),
            ("risk_budget_count", lambda payload: payload.update({"risk_budget_count": 99})),
            (
                "attack_modes",
                lambda payload: payload["attack_modes"].update(
                    {"modes": [mode for mode in payload["attack_modes"]["modes"] if mode["id"] != "severe_dust"]}
                ),
            ),
            (
                "quantiles",
                lambda payload: payload["risk_budgets"][0].update(
                    {"quantiles": {"p01": 0.01, "p05": 0.7, "p50": 0.6, "p95": 0.95, "p99": 0.99}}
                ),
            ),
            ("evidence_needed", lambda payload: payload["risk_budgets"][0].update({"evidence_needed": []})),
            ("acceptance_criteria", lambda payload: payload["risk_budgets"][0].update({"acceptance_criteria": []})),
            ("blocking_claims", lambda payload: payload["risk_budgets"][0].update({"blocking_claims": []})),
        ]

        for expected, mutate in cases:
            with self.subTest(expected=expected):
                payload = copy.deepcopy(_minimal_valid_payload())
                mutate(payload)

                errors = validate_capsule_risk_budget_artifact(payload)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_validator_accepts_minimal_valid_contract(self) -> None:
        self.assertEqual([], validate_capsule_risk_budget_artifact(_minimal_valid_payload()))


if __name__ == "__main__":
    unittest.main()
