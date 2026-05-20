from __future__ import annotations

import copy
from importlib import import_module
import json
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _external_reproduction_module():
    try:
        return import_module("mission.external_reproduction")
    except ModuleNotFoundError as exc:
        raise AssertionError("mission.external_reproduction must expose reproduction-kit builders") from exc


def _load_artifact(name: str) -> dict:
    path = REPO_ROOT / "artifacts" / name
    if not path.exists():
        raise AssertionError(f"committed external-reproduction artifact missing: artifacts/{name}")
    return json.loads(path.read_text(encoding="utf-8"))


class ExternalReproductionIntakeTests(unittest.TestCase):
    def test_external_reproduction_kit_is_exportable_without_claiming_execution(self) -> None:
        reproduction = _external_reproduction_module()
        payload = reproduction.build_external_reproduction_kit(REPO_ROOT)

        self.assertEqual("external_reproduction_kit.v1", payload["schema_version"])
        self.assertEqual([], reproduction.validate_external_reproduction_kit(payload, repo_root=REPO_ROOT))
        self.assertEqual(payload, _load_artifact("external_reproduction_kit.v1.json"))
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual("repo_native_reproduction_kit_ready_external_execution_open", payload["kit_status"])
        self.assertTrue(payload["rollup"]["export_cli_available"])
        self.assertFalse(payload["rollup"]["external_execution_completed"])
        self.assertFalse(payload["rollup"]["first_real_external_record_present"])
        self.assertGreaterEqual(payload["review_case_count"], 7)
        self.assertIn("external validation completed", payload["blocked_claims"])

        with tempfile.TemporaryDirectory() as tmp:
            export_result = reproduction.export_external_reproduction_pack(
                repo_root=REPO_ROOT,
                output_dir=Path(tmp) / "reviewer-pack",
                make_zip=False,
            )
            errors = reproduction.validate_exported_external_reproduction_pack(export_result["pack_root"])

        self.assertEqual([], errors)
        self.assertEqual("external_reproduction_pack.v1", export_result["manifest"]["schema_version"])
        self.assertIn("EXTERNAL_REPRODUCTION_README.md", export_result["manifest"]["pack_files"])
        self.assertIn("templates/external_evidence_record_template.v1.json", export_result["manifest"]["pack_files"])
        self.assertIn("commands/reproduction_commands.txt", export_result["manifest"]["pack_files"])

    def test_external_evidence_intake_is_open_until_real_external_records_exist(self) -> None:
        reproduction = _external_reproduction_module()
        payload = reproduction.build_external_evidence_intake(REPO_ROOT)

        self.assertEqual("external_evidence_intake.v1", payload["schema_version"])
        self.assertEqual([], reproduction.validate_external_evidence_intake(payload, repo_root=REPO_ROOT))
        self.assertEqual(payload, _load_artifact("external_evidence_intake.v1.json"))
        self.assertTrue(payload["non_certification_notice"])
        self.assertEqual("external_record_intake_ready_awaiting_external_submission", payload["intake_status"])
        self.assertEqual(0, payload["record_count"])
        self.assertEqual(0, payload["accepted_record_count"])
        self.assertFalse(payload["rollup"]["first_real_external_record_present"])
        self.assertFalse(payload["rollup"]["external_validation_completed"])
        self.assertFalse(payload["rollup"]["independent_backend_validated"])
        self.assertTrue(payload["validation_policy"]["reject_repository_maintainer_as_external"])
        self.assertTrue(payload["validation_policy"]["reject_self_signed_repo_native_records"])

    def test_record_validator_rejects_self_signed_repository_native_overclaim(self) -> None:
        reproduction = _external_reproduction_module()
        fake_record = reproduction.external_evidence_record_template(
            record_type="independent_reproduction",
            review_case_id="independent-backend-comparison",
        )
        fake_record["reviewer"]["reviewer_kind"] = "repository_maintainer"
        fake_record["attestation"]["attestation_kind"] = "self_signed_repo_native"
        fake_record["claim_effect"]["external_validation_completed"] = True

        errors = reproduction.validate_external_evidence_record(fake_record, repo_root=REPO_ROOT)

        self.assertTrue(errors)
        self.assertTrue(any("reviewer_kind" in error for error in errors), errors)
        self.assertTrue(any("attestation_kind" in error for error in errors), errors)
        self.assertTrue(any("claim_effect.external_validation_completed" in error for error in errors), errors)

    def test_record_validator_accepts_third_party_shape_without_unlocking_certification(self) -> None:
        reproduction = _external_reproduction_module()
        record = reproduction.external_evidence_record_template(
            record_type="independent_reproduction",
            review_case_id="independent-backend-comparison",
        )
        record["reviewer"].update(
            {
                "reviewer_kind": "independent_third_party",
                "name_or_handle": "external-reviewer-placeholder",
                "organization": "external-organization-placeholder",
                "conflict_of_interest_statement": "No repository maintainer role declared.",
            }
        )
        record["attestation"].update(
            {
                "attestation_kind": "third_party_signed_report",
                "signature_or_report_uri": "https://example.invalid/external-report-placeholder",
            }
        )
        record["reproduction"].update(
            {
                "reviewed_commit_sha": "106441e35d56614650d569c7052840442bedaea2",
                "commands": ["python3 scripts/ci/check_suite.py"],
                "raw_outputs_or_report_uri": "https://example.invalid/raw-output-placeholder",
            }
        )

        errors = reproduction.validate_external_evidence_record(record, repo_root=REPO_ROOT)

        self.assertEqual([], errors)
        self.assertFalse(record["claim_effect"]["certification_go"])
        self.assertFalse(record["claim_effect"]["qualification_complete"])

    def test_intake_validator_rejects_manual_record_count_or_claim_promotion(self) -> None:
        reproduction = _external_reproduction_module()
        payload = reproduction.build_external_evidence_intake(REPO_ROOT)
        broken = copy.deepcopy(payload)
        broken["record_count"] = 1
        broken["accepted_record_count"] = 1
        broken["rollup"]["first_real_external_record_present"] = True
        broken["rollup"]["external_validation_completed"] = True

        errors = reproduction.validate_external_evidence_intake(broken, repo_root=REPO_ROOT)

        self.assertTrue(errors)
        self.assertTrue(any("record_count" in error for error in errors), errors)
        self.assertTrue(any("external_validation_completed" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
