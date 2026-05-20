"""External reproduction kit and evidence-intake contracts.

This module prepares reviewer-owned reproduction packs and validates external
evidence records. It intentionally rejects repository-native self-attestations:
external records can be accepted only when they carry an independent reviewer
identity, an external attestation/report URI, and raw outputs or a report URI.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, Iterable, List, Mapping, Sequence
import zipfile


SOURCE_IMPLEMENTATION = "mission/external_reproduction/intake.py"
SOURCE_INIT = "mission/external_reproduction/__init__.py"
SOURCE_ARTIFACT_POLICY = "docs/ARTIFACT_POLICY.md"
SOURCE_REVIEW_PACK = "artifacts/external_validation_review_pack.v1.json"
SOURCE_EXTERNAL_LEDGER = "artifacts/external_validation_execution_ledger.v1.json"
SOURCE_PHYSICS_COMPARISON = "artifacts/independent_physics_backend_comparison.v1.json"
SOURCE_CAPSULE_QUALIFICATION = "artifacts/capsule_qualification_evidence_pack.v1.json"
SOURCE_EVIDENCE_CLOSURE = "artifacts/evidence_upgrade_closure.v1.json"
SOURCE_RELEASE_CANDIDATE = "artifacts/release_candidate_readiness.v1.json"
SOURCE_BROWSER_DATASET = "artifacts/browser_dataset.v1.json"
SOURCE_ROADMAP_CLOSURE = "artifacts/roadmap_closure.v1.json"
SOURCE_CHECK_SUITE = "scripts/ci/check_suite.py"

REPRODUCTION_KIT_SPEC = "mission/EXTERNAL_REPRODUCTION_KIT_SPEC_v1.md"
EVIDENCE_INTAKE_SPEC = "mission/EXTERNAL_EVIDENCE_INTAKE_SPEC_v1.md"
EVIDENCE_RECORD_SCHEMA = "mission/EXTERNAL_EVIDENCE_RECORD_SCHEMA_v1.json"

REPRODUCTION_KIT_BUILDER = "scripts/build_external_reproduction_kit_artifact.py"
EVIDENCE_INTAKE_BUILDER = "scripts/build_external_evidence_intake_artifact.py"
PACK_EXPORTER = "scripts/export_external_reproduction_pack.py"

REPRODUCTION_KIT_VALIDATOR = "scripts/ci/external_reproduction_kit_validate.py"
EVIDENCE_INTAKE_VALIDATOR = "scripts/ci/external_evidence_intake_validate.py"
EVIDENCE_RECORD_VALIDATOR = "scripts/ci/external_evidence_record_validate.py"
PACK_VALIDATOR = "scripts/ci/external_reproduction_pack_validate.py"

REPRODUCTION_KIT_ARTIFACT = "artifacts/external_reproduction_kit.v1.json"
EVIDENCE_INTAKE_ARTIFACT = "artifacts/external_evidence_intake.v1.json"
EXTERNAL_RECORDS_DIR = "evidence/external_records"

BLOCKED_CLAIMS = [
    "external validation completed",
    "third-party validated",
    "independent reproduction completed",
    "independent physics backend validated",
    "cross-backend comparison completed",
    "high-fidelity state trace complete",
    "qualified",
    "certified",
    "flight-ready",
    "source correctness proven",
]

PACK_SOURCE_FILES = [
    "README.md",
    "REPRODUCIBILITY.md",
    "LIMITATIONS.md",
    "MODEL_VERSION.json",
    "VERSION",
    "mission/EXTERNAL_VALIDATION_REVIEW_PACK_SPEC_v1.md",
    "mission/EXTERNAL_VALIDATION_EXECUTION_LEDGER_SPEC_v1.md",
    "mission/INDEPENDENT_PHYSICS_BACKEND_COMPARISON_SPEC_v1.md",
    "mission/CAPSULE_QUALIFICATION_EVIDENCE_PACK_SPEC_v1.md",
    "mission/EVIDENCE_UPGRADE_CLOSURE_SPEC_v1.md",
    "mission/RELEASE_CANDIDATE_READINESS_SPEC_v1.md",
    REPRODUCTION_KIT_SPEC,
    EVIDENCE_INTAKE_SPEC,
    EVIDENCE_RECORD_SCHEMA,
    SOURCE_REVIEW_PACK,
    SOURCE_EXTERNAL_LEDGER,
    SOURCE_PHYSICS_COMPARISON,
    SOURCE_CAPSULE_QUALIFICATION,
    SOURCE_EVIDENCE_CLOSURE,
    SOURCE_RELEASE_CANDIDATE,
    REPRODUCTION_KIT_ARTIFACT,
    EVIDENCE_INTAKE_ARTIFACT,
    SOURCE_ROADMAP_CLOSURE,
    SOURCE_CHECK_SUITE,
    REPRODUCTION_KIT_VALIDATOR,
    EVIDENCE_INTAKE_VALIDATOR,
    EVIDENCE_RECORD_VALIDATOR,
]

REPRODUCTION_COMMANDS = [
    "python3 scripts/ci/check_suite.py",
    "python3 scripts/ci/external_reproduction_kit_validate.py --strict",
    "python3 scripts/ci/external_evidence_intake_validate.py --strict",
    "python3 scripts/ci/external_validation_execution_ledger_validate.py --strict",
    "python3 scripts/ci/independent_physics_backend_comparison_validate.py --strict",
    "python3 scripts/ci/capsule_qualification_evidence_pack_validate.py --strict",
]

RECORD_TYPES = {
    "independent_reproduction",
    "independent_physics_backend",
    "capsule_qualification",
    "public_wording_audit",
    "external_red_team",
}
BAD_REVIEWER_KINDS = {
    "repository_maintainer",
    "repo_native_self_check",
    "internal_ci",
    "automated_internal_ci",
}
ALLOWED_REVIEWER_KINDS = {"independent_third_party", "external_lab", "external_auditor"}
BAD_ATTESTATION_KINDS = {"self_signed_repo_native", "internal_ci_log", "repository_maintainer_statement"}
ALLOWED_ATTESTATION_KINDS = {"third_party_signed_report", "institutional_report_uri", "public_notarized_record"}
CLAIM_EFFECT_FIELDS = [
    "external_validation_completed",
    "independent_reproduction_completed",
    "independent_backend_validated",
    "qualification_complete",
    "certification_go",
    "flight_readiness_go",
]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source_artifacts(repo_root: Path, paths: Sequence[str]) -> List[Dict[str, str]]:
    return [{"path": path, "sha256": _sha256_file(repo_root / path)} for path in paths]


def _source_hash_by_path(payload: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in payload.get("source_artifacts", []):
        if isinstance(item, Mapping) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str):
            out[str(item["path"])] = str(item["sha256"])
    return out


def _validate_sources(
    *,
    repo_root: Path,
    payload: Mapping[str, Any],
    required_paths: Iterable[str],
    errors: List[str],
) -> None:
    expected = set(required_paths)
    by_path = _source_hash_by_path(payload)
    missing = sorted(expected - set(by_path))
    if missing:
        errors.append("source_artifacts missing required paths: " + ", ".join(missing))
    for path in sorted(expected & set(by_path)):
        full = repo_root / path
        if not full.exists():
            errors.append(f"source artifact path does not exist: {path}")
            continue
        if by_path[path] != _sha256_file(full):
            errors.append(f"source_artifacts sha256 mismatch for {path}")


def _determinism_signature(parts: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _review_case_ids(repo_root: Path) -> List[str]:
    review_pack = _load_json(repo_root / SOURCE_REVIEW_PACK)
    cases = review_pack.get("review_cases", [])
    if not isinstance(cases, list):
        return []
    return [str(case.get("id")) for case in cases if isinstance(case, Mapping) and case.get("id")]


def _required_source_paths(spec: str, builder: str, validator: str) -> List[str]:
    return [spec, SOURCE_IMPLEMENTATION, SOURCE_INIT, builder, validator, SOURCE_ARTIFACT_POLICY]


def _kit_source_paths() -> List[str]:
    return [
        SOURCE_REVIEW_PACK,
        SOURCE_EXTERNAL_LEDGER,
        SOURCE_PHYSICS_COMPARISON,
        SOURCE_CAPSULE_QUALIFICATION,
        PACK_EXPORTER,
        PACK_VALIDATOR,
        *_required_source_paths(REPRODUCTION_KIT_SPEC, REPRODUCTION_KIT_BUILDER, REPRODUCTION_KIT_VALIDATOR),
    ]


def _intake_source_paths() -> List[str]:
    return [
        SOURCE_EXTERNAL_LEDGER,
        SOURCE_PHYSICS_COMPARISON,
        SOURCE_CAPSULE_QUALIFICATION,
        EVIDENCE_RECORD_SCHEMA,
        EVIDENCE_RECORD_VALIDATOR,
        EXTERNAL_RECORDS_DIR + "/README.md",
        *_required_source_paths(EVIDENCE_INTAKE_SPEC, EVIDENCE_INTAKE_BUILDER, EVIDENCE_INTAKE_VALIDATOR),
    ]


def _record_types_for_case(case_id: str) -> List[str]:
    if case_id == "independent-backend-comparison":
        return ["independent_reproduction", "independent_physics_backend"]
    if case_id == "public-wording-overinterpretation":
        return ["public_wording_audit"]
    if case_id in {"optimistic-prior-collapse", "dust-tail-severe-mode", "media-decay-severe-mode"}:
        return ["independent_reproduction"]
    return ["external_red_team"]


def build_external_reproduction_kit(repo_root: Path) -> Dict[str, Any]:
    review_pack = _load_json(repo_root / SOURCE_REVIEW_PACK)
    physics_comparison = _load_json(repo_root / SOURCE_PHYSICS_COMPARISON)
    cases = review_pack.get("review_cases", [])
    if not isinstance(cases, list):
        cases = []

    review_cases: List[Dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, Mapping):
            continue
        case_id = str(case.get("id"))
        review_cases.append(
            {
                "review_case_id": case_id,
                "title": case.get("title"),
                "record_types": _record_types_for_case(case_id),
                "source_inputs": case.get("source_inputs", []),
                "expected_reviewer_action": "run_or_independently_recompute_and_submit_external_evidence_record",
                "status": "external_execution_required",
            }
        )

    pack_files = [
        "EXTERNAL_REPRODUCTION_README.md",
        "commands/reproduction_commands.txt",
        "templates/external_evidence_record_template.v1.json",
        "manifest/external_reproduction_pack_manifest.v1.json",
        *[f"repository/{path}" for path in PACK_SOURCE_FILES],
    ]
    payload: Dict[str, Any] = {
        "schema_version": "external_reproduction_kit.v1",
        "generator": REPRODUCTION_KIT_BUILDER,
        "public_scope": "external_reviewer_reproduction_kit",
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, _kit_source_paths()),
        "kit_status": "repo_native_reproduction_kit_ready_external_execution_open",
        "source_commit_sha_policy": "resolved_by_exported_pack_manifest_not_tracked_artifact",
        "review_case_count": len(review_cases),
        "review_cases": review_cases,
        "primary_tracks": [
            {
                "track_id": "independent_reproduction",
                "status": "external_required",
                "record_schema_ref": EVIDENCE_RECORD_SCHEMA,
            },
            {
                "track_id": "independent_physics_backend",
                "status": "external_required",
                "record_schema_ref": EVIDENCE_RECORD_SCHEMA,
            },
            {
                "track_id": "capsule_qualification",
                "status": "external_required_after_reproduction",
                "record_schema_ref": EVIDENCE_RECORD_SCHEMA,
            },
        ],
        "pack_contract": {
            "export_cli": PACK_EXPORTER,
            "pack_validator": PACK_VALIDATOR,
            "default_archive_name": "external-reproduction-kit-v1.zip",
            "output_root_semantics": "reviewer_owned_or_temporary; generated pack contents are not proof records",
            "pack_file_count": len(pack_files),
            "pack_files": pack_files,
            "commands": list(REPRODUCTION_COMMANDS),
        },
        "readiness_snapshot": {
            "repo_analytic_check_count": physics_comparison.get("analytic_check_count"),
            "repo_analytic_max_relative_error": physics_comparison.get("rollup", {}).get("max_relative_error")
            if isinstance(physics_comparison.get("rollup"), Mapping)
            else None,
        },
        "rollup": {
            "external_reproduction_kit_ready": True,
            "export_cli_available": True,
            "record_schema_available": True,
            "external_execution_completed": False,
            "first_real_external_record_present": False,
            "fake_external_records_accepted": False,
            "external_validation_completed": False,
            "independent_backend_validated": False,
        },
        "blocked_claims": list(BLOCKED_CLAIMS),
        "external_evidence_gaps": [
            "external reviewer execution of the pack",
            "signed independent reproduction report",
            "independent physics backend comparison report",
            "raw outputs or immutable report URI",
            "reviewer exception log",
        ],
        "interpretation_limits": [
            "The pack is a reviewer handoff, not an external validation record.",
            "Exporting a pack does not complete reproduction or certification.",
            "External records must pass the intake validator before changing evidence counts.",
        ],
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "review_cases": review_cases,
            "pack_files": pack_files,
            "rollup": payload["rollup"],
        }
    )
    return payload


def validate_external_reproduction_kit(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != "external_reproduction_kit.v1":
        errors.append("schema_version must be external_reproduction_kit.v1")
    if payload.get("generator") != REPRODUCTION_KIT_BUILDER:
        errors.append(f"generator must be {REPRODUCTION_KIT_BUILDER}")
    if payload.get("public_scope") != "external_reviewer_reproduction_kit":
        errors.append("public_scope must be external_reviewer_reproduction_kit")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("kit_status") != "repo_native_reproduction_kit_ready_external_execution_open":
        errors.append("kit_status must keep external execution open")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, required_paths=_kit_source_paths(), errors=errors)
    cases = payload.get("review_cases")
    if not isinstance(cases, list) or len(cases) < 7:
        errors.append("review_cases must contain at least 7 rows")
        cases = []
    if payload.get("review_case_count") != len(cases):
        errors.append("review_case_count must equal len(review_cases)")
    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            errors.append(f"review_cases[{index}] must be object")
            continue
        if case.get("status") != "external_execution_required":
            errors.append(f"review_cases[{index}].status must be external_execution_required")
        record_types = case.get("record_types")
        if not isinstance(record_types, list) or not record_types:
            errors.append(f"review_cases[{index}].record_types must be non-empty list")
        elif any(record_type not in RECORD_TYPES for record_type in record_types):
            errors.append(f"review_cases[{index}].record_types contains invalid type")
    contract = payload.get("pack_contract")
    if not isinstance(contract, Mapping):
        errors.append("pack_contract must be object")
        contract = {}
    if contract.get("export_cli") != PACK_EXPORTER:
        errors.append(f"pack_contract.export_cli must be {PACK_EXPORTER}")
    if contract.get("pack_validator") != PACK_VALIDATOR:
        errors.append(f"pack_contract.pack_validator must be {PACK_VALIDATOR}")
    pack_files = contract.get("pack_files")
    if not isinstance(pack_files, list) or "EXTERNAL_REPRODUCTION_README.md" not in pack_files:
        errors.append("pack_contract.pack_files must include EXTERNAL_REPRODUCTION_README.md")
        pack_files = []
    if contract.get("pack_file_count") != len(pack_files):
        errors.append("pack_contract.pack_file_count must equal len(pack_files)")
    commands = contract.get("commands")
    if not isinstance(commands, list) or "python3 scripts/ci/check_suite.py" not in commands:
        errors.append("pack_contract.commands must include canonical check suite")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    for field in ("external_reproduction_kit_ready", "export_cli_available", "record_schema_available"):
        if rollup.get(field) is not True:
            errors.append(f"rollup.{field} must be true")
    for field in (
        "external_execution_completed",
        "first_real_external_record_present",
        "fake_external_records_accepted",
        "external_validation_completed",
        "independent_backend_validated",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list) or "external validation completed" not in blocked:
        errors.append("blocked_claims must block external validation completion")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors


def external_evidence_record_template(*, record_type: str, review_case_id: str) -> Dict[str, Any]:
    return {
        "schema_version": "external_evidence_record.v1",
        "record_id": f"external-{record_type}-{review_case_id}",
        "record_type": record_type,
        "review_case_id": review_case_id,
        "reviewer": {
            "reviewer_kind": "independent_third_party",
            "name_or_handle": "",
            "organization": "",
            "conflict_of_interest_statement": "",
        },
        "attestation": {
            "attestation_kind": "third_party_signed_report",
            "signature_or_report_uri": "",
        },
        "reproduction": {
            "reviewed_commit_sha": "",
            "commands": [],
            "raw_outputs_or_report_uri": "",
            "output_artifacts": [],
            "exceptions_or_disagreements": [],
        },
        "claim_effect": {
            "external_validation_completed": False,
            "independent_reproduction_completed": False,
            "independent_backend_validated": False,
            "qualification_complete": False,
            "certification_go": False,
            "flight_readiness_go": False,
        },
    }


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_http_uri(value: Any) -> bool:
    return isinstance(value, str) and (value.startswith("https://") or value.startswith("http://"))


def validate_external_evidence_record(
    record: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    if record.get("schema_version") != "external_evidence_record.v1":
        errors.append("schema_version must be external_evidence_record.v1")
    if not _is_non_empty_string(record.get("record_id")):
        errors.append("record_id must be non-empty string")
    if record.get("record_type") not in RECORD_TYPES:
        errors.append("record_type must be a known external evidence record type")
    if not _is_non_empty_string(record.get("review_case_id")):
        errors.append("review_case_id must be non-empty string")
    elif repo_root is not None and record.get("review_case_id") not in set(_review_case_ids(repo_root)):
        errors.append("review_case_id must reference external validation review pack")

    reviewer = record.get("reviewer")
    if not isinstance(reviewer, Mapping):
        errors.append("reviewer must be object")
        reviewer = {}
    reviewer_kind = reviewer.get("reviewer_kind")
    if reviewer_kind in BAD_REVIEWER_KINDS:
        errors.append("reviewer_kind cannot be repository-native or internal")
    if reviewer_kind not in ALLOWED_REVIEWER_KINDS:
        errors.append("reviewer_kind must be independent_third_party, external_lab, or external_auditor")
    for field in ("name_or_handle", "organization", "conflict_of_interest_statement"):
        if not _is_non_empty_string(reviewer.get(field)):
            errors.append(f"reviewer.{field} must be non-empty string")

    attestation = record.get("attestation")
    if not isinstance(attestation, Mapping):
        errors.append("attestation must be object")
        attestation = {}
    attestation_kind = attestation.get("attestation_kind")
    if attestation_kind in BAD_ATTESTATION_KINDS:
        errors.append("attestation_kind cannot be self-signed or repository-native")
    if attestation_kind not in ALLOWED_ATTESTATION_KINDS:
        errors.append("attestation_kind must be an external report or notarized record kind")
    if not _is_http_uri(attestation.get("signature_or_report_uri")):
        errors.append("attestation.signature_or_report_uri must be http(s) URI")

    reproduction = record.get("reproduction")
    if not isinstance(reproduction, Mapping):
        errors.append("reproduction must be object")
        reproduction = {}
    commit_sha = reproduction.get("reviewed_commit_sha")
    if not isinstance(commit_sha, str) or not SHA_RE.match(commit_sha):
        errors.append("reproduction.reviewed_commit_sha must be 40-char lowercase git sha")
    commands = reproduction.get("commands")
    if not isinstance(commands, list) or not commands or any(not _is_non_empty_string(command) for command in commands):
        errors.append("reproduction.commands must be a non-empty string list")
    if not _is_http_uri(reproduction.get("raw_outputs_or_report_uri")):
        errors.append("reproduction.raw_outputs_or_report_uri must be http(s) URI")
    artifacts = reproduction.get("output_artifacts")
    if not isinstance(artifacts, list):
        errors.append("reproduction.output_artifacts must be list")
    exceptions = reproduction.get("exceptions_or_disagreements")
    if not isinstance(exceptions, list):
        errors.append("reproduction.exceptions_or_disagreements must be list")

    claim_effect = record.get("claim_effect")
    if not isinstance(claim_effect, Mapping):
        errors.append("claim_effect must be object")
        claim_effect = {}
    for field in CLAIM_EFFECT_FIELDS:
        if not _is_bool(claim_effect.get(field)):
            errors.append(f"claim_effect.{field} must be boolean")
        if claim_effect.get(field) is True:
            errors.append(f"claim_effect.{field} cannot be true in external_evidence_record.v1 intake")
    return errors


def _record_files(records_dir: Path) -> List[Path]:
    if not records_dir.exists():
        return []
    return sorted(path for path in records_dir.glob("*.json") if path.is_file())


def build_external_evidence_intake(repo_root: Path, records_dir: Path | None = None) -> Dict[str, Any]:
    records_rel = EXTERNAL_RECORDS_DIR
    records_path = records_dir if records_dir is not None else repo_root / EXTERNAL_RECORDS_DIR
    record_files = _record_files(records_path)
    accepted_records: List[Dict[str, Any]] = []
    rejected_records: List[Dict[str, Any]] = []
    for path in record_files:
        try:
            record = _load_json(path)
        except json.JSONDecodeError as exc:
            rejected_records.append({"path": str(path), "errors": [f"invalid JSON: {exc}"]})
            continue
        errors = validate_external_evidence_record(record, repo_root=repo_root)
        summary = {
            "path": str(path.relative_to(repo_root)) if path.is_relative_to(repo_root) else str(path),
            "record_id": record.get("record_id"),
            "record_type": record.get("record_type"),
            "review_case_id": record.get("review_case_id"),
        }
        if errors:
            rejected_records.append({**summary, "errors": errors})
        else:
            accepted_records.append(summary)

    payload: Dict[str, Any] = {
        "schema_version": "external_evidence_intake.v1",
        "generator": EVIDENCE_INTAKE_BUILDER,
        "public_scope": "external_evidence_record_intake",
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, _intake_source_paths()),
        "intake_status": "external_record_intake_ready_awaiting_external_submission"
        if not accepted_records
        else "external_records_present_pending_claim_promotion_review",
        "record_schema_ref": EVIDENCE_RECORD_SCHEMA,
        "external_records_dir": records_rel,
        "record_count": len(record_files),
        "accepted_record_count": len(accepted_records),
        "rejected_record_count": len(rejected_records),
        "accepted_records": accepted_records,
        "rejected_records": rejected_records,
        "record_templates": [
            external_evidence_record_template(
                record_type="independent_reproduction",
                review_case_id="independent-backend-comparison",
            ),
            external_evidence_record_template(
                record_type="independent_physics_backend",
                review_case_id="independent-backend-comparison",
            ),
            external_evidence_record_template(
                record_type="capsule_qualification",
                review_case_id="media-decay-severe-mode",
            ),
        ],
        "validation_policy": {
            "reject_repository_maintainer_as_external": True,
            "reject_self_signed_repo_native_records": True,
            "require_external_attestation_uri": True,
            "require_raw_outputs_or_report_uri": True,
            "records_do_not_directly_unlock_claims": True,
            "claim_promotion_requires_followup_review": True,
        },
        "rollup": {
            "intake_contract_ready": True,
            "record_schema_available": True,
            "record_count": len(record_files),
            "accepted_record_count": len(accepted_records),
            "rejected_record_count": len(rejected_records),
            "first_real_external_record_present": len(accepted_records) > 0,
            "self_signed_records_accepted": False,
            "external_validation_completed": False,
            "independent_reproduction_completed": False,
            "independent_backend_validated": False,
            "qualification_complete": False,
            "certification_go": False,
            "flight_readiness_go": False,
        },
        "blocked_claims": list(BLOCKED_CLAIMS),
        "external_evidence_gaps": [
            "first accepted independent reproduction record",
            "independent backend comparison record",
            "capsule lab qualification records",
            "public immutable report URIs or signed attestations",
        ],
        "interpretation_limits": [
            "An accepted record is evidence intake, not automatic claim promotion.",
            "Self-signed repository-native records are rejected.",
            "Certification, qualification, and flight-readiness remain blocked in v1.",
        ],
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "record_count": payload["record_count"],
            "accepted_records": accepted_records,
            "rejected_records": rejected_records,
            "rollup": payload["rollup"],
        }
    )
    return payload


def validate_external_evidence_intake(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    records_dir: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != "external_evidence_intake.v1":
        errors.append("schema_version must be external_evidence_intake.v1")
    if payload.get("generator") != EVIDENCE_INTAKE_BUILDER:
        errors.append(f"generator must be {EVIDENCE_INTAKE_BUILDER}")
    if payload.get("public_scope") != "external_evidence_record_intake":
        errors.append("public_scope must be external_evidence_record_intake")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("record_schema_ref") != EVIDENCE_RECORD_SCHEMA:
        errors.append(f"record_schema_ref must be {EVIDENCE_RECORD_SCHEMA}")
    if payload.get("external_records_dir") != EXTERNAL_RECORDS_DIR:
        errors.append(f"external_records_dir must be {EXTERNAL_RECORDS_DIR}")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, required_paths=_intake_source_paths(), errors=errors)
        expected = build_external_evidence_intake(repo_root, records_dir=records_dir)
        for field in (
            "intake_status",
            "record_count",
            "accepted_record_count",
            "rejected_record_count",
            "accepted_records",
            "rejected_records",
        ):
            if payload.get(field) != expected.get(field):
                errors.append(f"{field} must match validated records in {expected.get('external_records_dir')}")
    for field in ("record_count", "accepted_record_count", "rejected_record_count"):
        if not isinstance(payload.get(field), int) or int(payload.get(field, -1)) < 0:
            errors.append(f"{field} must be non-negative integer")
    if payload.get("record_count") != int(payload.get("accepted_record_count", 0)) + int(
        payload.get("rejected_record_count", 0)
    ):
        errors.append("record_count must equal accepted_record_count + rejected_record_count")
    policy = payload.get("validation_policy")
    if not isinstance(policy, Mapping):
        errors.append("validation_policy must be object")
        policy = {}
    for field in (
        "reject_repository_maintainer_as_external",
        "reject_self_signed_repo_native_records",
        "require_external_attestation_uri",
        "require_raw_outputs_or_report_uri",
        "records_do_not_directly_unlock_claims",
        "claim_promotion_requires_followup_review",
    ):
        if policy.get(field) is not True:
            errors.append(f"validation_policy.{field} must be true")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("intake_contract_ready") is not True:
        errors.append("rollup.intake_contract_ready must be true")
    if rollup.get("record_count") != payload.get("record_count"):
        errors.append("rollup.record_count must equal record_count")
    if rollup.get("accepted_record_count") != payload.get("accepted_record_count"):
        errors.append("rollup.accepted_record_count must equal accepted_record_count")
    if rollup.get("first_real_external_record_present") != (int(payload.get("accepted_record_count", 0)) > 0):
        errors.append("rollup.first_real_external_record_present must reflect accepted_record_count")
    for field in (
        "self_signed_records_accepted",
        "external_validation_completed",
        "independent_reproduction_completed",
        "independent_backend_validated",
        "qualification_complete",
        "certification_go",
        "flight_readiness_go",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list) or "external validation completed" not in blocked:
        errors.append("blocked_claims must block external validation completion")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors


def _copy_pack_sources(repo_root: Path, pack_root: Path) -> List[str]:
    copied: List[str] = []
    for rel in PACK_SOURCE_FILES:
        src = repo_root / rel
        dest = pack_root / "repository" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(str(dest.relative_to(pack_root)))
    return copied


def _pack_readme() -> str:
    return "\n".join(
        [
            "# External Reproduction Pack v1",
            "",
            "This pack is a reviewer handoff. It is not an external validation record by itself.",
            "",
            "Run the commands in `commands/reproduction_commands.txt` from a fresh checkout of the referenced commit.",
            "Submit results using `templates/external_evidence_record_template.v1.json` only when an independent reviewer can attach raw outputs or an immutable report URI.",
            "",
            "Repository maintainers, internal CI logs, and self-signed records are rejected by the intake validator.",
            "",
        ]
    )


def export_external_reproduction_pack(
    *,
    repo_root: Path,
    output_dir: Path,
    make_zip: bool = True,
) -> Dict[str, Any]:
    pack_root = output_dir
    if pack_root.exists():
        shutil.rmtree(pack_root)
    pack_root.mkdir(parents=True)
    copied = _copy_pack_sources(repo_root, pack_root)

    (pack_root / "EXTERNAL_REPRODUCTION_README.md").write_text(_pack_readme(), encoding="utf-8")
    commands_path = pack_root / "commands" / "reproduction_commands.txt"
    commands_path.parent.mkdir(parents=True, exist_ok=True)
    commands_path.write_text("\n".join(REPRODUCTION_COMMANDS) + "\n", encoding="utf-8")

    template = external_evidence_record_template(
        record_type="independent_reproduction",
        review_case_id="independent-backend-comparison",
    )
    _write_json(pack_root / "templates" / "external_evidence_record_template.v1.json", template)

    pack_files = [
        "EXTERNAL_REPRODUCTION_README.md",
        "commands/reproduction_commands.txt",
        "templates/external_evidence_record_template.v1.json",
        *copied,
    ]
    manifest = {
        "schema_version": "external_reproduction_pack.v1",
        "source_commit_sha": _git_head(repo_root),
        "kit_artifact_ref": REPRODUCTION_KIT_ARTIFACT,
        "evidence_intake_artifact_ref": EVIDENCE_INTAKE_ARTIFACT,
        "record_schema_ref": EVIDENCE_RECORD_SCHEMA,
        "pack_files": ["manifest/external_reproduction_pack_manifest.v1.json", *pack_files],
        "commands": list(REPRODUCTION_COMMANDS),
        "non_certification_notice": True,
    }
    _write_json(pack_root / "manifest" / "external_reproduction_pack_manifest.v1.json", manifest)

    zip_path: Path | None = None
    if make_zip:
        zip_path = pack_root.with_suffix(".zip")
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(pack_root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(pack_root))

    return {
        "pack_root": pack_root,
        "zip_path": zip_path,
        "manifest": manifest,
    }


def validate_exported_external_reproduction_pack(pack_root: Path) -> List[str]:
    errors: List[str] = []
    required = [
        "EXTERNAL_REPRODUCTION_README.md",
        "commands/reproduction_commands.txt",
        "templates/external_evidence_record_template.v1.json",
        "manifest/external_reproduction_pack_manifest.v1.json",
    ]
    for rel in required:
        if not (pack_root / rel).is_file():
            errors.append(f"missing pack file: {rel}")
    manifest_path = pack_root / "manifest" / "external_reproduction_pack_manifest.v1.json"
    if manifest_path.is_file():
        manifest = _load_json(manifest_path)
        if manifest.get("schema_version") != "external_reproduction_pack.v1":
            errors.append("manifest.schema_version must be external_reproduction_pack.v1")
        files = manifest.get("pack_files")
        if not isinstance(files, list):
            errors.append("manifest.pack_files must be list")
            files = []
        for rel in required:
            if rel not in files:
                errors.append(f"manifest.pack_files missing {rel}")
    template_path = pack_root / "templates" / "external_evidence_record_template.v1.json"
    if template_path.is_file():
        template = _load_json(template_path)
        if template.get("schema_version") != "external_evidence_record.v1":
            errors.append("template.schema_version must be external_evidence_record.v1")
        if template.get("claim_effect", {}).get("certification_go") is not False:
            errors.append("template must not unlock certification")
    return errors
