"""External validation campaign artifacts.

The campaign layer coordinates the six external-proof workstreams without
turning repository-native evidence into third-party validation, lab
qualification, or public-claim approval.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .backend_environment import (
    build_independent_backend_execution_plan,
    build_line_of_sight_environment_model,
    validate_independent_backend_execution_plan,
    validate_line_of_sight_environment_model,
)


SOURCE_IMPLEMENTATION = "mission/validation_campaign/campaign.py"
SOURCE_BACKEND_ENVIRONMENT_IMPLEMENTATION = "mission/validation_campaign/backend_environment.py"
SOURCE_INIT = "mission/validation_campaign/__init__.py"
SOURCE_ARTIFACT_POLICY = "docs/ARTIFACT_POLICY.md"
SOURCE_ENVIRONMENT_BRIEF = "docs/research/CAPSULE_ENVIRONMENT_DATA_BRIEF_v1.md"
SOURCE_CAPSULE_DESIGN = "mission/capsule/capsule_design.v1.json"
SOURCE_REVIEW_PACK = "artifacts/external_validation_review_pack.v1.json"
SOURCE_PHYSICS_COMPARISON = "artifacts/independent_physics_backend_comparison.v1.json"
SOURCE_CAPSULE_QUALIFICATION = "artifacts/capsule_qualification_evidence_pack.v1.json"
SOURCE_REPRODUCTION_KIT = "artifacts/external_reproduction_kit.v1.json"
SOURCE_EVIDENCE_INTAKE = "artifacts/external_evidence_intake.v1.json"
SOURCE_PUBLIC_NARRATIVE = "artifacts/public_narrative_hardening.v1.json"

CAMPAIGN_SPEC = "mission/EXTERNAL_VALIDATION_CAMPAIGN_SPEC_v1.md"
CAMPAIGN_BUILDER = "scripts/build_external_validation_campaign_artifact.py"
CAMPAIGN_VALIDATOR = "scripts/ci/external_validation_campaign_validate.py"
CAMPAIGN_ARTIFACT = "artifacts/external_validation_campaign.v1.json"

QUALIFICATION_TRACKS = [
    ("ballistic-limit", "Stack-level dust/fragment ballistic-limit evidence"),
    ("hydrocode-correlation", "Hydrocode correlation against representative impact tests"),
    ("radiation-transport", "Material-specific GCR/TID/SEE radiation-transport evidence"),
    ("archive-media-aging", "Long-duration archive-media aging evidence"),
    ("ecc-recovery", "Error-correction and redundant-media recovery campaign"),
    ("independent-review", "Independent reviewer/lab qualification dossier"),
]

PROMOTION_CLAIMS = [
    "external validation completed",
    "independent reproduction completed",
    "independent physics backend validated",
    "high-fidelity state trace complete",
    "qualification complete",
    "certified",
    "flight-ready",
    "public claim approval complete",
]

BLOCKED_CLAIMS = [
    "external validation completed",
    "third-party validated",
    "independent reproduction completed",
    "independent physics backend validated",
    "cross-backend comparison completed",
    "high-fidelity state trace complete",
    "fixed mm/cm dust truth",
    "line-of-sight environment validated",
    "qualification complete",
    "qualified",
    "certified",
    "flight-ready",
    "legal or public approval complete",
    "public claim approval complete",
    "source correctness proven",
]


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


def _determinism_signature(parts: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


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


def _common_source_paths() -> List[str]:
    return [
        CAMPAIGN_SPEC,
        SOURCE_IMPLEMENTATION,
        SOURCE_BACKEND_ENVIRONMENT_IMPLEMENTATION,
        SOURCE_INIT,
        CAMPAIGN_BUILDER,
        CAMPAIGN_VALIDATOR,
        SOURCE_ARTIFACT_POLICY,
    ]


def _campaign_source_paths() -> List[str]:
    return [
        SOURCE_PHYSICS_COMPARISON,
        SOURCE_CAPSULE_QUALIFICATION,
        SOURCE_REPRODUCTION_KIT,
        SOURCE_EVIDENCE_INTAKE,
        SOURCE_PUBLIC_NARRATIVE,
        SOURCE_REVIEW_PACK,
        SOURCE_CAPSULE_DESIGN,
        SOURCE_ENVIRONMENT_BRIEF,
        *_common_source_paths(),
    ]


def _unique(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(values))


def _accepted_records(intake_payload: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    records = intake_payload.get("accepted_records")
    if isinstance(records, list):
        return [record for record in records if isinstance(record, Mapping)]
    return []


def _rollup_bool(payload: Mapping[str, Any], field: str) -> bool:
    rollup = payload.get("rollup")
    if isinstance(rollup, Mapping):
        return bool(rollup.get(field))
    return False


def build_capsule_qualification_program(repo_root: Path) -> Dict[str, Any]:
    pack = _load_json(repo_root / SOURCE_CAPSULE_QUALIFICATION)
    design = _load_json(repo_root / SOURCE_CAPSULE_DESIGN)
    tracks = [
        {
            "track_id": track_id,
            "title": title,
            "status": "external_required",
            "external_required": True,
            "lab_record_count": 0,
            "repo_native_evidence": SOURCE_CAPSULE_QUALIFICATION,
        }
        for track_id, title in QUALIFICATION_TRACKS
    ]
    payload: Dict[str, Any] = {
        "schema_version": "capsule_qualification_program.v1",
        "generator": CAMPAIGN_BUILDER,
        "public_scope": "capsule_qualification_program_boundary",
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(
            repo_root,
            [SOURCE_CAPSULE_QUALIFICATION, SOURCE_CAPSULE_DESIGN, *_common_source_paths()],
        ),
        "qualification_program_status": "planned_external_records_required",
        "capsule_design_ref": SOURCE_CAPSULE_DESIGN,
        "configured_capsule_mass_kg": design.get("mass_budget", {}).get("configured_capsule_mass_kg"),
        "material_count": len(design.get("materials", [])) if isinstance(design.get("materials"), list) else 0,
        "track_count": len(tracks),
        "lab_record_count": 0,
        "lab_records": [],
        "qualification_test_count": int(pack.get("qualification_test_count", len(tracks))),
        "qualification_tracks": tracks,
        "rollup": {
            "all_tracks_external_required": True,
            "lab_record_count": 0,
            "track_count": len(tracks),
            "qualification_complete": False,
            "certification_claimed": False,
            "certification_go": False,
            "flight_ready_claimed": False,
            "legal_public_approval_claimed": False,
        },
        "blocked_claims": _unique(
            [
                "qualification complete",
                "certified",
                "flight-ready",
                "legal or public approval complete",
                *BLOCKED_CLAIMS,
            ]
        ),
        "external_evidence_gaps": [
            "stack-level ballistic-limit records",
            "hydrocode/lab correlation report",
            "radiation transport and media-aging records",
            "independent qualification review",
        ],
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "qualification_tracks": payload["qualification_tracks"],
            "rollup": payload["rollup"],
        }
    )
    return payload


def validate_capsule_qualification_program(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != "capsule_qualification_program.v1":
        errors.append("schema_version must be capsule_qualification_program.v1")
    if payload.get("generator") != CAMPAIGN_BUILDER:
        errors.append(f"generator must be {CAMPAIGN_BUILDER}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("qualification_program_status") != "planned_external_records_required":
        errors.append("qualification_program_status must require external records")
    if repo_root is not None:
        _validate_sources(
            repo_root=repo_root,
            payload=payload,
            required_paths=[SOURCE_CAPSULE_QUALIFICATION, SOURCE_CAPSULE_DESIGN, *_common_source_paths()],
            errors=errors,
        )
    tracks = payload.get("qualification_tracks")
    if not isinstance(tracks, list) or [track.get("track_id") for track in tracks if isinstance(track, Mapping)] != [
        track_id for track_id, _ in QUALIFICATION_TRACKS
    ]:
        errors.append("qualification_tracks must match required track ids")
        tracks = []
    for index, track in enumerate(tracks):
        if not isinstance(track, Mapping):
            errors.append(f"qualification_tracks[{index}] must be object")
            continue
        if track.get("status") != "external_required":
            errors.append(f"qualification_tracks[{index}].status must be external_required")
        if track.get("external_required") is not True:
            errors.append(f"qualification_tracks[{index}].external_required must be true")
        if track.get("lab_record_count") != 0:
            errors.append(f"qualification_tracks[{index}].lab_record_count must be 0")
    if payload.get("lab_record_count") != 0:
        errors.append("lab_record_count must be 0")
    if payload.get("lab_records") != []:
        errors.append("lab_records must be empty")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("all_tracks_external_required") is not True:
        errors.append("rollup.all_tracks_external_required must be true")
    for field in (
        "qualification_complete",
        "certification_claimed",
        "certification_go",
        "flight_ready_claimed",
        "legal_public_approval_claimed",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list) or "qualification complete" not in blocked:
        errors.append("blocked_claims must block qualification complete")
    if isinstance(blocked, list):
        for claim in ("certified", "flight-ready", "legal or public approval complete"):
            if claim not in blocked:
                errors.append(f"blocked_claims must block {claim}")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors


def build_proof_promotion_review(
    repo_root: Path,
    *,
    intake_payload: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    intake = dict(intake_payload) if intake_payload is not None else _load_json(repo_root / SOURCE_EVIDENCE_INTAKE)
    accepted_records = _accepted_records(intake)
    claim_reviews = [
        {
            "claim": claim,
            "decision": "followup_review_required" if accepted_records else "external_record_required",
            "promotion_allowed": False,
            "promoted": False,
            "accepted_record_count": len(accepted_records),
        }
        for claim in PROMOTION_CLAIMS
    ]
    payload: Dict[str, Any] = {
        "schema_version": "proof_promotion_review.v1",
        "generator": CAMPAIGN_BUILDER,
        "public_scope": "claim_promotion_review_boundary",
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, [SOURCE_EVIDENCE_INTAKE, *_common_source_paths()]),
        "promotion_review_status": "blocked_until_valid_external_records",
        "reviewed_record_count": len(accepted_records),
        "reviewed_records": [
            {
                "record_id": record.get("record_id"),
                "record_type": record.get("record_type"),
                "review_case_id": record.get("review_case_id"),
            }
            for record in accepted_records
        ],
        "review_policy": {
            "records_do_not_directly_unlock_claims": True,
            "proof_promotion_requires_followup_review": True,
            "v1_auto_promotion_enabled": False,
        },
        "claim_reviews": claim_reviews,
        "rollup": {
            "accepted_record_count": int(intake.get("accepted_record_count", len(accepted_records))),
            "first_real_external_record_present": bool(_rollup_bool(intake, "first_real_external_record_present")),
            "reviewed_record_count": len(accepted_records),
            "promoted_claim_count": 0,
            "external_validation_completed": False,
            "automatic_claim_promotion_allowed": False,
        },
        "blocked_claims": _unique(["automatic claim promotion", *PROMOTION_CLAIMS, *BLOCKED_CLAIMS]),
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "claim_reviews": payload["claim_reviews"],
            "rollup": payload["rollup"],
        }
    )
    return payload


def validate_proof_promotion_review(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != "proof_promotion_review.v1":
        errors.append("schema_version must be proof_promotion_review.v1")
    if payload.get("generator") != CAMPAIGN_BUILDER:
        errors.append(f"generator must be {CAMPAIGN_BUILDER}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("promotion_review_status") != "blocked_until_valid_external_records":
        errors.append("promotion_review_status must remain blocked")
    if repo_root is not None:
        _validate_sources(
            repo_root=repo_root,
            payload=payload,
            required_paths=[SOURCE_EVIDENCE_INTAKE, *_common_source_paths()],
            errors=errors,
        )
    policy = payload.get("review_policy")
    if not isinstance(policy, Mapping):
        errors.append("review_policy must be object")
        policy = {}
    if policy.get("records_do_not_directly_unlock_claims") is not True:
        errors.append("review_policy.records_do_not_directly_unlock_claims must be true")
    if policy.get("proof_promotion_requires_followup_review") is not True:
        errors.append("review_policy.proof_promotion_requires_followup_review must be true")
    if policy.get("v1_auto_promotion_enabled") is not False:
        errors.append("review_policy.v1_auto_promotion_enabled must be false")
    reviews = payload.get("claim_reviews")
    if not isinstance(reviews, list) or not reviews:
        errors.append("claim_reviews must be non-empty")
        reviews = []
    for index, review in enumerate(reviews):
        if not isinstance(review, Mapping):
            errors.append(f"claim_reviews[{index}] must be object")
            continue
        if review.get("promotion_allowed") is not False:
            errors.append(f"claim_reviews[{index}].promotion_allowed must be false")
        if review.get("promoted") is not False:
            errors.append(f"claim_reviews[{index}].promoted must be false")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    for field in ("promoted_claim_count",):
        if rollup.get(field) != 0:
            errors.append(f"rollup.{field} must be 0")
    for field in ("external_validation_completed", "automatic_claim_promotion_allowed"):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors


def build_public_evidence_dossier(repo_root: Path) -> Dict[str, Any]:
    design = _load_json(repo_root / SOURCE_CAPSULE_DESIGN)
    review_pack = _load_json(repo_root / SOURCE_REVIEW_PACK)
    intake = _load_json(repo_root / SOURCE_EVIDENCE_INTAKE)
    qualification = build_capsule_qualification_program(repo_root)
    material_count = len(design.get("materials", [])) if isinstance(design.get("materials"), list) else 0
    review_cases = review_pack.get("review_cases", [])
    review_case_count = len(review_cases) if isinstance(review_cases, list) else 0
    payload: Dict[str, Any] = {
        "schema_version": "public_evidence_dossier.v1",
        "generator": CAMPAIGN_BUILDER,
        "public_scope": "reviewer_facing_evidence_boundary",
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(
            repo_root,
            [
                SOURCE_CAPSULE_DESIGN,
                SOURCE_REVIEW_PACK,
                SOURCE_EVIDENCE_INTAKE,
                SOURCE_CAPSULE_QUALIFICATION,
                *_common_source_paths(),
            ],
        ),
        "dossier_status": "repo_native_dossier_ready_external_records_open",
        "external_record_count": int(intake.get("record_count", 0)),
        "accepted_external_record_count": int(intake.get("accepted_record_count", 0)),
        "qualification_program": qualification,
        "dossier_sections": {
            "design_evidence": {
                "artifact_ref": SOURCE_CAPSULE_DESIGN,
                "material_count": material_count,
                "configured_capsule_mass_kg": design.get("mass_budget", {}).get("configured_capsule_mass_kg"),
            },
            "qualification_program": {
                "artifact_ref": SOURCE_CAPSULE_QUALIFICATION,
                "track_count": len(qualification.get("qualification_tracks", [])),
                "lab_record_count": qualification.get("lab_record_count", 0),
            },
            "external_review": {
                "artifact_ref": SOURCE_REVIEW_PACK,
                "review_case_count": review_case_count,
                "accepted_external_record_count": int(intake.get("accepted_record_count", 0)),
            },
            "claim_boundary": {
                "blocked_claim_count": len(BLOCKED_CLAIMS),
                "shows_blocked_claims": True,
                "certification_language_allowed": False,
            },
        },
        "claim_status": {
            "qualification_complete": False,
            "certification_claimed": False,
            "flight_ready_claimed": False,
            "legal_public_approval_claimed": False,
            "public_claim_approval_claimed": False,
        },
        "approved_public_claims": [],
        "blocked_claims": list(BLOCKED_CLAIMS),
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "dossier_sections": payload["dossier_sections"],
            "claim_status": payload["claim_status"],
        }
    )
    return payload


def validate_public_evidence_dossier(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != "public_evidence_dossier.v1":
        errors.append("schema_version must be public_evidence_dossier.v1")
    if payload.get("generator") != CAMPAIGN_BUILDER:
        errors.append(f"generator must be {CAMPAIGN_BUILDER}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("dossier_status") != "repo_native_dossier_ready_external_records_open":
        errors.append("dossier_status must keep external records open")
    if payload.get("public_scope") != "reviewer_facing_evidence_boundary":
        errors.append("public_scope must be reviewer_facing_evidence_boundary")
    if repo_root is not None:
        _validate_sources(
            repo_root=repo_root,
            payload=payload,
            required_paths=[
                SOURCE_CAPSULE_DESIGN,
                SOURCE_REVIEW_PACK,
                SOURCE_EVIDENCE_INTAKE,
                SOURCE_CAPSULE_QUALIFICATION,
                *_common_source_paths(),
            ],
            errors=errors,
        )
    if payload.get("external_record_count") != 0:
        errors.append("external_record_count must be 0")
    if payload.get("accepted_external_record_count") != 0:
        errors.append("accepted_external_record_count must be 0")
    qualification = payload.get("qualification_program")
    if not isinstance(qualification, Mapping):
        errors.append("qualification_program must be object")
    else:
        errors.extend(
            "qualification_program." + error
            for error in validate_capsule_qualification_program(qualification, repo_root=repo_root)
        )
    sections = payload.get("dossier_sections")
    if not isinstance(sections, Mapping):
        errors.append("dossier_sections must be object")
        sections = {}
    claim_boundary = sections.get("claim_boundary") if isinstance(sections, Mapping) else {}
    if not isinstance(claim_boundary, Mapping) or claim_boundary.get("shows_blocked_claims") is not True:
        errors.append("dossier_sections.claim_boundary.shows_blocked_claims must be true")
    if isinstance(claim_boundary, Mapping) and claim_boundary.get("certification_language_allowed") is not False:
        errors.append("dossier_sections.claim_boundary.certification_language_allowed must be false")
    status = payload.get("claim_status")
    if not isinstance(status, Mapping):
        errors.append("claim_status must be object")
        status = {}
    for field in (
        "qualification_complete",
        "certification_claimed",
        "flight_ready_claimed",
        "legal_public_approval_claimed",
        "public_claim_approval_claimed",
    ):
        if status.get(field) is not False:
            errors.append(f"claim_status.{field} must be false")
    if payload.get("approved_public_claims") != []:
        errors.append("approved_public_claims must be empty")
    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list):
        errors.append("blocked_claims must be list")
    else:
        for claim in ("qualification complete", "certified", "flight-ready", "legal or public approval complete"):
            if claim not in blocked:
                errors.append(f"blocked_claims must block {claim}")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors


def build_external_validation_campaign(repo_root: Path) -> Dict[str, Any]:
    intake = _load_json(repo_root / SOURCE_EVIDENCE_INTAKE)
    backend = build_independent_backend_execution_plan(repo_root)
    environment = build_line_of_sight_environment_model(repo_root)
    qualification = build_capsule_qualification_program(repo_root)
    promotion = build_proof_promotion_review(repo_root, intake_payload=intake)
    dossier = build_public_evidence_dossier(repo_root)
    backend_snapshot = backend.get("readiness_snapshot", {}) if isinstance(backend.get("readiness_snapshot"), Mapping) else {}
    backend_repo_analytic_count = int(
        backend.get("repo_analytic_check_count", backend_snapshot.get("repo_analytic_check_count", 0))
    )
    backend_deliverables = backend.get("required_external_deliverables")
    if not isinstance(backend_deliverables, list):
        backend_deliverables = []
        for track in backend.get("execution_tracks", []):
            if isinstance(track, Mapping):
                evidence = track.get("acceptance_evidence", [])
                if isinstance(evidence, list):
                    backend_deliverables.extend(str(item) for item in evidence if isinstance(item, str))
    accepted_count = int(intake.get("accepted_record_count", 0))
    workstreams = [
        {
            "workstream_id": "first-real-external-record",
            "status": "external_required",
            "evidence_ref": SOURCE_EVIDENCE_INTAKE,
            "current_accepted_record_count": accepted_count,
        },
        {
            "workstream_id": "independent-physics-backend",
            "status": "external_required",
            "evidence_ref": SOURCE_PHYSICS_COMPARISON,
            "current_accepted_record_count": accepted_count,
        },
        {
            "workstream_id": "capsule-qualification-program",
            "status": "external_required",
            "evidence_ref": SOURCE_CAPSULE_QUALIFICATION,
            "current_accepted_record_count": accepted_count,
        },
        {
            "workstream_id": "line-of-sight-environment-model",
            "status": "direction_dependent_model_required",
            "evidence_ref": SOURCE_ENVIRONMENT_BRIEF,
            "current_accepted_record_count": accepted_count,
        },
        {
            "workstream_id": "proof-promotion-review",
            "status": "blocked_until_valid_external_records",
            "evidence_ref": SOURCE_EVIDENCE_INTAKE,
            "current_accepted_record_count": accepted_count,
        },
        {
            "workstream_id": "public-evidence-dossier",
            "status": "repo_dossier_ready_external_records_absent",
            "evidence_ref": CAMPAIGN_ARTIFACT,
            "current_accepted_record_count": accepted_count,
        },
    ]
    payload: Dict[str, Any] = {
        "schema_version": "external_validation_campaign.v1",
        "generator": CAMPAIGN_BUILDER,
        "public_scope": "six_workstream_external_validation_campaign",
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, _campaign_source_paths()),
        "campaign_status": "repo_campaign_ready_external_execution_required",
        "campaign_policy": {
            "records_do_not_directly_unlock_claims": True,
            "proof_promotion_requires_followup_review": True,
            "repo_native_artifacts_are_not_external_records": True,
        },
        "workstream_count": len(workstreams),
        "workstreams": workstreams,
        "independent_backend_execution_plan": {
            "status": "external_required",
            "repo_analytic_check_count": backend_repo_analytic_count,
            "independent_external_backend_complete": False,
            "high_fidelity_state_trace_complete": False,
            "required_deliverables": backend_deliverables,
        },
        "line_of_sight_environment_model": {
            "status": "direction_dependent_model_required",
            "source_backed_anchors": environment["source_backed_anchors"],
            "assumption_bound_families": [
                "exact mm/cm interstellar dust flux over Myr horizons",
                "target-region plasma for black-hole approach",
                "line-of-sight ISM average for selected target",
            ],
            "line_of_sight_rows": environment["line_of_sight_rows"],
            "rollup": {
                "line_of_sight_model_complete": False,
                "target_region_environment_calibrated": False,
                "fixed_mm_cm_dust_truth_claimed": False,
            },
        },
        "capsule_qualification_program": {
            "status": "external_required",
            "lab_record_count": qualification["lab_record_count"],
            "test_count": qualification["qualification_test_count"],
            "qualification_tracks": qualification["qualification_tracks"],
            "qualification_complete": False,
            "certification_go": False,
            "flight_ready_claimed": False,
        },
        "proof_promotion_review": {
            "status": "blocked_until_valid_external_records",
            "requires_followup_review": True,
            "automatic_claim_promotion_allowed": False,
            "promoted_claims": [],
            "rollup": promotion["rollup"],
            "claim_reviews": promotion["claim_reviews"],
        },
        "public_evidence_dossier": {
            "status": "repo_dossier_ready_external_records_absent",
            "sections": list(dossier["dossier_sections"].keys()),
            "shows_blocked_claims": True,
            "marketing_claim_surface": False,
            "certification_language_allowed": False,
            "public_claim_approval_completed": False,
        },
        "rollup": {
            "campaign_ready": True,
            "workstream_count": len(workstreams),
            "accepted_record_count": accepted_count,
            "accepted_external_record_count": accepted_count,
            "first_real_external_record_present": False,
            "external_validation_completed": False,
            "independent_backend_validated": False,
            "line_of_sight_model_complete": False,
            "qualification_complete": False,
            "proof_promotion_applied": False,
            "public_dossier_ready": True,
            "certification_go": False,
        },
        "blocked_claims": list(BLOCKED_CLAIMS),
        "external_evidence_gaps": [
            "first accepted external evidence intake record",
            "independent backend execution report",
            "capsule lab qualification records",
            "direction-specific line-of-sight dust/plasma model",
            "manual proof-promotion review after valid records arrive",
            "public/legal wording approval outside the repository",
        ],
        "interpretation_limits": [
            "This artifact coordinates the campaign; it is not itself external evidence.",
            "No automatic claim promotion is allowed in v1, even if future records are accepted.",
            "The public dossier can show blocked claims but cannot approve certification language.",
        ],
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "workstreams": payload["workstreams"],
            "rollup": payload["rollup"],
            "campaign_policy": payload["campaign_policy"],
        }
    )
    return payload


def validate_external_validation_campaign(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != "external_validation_campaign.v1":
        errors.append("schema_version must be external_validation_campaign.v1")
    if payload.get("generator") != CAMPAIGN_BUILDER:
        errors.append(f"generator must be {CAMPAIGN_BUILDER}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("campaign_status") != "repo_campaign_ready_external_execution_required":
        errors.append("campaign_status must keep external execution required")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, required_paths=_campaign_source_paths(), errors=errors)
    policy = payload.get("campaign_policy")
    if not isinstance(policy, Mapping):
        errors.append("campaign_policy must be object")
        policy = {}
    for field in (
        "records_do_not_directly_unlock_claims",
        "proof_promotion_requires_followup_review",
        "repo_native_artifacts_are_not_external_records",
    ):
        if policy.get(field) is not True:
            errors.append(f"campaign_policy.{field} must be true")
    expected_ids = [
        "first-real-external-record",
        "independent-physics-backend",
        "capsule-qualification-program",
        "line-of-sight-environment-model",
        "proof-promotion-review",
        "public-evidence-dossier",
    ]
    workstreams = payload.get("workstreams")
    if not isinstance(workstreams, list):
        errors.append("workstreams must be list")
        workstreams = []
    if [row.get("workstream_id") for row in workstreams if isinstance(row, Mapping)] != expected_ids:
        errors.append("workstreams must contain the six required workstream ids in order")
    if payload.get("workstream_count") != 6:
        errors.append("workstream_count must be 6")
    if not any(
        isinstance(row, Mapping)
        and row.get("workstream_id") == "line-of-sight-environment-model"
        and row.get("status") == "direction_dependent_model_required"
        for row in workstreams
    ):
        errors.append("line-of-sight-environment-model status must be direction_dependent_model_required")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("campaign_ready") is not True:
        errors.append("rollup.campaign_ready must be true")
    if rollup.get("workstream_count") != 6:
        errors.append("rollup.workstream_count must be 6")
    for field in ("accepted_record_count", "accepted_external_record_count"):
        if rollup.get(field) != 0:
            errors.append(f"rollup.{field} must be 0")
    for field in (
        "first_real_external_record_present",
        "external_validation_completed",
        "independent_backend_validated",
        "line_of_sight_model_complete",
        "qualification_complete",
        "proof_promotion_applied",
        "certification_go",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    if rollup.get("public_dossier_ready") is not True:
        errors.append("rollup.public_dossier_ready must be true")

    backend = payload.get("independent_backend_execution_plan")
    if not isinstance(backend, Mapping):
        errors.append("independent_backend_execution_plan must be object")
        backend = {}
    if backend.get("status") != "external_required":
        errors.append("independent_backend_execution_plan.status must be external_required")
    if backend.get("repo_analytic_check_count") != 5:
        errors.append("independent_backend_execution_plan.repo_analytic_check_count must be 5")
    for field in ("independent_external_backend_complete", "high_fidelity_state_trace_complete"):
        if backend.get(field) is not False:
            errors.append(f"independent_backend_execution_plan.{field} must be false")

    environment = payload.get("line_of_sight_environment_model")
    if not isinstance(environment, Mapping):
        errors.append("line_of_sight_environment_model must be object")
        environment = {}
    if environment.get("status") != "direction_dependent_model_required":
        errors.append("line_of_sight_environment_model.status must be direction_dependent_model_required")
    anchors = environment.get("source_backed_anchors")
    if not isinstance(anchors, list) or len(anchors) < 4:
        errors.append("line_of_sight_environment_model.source_backed_anchors must contain at least 4 anchors")
    families = environment.get("assumption_bound_families")
    if not isinstance(families, list) or "exact mm/cm interstellar dust flux over Myr horizons" not in families:
        errors.append("line_of_sight_environment_model.assumption_bound_families must include exact mm/cm dust tail")
    environment_rollup = environment.get("rollup")
    if not isinstance(environment_rollup, Mapping):
        errors.append("line_of_sight_environment_model.rollup must be object")
        environment_rollup = {}
    for field in ("line_of_sight_model_complete", "target_region_environment_calibrated", "fixed_mm_cm_dust_truth_claimed"):
        if environment_rollup.get(field) is not False:
            errors.append(f"line_of_sight_environment_model.rollup.{field} must be false")
    if environment.get("line_of_sight_model_complete") is True:
        errors.append("line_of_sight_environment_model.line_of_sight_model_complete must not be true")

    qualification = payload.get("capsule_qualification_program")
    if not isinstance(qualification, Mapping):
        errors.append("capsule_qualification_program must be object")
        qualification = {}
    if qualification.get("status") != "external_required":
        errors.append("capsule_qualification_program.status must be external_required")
    if qualification.get("lab_record_count") != 0:
        errors.append("capsule_qualification_program.lab_record_count must be 0")
    if not isinstance(qualification.get("test_count"), int) or qualification.get("test_count") < 6:
        errors.append("capsule_qualification_program.test_count must be at least 6")
    for field in ("qualification_complete", "certification_go", "flight_ready_claimed"):
        if qualification.get(field) is not False:
            errors.append(f"capsule_qualification_program.{field} must be false")

    promotion = payload.get("proof_promotion_review")
    if not isinstance(promotion, Mapping):
        errors.append("proof_promotion_review must be object")
        promotion = {}
    if promotion.get("status") != "blocked_until_valid_external_records":
        errors.append("proof_promotion_review.status must be blocked_until_valid_external_records")
    if promotion.get("requires_followup_review") is not True:
        errors.append("proof_promotion_review.requires_followup_review must be true")
    if promotion.get("automatic_claim_promotion_allowed") is not False:
        errors.append("proof_promotion_review.automatic_claim_promotion_allowed must be false")
    if promotion.get("promoted_claims") != []:
        errors.append("proof_promotion_review.promoted_claims must be empty")

    dossier = payload.get("public_evidence_dossier")
    if not isinstance(dossier, Mapping):
        errors.append("public_evidence_dossier must be object")
        dossier = {}
    if dossier.get("status") != "repo_dossier_ready_external_records_absent":
        errors.append("public_evidence_dossier.status must be repo_dossier_ready_external_records_absent")
    for field in ("shows_blocked_claims",):
        if dossier.get(field) is not True:
            errors.append(f"public_evidence_dossier.{field} must be true")
    for field in ("marketing_claim_surface", "certification_language_allowed", "public_claim_approval_completed"):
        if dossier.get(field) is not False:
            errors.append(f"public_evidence_dossier.{field} must be false")

    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list):
        errors.append("blocked_claims must be list")
    else:
        for claim in ("certified", "flight-ready", "external validation completed", "fixed mm/cm dust truth"):
            if claim not in blocked:
                errors.append(f"blocked_claims must block {claim}")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors
