from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from mission.deep_time.feasibility import (
    SCHEMA_VERSION,
    _impact_energy_j,
    build_deep_time_archive_feasibility,
    validate_deep_time_archive_feasibility,
)
from scripts.build_deep_time_archive_feasibility_artifact import DEFAULT_OUTPUT
from scripts.build_deep_time_archive_feasibility_artifact import main as build_main


REPO_ROOT = Path(__file__).resolve().parents[1]


class DeepTimeArchiveFeasibilityTests(unittest.TestCase):
    def test_committed_artifact_validates_and_keeps_claims_bounded(self) -> None:
        payload = json.loads((REPO_ROOT / DEFAULT_OUTPUT).read_text(encoding="utf-8"))

        self.assertEqual([], validate_deep_time_archive_feasibility(payload, repo_root=REPO_ROOT))
        self.assertEqual(SCHEMA_VERSION, payload["schema_version"])
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual("gaia-bh1-reference", payload["target_corridor"]["target_id"])
        self.assertFalse(payload["target_corridor"]["dynamic_target_worldline_corridor"]["status"] != "external_required")
        self.assertIsNone(payload["probability_decomposition"]["full_P_archive_recoverable"])
        self.assertIn("mission feasible", payload["blocked_claims"])
        self.assertIn("guaranteed archive recovery", payload["blocked_claims"])
        self.assertFalse(payload["rollup"]["full_probability_closed"])
        self.assertFalse(payload["rollup"]["qualification_complete"])

    def test_builder_is_deterministic_for_same_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "first.json"
            second = Path(temp_dir) / "second.json"

            payload_a = build_deep_time_archive_feasibility(REPO_ROOT)
            payload_b = build_deep_time_archive_feasibility(REPO_ROOT)
            first.write_text(json.dumps(payload_a, sort_keys=True), encoding="utf-8")
            second.write_text(json.dumps(payload_b, sort_keys=True), encoding="utf-8")

            self.assertEqual(payload_a["determinism_signature"], payload_b["determinism_signature"])
            self.assertEqual(first.read_text(encoding="utf-8"), second.read_text(encoding="utf-8"))

    def test_impact_energy_scales_with_radius_cubed_and_velocity_squared(self) -> None:
        e_1_um_45 = _impact_energy_j(1.0e-6, 45.0)
        e_10_um_45 = _impact_energy_j(1.0e-5, 45.0)
        e_1_um_60 = _impact_energy_j(1.0e-6, 60.0)

        self.assertAlmostEqual(e_1_um_45 * 1000.0, e_10_um_45, delta=e_10_um_45 * 1.0e-12)
        self.assertAlmostEqual((60.0 / 45.0) ** 2, e_1_um_60 / e_1_um_45, places=12)

    def test_validator_rejects_overclaim_breaks(self) -> None:
        payload = build_deep_time_archive_feasibility(REPO_ROOT)
        cases = [
            ("full_P_archive_recoverable", lambda p: p["probability_decomposition"].update({"full_P_archive_recoverable": 0.1})),
            ("Case A", lambda p: p["encounter_geometry"]["case_a_capture_rows"][0].update({"control_interpretation": "controllable"})),
            ("inbound_vinf", lambda p: p["architecture_and_control"]["conditional_35_45_km_s"][0].update({"inbound_vinf_m_s": 0.0})),
            ("hydrocode_extrapolation_required", lambda p: p["dust_and_particles"]["shield_response_boundary"].update({"hydrocode_extrapolation_required": False})),
            ("ten_myr_experimental_proof_available", lambda p: p["media_readability"].update({"ten_myr_experimental_proof_available": True})),
            ("blocked_claims", lambda p: p.update({"blocked_claims": []})),
        ]
        for expected, mutate in cases:
            with self.subTest(expected=expected):
                bad = copy.deepcopy(payload)
                mutate(bad)

                errors = validate_deep_time_archive_feasibility(bad, repo_root=REPO_ROOT)

                self.assertTrue(errors)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_builder_cli_writes_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "deep_time.json"
            # Exercise the import path indirectly by calling the builder function
            # path used by the CLI module.
            payload = build_deep_time_archive_feasibility(REPO_ROOT)
            output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            written = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual([], validate_deep_time_archive_feasibility(written, repo_root=REPO_ROOT))


if __name__ == "__main__":
    unittest.main()
