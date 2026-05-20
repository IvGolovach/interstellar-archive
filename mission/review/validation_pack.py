"""Roadmap item 14 external validation review-pack artifact."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


SCHEMA_VERSION = "external_validation_review_pack.v1"
GENERATOR = "scripts/build_external_validation_review_pack_artifact.py"
PUBLIC_SCOPE = "external_validation_independent_review_pack"
SOURCE_SPEC = "mission/EXTERNAL_VALIDATION_REVIEW_PACK_SPEC_v1.md"
SOURCE_IMPLEMENTATION = "mission/review/validation_pack.py"
SOURCE_BUILDER = "scripts/build_external_validation_review_pack_artifact.py"
SOURCE_VALIDATOR = "scripts/ci/external_validation_review_pack_validate.py"
SOURCE_GAPS = "docs/research/VALIDATION_AND_QUALIFICATION_GAPS_v1.md"
SOURCE_ROADMAP_DOC = "docs/FULL_V2_ROADMAP_CLOSURE.md"
SOURCE_ARTIFACT_POLICY = "docs/ARTIFACT_POLICY.md"
SOURCE_DAG_BOUNDARY = "artifacts/mission_dag_v2_boundary.v1.json"
SOURCE_EVIDENCE_UPGRADE = "artifacts/evidence_upgrade_campaign.v1.json"
SOURCE_RUNTIME_GENERATION = "artifacts/runtime_scenario_generation.v1.json"
SOURCE_COST_ARCHITECTURE = "artifacts/cost_procurement_architecture_feasibility.v1.json"
SOURCE_PROBABILITY_COUPLING = "artifacts/mission_probability_coupling.v1.json"
SOURCE_UNCERTAINTY_INTERACTIONS = "artifacts/uncertainty_interactions.v1.json"
SOURCE_CAPSULE_RISK = "artifacts/capsule_risk_budget.v1.json"
SOURCE_EVIDENCE_CLAIMS = "evidence/claims.json"
SOURCE_EVIDENCE_ASSUMPTIONS = "evidence/assumptions.json"
SOURCE_EVIDENCE_SOURCES = "evidence/sources.json"
SOURCE_EVIDENCE_PACK_META = "artifacts/evidence-pack-v1/metadata.json"
SOURCE_EVIDENCE_PACK_CHECKSUMS = "artifacts/evidence-pack-v1/checksums.sha256"

BLOCKED_CLAIMS = [
    "external validation completed",
    "independent reproduction completed",
    "independent physics backend validated",
    "cross-backend comparison completed",
    "high-fidelity state trace complete",
    "third-party validated",
    "certified",
    "qualified",
    "flight-ready",
    "proven mission feasible",
    "procurement-grade cost estimate",
    "vendor quote obtained",
    "regulatory or operations approval complete",
    "source correctness proven",
    "trust grades upgraded automatically",
    "persistent reviewed run archive",
]
DELIVERABLE_IDS = [
    "third_party_reproduction_report",
    "independent_physics_benchmark_report",
    "high_fidelity_state_trace_bundle",
    "external_red_team_report",
    "reviewer_exception_log",
    "public_claim_wording_audit",
]
REVIEW_CASE_DEFS = [
    {
        "id": "optimistic-prior-collapse",
        "title": "Optimistic prior collapse",
        "source_inputs": [SOURCE_PROBABILITY_COUPLING, SOURCE_EVIDENCE_UPGRADE],
        "review_questions": [
            "Which mission-probability factors are external and unclosed?",
            "Does any trust-grade promotion require independent source evidence?",
        ],
        "expected_failure_modes": ["source correctness proven", "trust grades upgraded automatically"],
        "external_deliverable_ids": ["third_party_reproduction_report", "reviewer_exception_log"],
    },
    {
        "id": "dust-tail-severe-mode",
        "title": "Dust-tail severe mode",
        "source_inputs": [SOURCE_CAPSULE_RISK, SOURCE_UNCERTAINTY_INTERACTIONS],
        "review_questions": [
            "Which dust-tail assumptions dominate failure pressure?",
            "What line-of-sight dust evidence is missing before risk can be treated as physical truth?",
        ],
        "expected_failure_modes": ["certified", "proven mission feasible"],
        "external_deliverable_ids": [
            "independent_physics_benchmark_report",
            "high_fidelity_state_trace_bundle",
            "reviewer_exception_log",
        ],
    },
    {
        "id": "media-decay-severe-mode",
        "title": "Archive media decay severe mode",
        "source_inputs": [SOURCE_CAPSULE_RISK, SOURCE_GAPS],
        "review_questions": [
            "Are physical survival and readable archive recovery separated?",
            "Which accelerated-aging and ECC recovery tests are still external?",
        ],
        "expected_failure_modes": ["qualified", "flight-ready"],
        "external_deliverable_ids": ["third_party_reproduction_report", "external_red_team_report", "reviewer_exception_log"],
    },
    {
        "id": "targetability-separated-from-capsule-survival",
        "title": "Targetability separated from capsule survival",
        "source_inputs": [SOURCE_PROBABILITY_COUPLING, SOURCE_RUNTIME_GENERATION],
        "review_questions": [
            "Does the artifact keep target delivery external instead of folding it into capsule survival?",
            "Do local run packs remain user-owned rather than reviewed repository truth?",
        ],
        "expected_failure_modes": ["persistent reviewed run archive", "proven mission feasible"],
        "external_deliverable_ids": ["third_party_reproduction_report", "external_red_team_report", "reviewer_exception_log"],
    },
    {
        "id": "independent-backend-comparison",
        "title": "Independent backend comparison",
        "source_inputs": [SOURCE_DAG_BOUNDARY],
        "review_questions": [
            "Which modules have only v1 wrapper support?",
            "What state traces and external backend records are required before independent validation can be claimed?",
        ],
        "expected_failure_modes": [
            "independent physics backend validated",
            "cross-backend comparison completed",
            "high-fidelity state trace complete",
        ],
        "external_deliverable_ids": [
            "independent_physics_benchmark_report",
            "high_fidelity_state_trace_bundle",
            "reviewer_exception_log",
        ],
    },
    {
        "id": "procurement-and-operations-boundary",
        "title": "Procurement and operations boundary",
        "source_inputs": [SOURCE_COST_ARCHITECTURE, SOURCE_GAPS],
        "review_questions": [
            "Are proxy costs separated from procurement estimates and vendor quotes?",
            "Which launch, regulatory, and operations records remain external?",
        ],
        "expected_failure_modes": [
            "procurement-grade cost estimate",
            "vendor quote obtained",
            "regulatory or operations approval complete",
        ],
        "external_deliverable_ids": ["third_party_reproduction_report", "external_red_team_report", "public_claim_wording_audit"],
    },
    {
        "id": "public-wording-overinterpretation",
        "title": "Public wording overinterpretation",
        "source_inputs": [SOURCE_ROADMAP_DOC, SOURCE_ARTIFACT_POLICY],
        "review_questions": [
            "Can a public reader mistake a generated artifact for certification?",
            "Are forbidden claims visibly blocked at the route and artifact level?",
        ],
        "expected_failure_modes": ["third-party validated", "certified", "flight-ready"],
        "external_deliverable_ids": ["external_red_team_report", "public_claim_wording_audit", "reviewer_exception_log"],
    },
]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_artifacts(repo_root: Path, paths: Sequence[str]) -> List[Dict[str, str]]:
    return [{"path": path, "sha256": _sha256_file(repo_root / path)} for path in paths]


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _review_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    for item in REVIEW_CASE_DEFS:
        cases.append(
            {
                **item,
                "status": "external_required",
                "independent_result_available": False,
                "acceptance_record_required": {
                    "reviewer_identity": True,
                    "review_date_utc": True,
                    "reviewed_commit_sha": True,
                    "commands_or_tools": True,
                    "raw_outputs_or_report_uri": True,
                    "exceptions_or_disagreements": True,
                },
                "blocked_claims": list(dict.fromkeys([*item["expected_failure_modes"], *BLOCKED_CLAIMS])),
            }
        )
    return cases


def _deliverables() -> List[Dict[str, Any]]:
    return [
        {
            "id": "third_party_reproduction_report",
            "status": "external_required",
            "acceptance_fields": ["reviewer_identity", "date", "commit_sha", "commands", "outputs", "exceptions"],
            "blocked_claim": "independent reproduction completed",
        },
        {
            "id": "independent_physics_benchmark_report",
            "status": "external_required",
            "acceptance_fields": ["backend_name", "scenario_ids", "state_trace_hashes", "comparison_summary"],
            "blocked_claim": "independent physics backend validated",
        },
        {
            "id": "high_fidelity_state_trace_bundle",
            "status": "external_required",
            "acceptance_fields": ["module_ids", "scenario_ids", "state_trace_hashes", "backend_versions"],
            "blocked_claim": "high-fidelity state trace complete",
        },
        {
            "id": "external_red_team_report",
            "status": "external_required",
            "acceptance_fields": ["reviewer_identity", "case_ids", "findings", "unresolved_exceptions"],
            "blocked_claim": "external validation completed",
        },
        {
            "id": "reviewer_exception_log",
            "status": "external_required",
            "acceptance_fields": ["case_id", "finding", "severity", "resolution_status"],
            "blocked_claim": "third-party validated",
        },
        {
            "id": "public_claim_wording_audit",
            "status": "external_required",
            "acceptance_fields": ["auditor_identity", "reviewed_surfaces", "blocked_claims_found", "approved_wording"],
            "blocked_claim": "external validation completed",
        },
    ]


def _roadmap_item() -> Dict[str, Any]:
    return {
        "id": "roadmap-14",
        "title": "External validation and independent review pack",
        "status": "repo_native_closure_implemented_external_evidence_open",
        "implementation_mode": "tracked_external_validation_review_pack",
        "summary": "Packages red-team cases, required reviewer deliverables, and external validation blockers without claiming review completion.",
        "external_evidence_gaps": [
            "third-party reproduction reports",
            "independent physics benchmark comparisons",
            "high-fidelity module state traces",
            "external red-team review findings",
        ],
        "claim_boundary": "Implemented as a deterministic repository artifact and review contract; external qualification remains separate.",
    }


def build_external_validation_review_pack(repo_root: Path) -> Dict[str, Any]:
    dag_boundary = _load_json(repo_root / SOURCE_DAG_BOUNDARY)
    evidence_upgrade = _load_json(repo_root / SOURCE_EVIDENCE_UPGRADE)
    runtime_generation = _load_json(repo_root / SOURCE_RUNTIME_GENERATION)
    cost_architecture = _load_json(repo_root / SOURCE_COST_ARCHITECTURE)

    source_paths = [
        SOURCE_DAG_BOUNDARY,
        SOURCE_EVIDENCE_UPGRADE,
        SOURCE_RUNTIME_GENERATION,
        SOURCE_COST_ARCHITECTURE,
        SOURCE_PROBABILITY_COUPLING,
        SOURCE_UNCERTAINTY_INTERACTIONS,
        SOURCE_CAPSULE_RISK,
        SOURCE_EVIDENCE_CLAIMS,
        SOURCE_EVIDENCE_ASSUMPTIONS,
        SOURCE_EVIDENCE_SOURCES,
        SOURCE_EVIDENCE_PACK_META,
        SOURCE_EVIDENCE_PACK_CHECKSUMS,
        SOURCE_GAPS,
        SOURCE_ROADMAP_DOC,
        SOURCE_ARTIFACT_POLICY,
        SOURCE_SPEC,
        SOURCE_IMPLEMENTATION,
        SOURCE_BUILDER,
        SOURCE_VALIDATOR,
    ]
    cases = _review_cases()
    deliverables = _deliverables()
    dag_rollup = dag_boundary.get("rollup", {}) if isinstance(dag_boundary.get("rollup"), Mapping) else {}
    evidence_rollup = evidence_upgrade.get("rollup", {}) if isinstance(evidence_upgrade.get("rollup"), Mapping) else {}
    runtime_rollup = runtime_generation.get("rollup", {}) if isinstance(runtime_generation.get("rollup"), Mapping) else {}
    cost_rollup = cost_architecture.get("rollup", {}) if isinstance(cost_architecture.get("rollup"), Mapping) else {}

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "public_scope": PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, source_paths),
        "review_pack_status": "repo_native_review_pack_ready_external_review_not_completed",
        "roadmap_item": _roadmap_item(),
        "required_external_deliverables": deliverables,
        "review_case_count": len(cases),
        "review_cases": cases,
        "dag_review_surface": {
            "module_count": dag_boundary.get("module_count"),
            "state_trace_contract_complete": dag_rollup.get("state_trace_contract_complete"),
            "independent_backend_complete": dag_rollup.get("independent_backend_complete"),
            "high_fidelity_state_traces_available": dag_rollup.get("high_fidelity_state_traces_available"),
            "cross_backend_comparison_available": dag_rollup.get("cross_backend_comparison_available"),
            "external_reproduction_completed": dag_rollup.get("external_reproduction_completed"),
        },
        "evidence_review_surface": {
            "claim_count": evidence_upgrade.get("claim_count"),
            "trust_grade_distribution": evidence_upgrade.get("trust_distribution", {}),
            "public_campaign_count": evidence_upgrade.get("public_campaign_count"),
            "source_chain_contract": "claim -> assumption -> model -> artifact -> source",
            "automatic_trust_upgrade_claimed": False,
            "source_correctness_claimed": False,
            "speculative_quarantine_count": evidence_rollup.get("speculative_quarantine_count"),
        },
        "runtime_review_surface": {
            "local_pack_validator": "scripts/ci/user_mission_run_pack_validate.py",
            "generation_row_count": runtime_generation.get("generation_row_count"),
            "remote_execution_claimed": runtime_rollup.get("remote_execution_claimed"),
            "persistent_reviewed_archive_claimed": runtime_rollup.get("persistent_reviewed_archive_claimed"),
        },
        "cost_procurement_review_surface": {
            "architecture_row_count": cost_architecture.get("architecture_row_count"),
            "procurement_grade_estimate_available": cost_rollup.get("procurement_grade_estimate_available"),
            "vendor_quote_count": cost_rollup.get("vendor_quote_count"),
            "launch_vehicle_selected": cost_rollup.get("launch_vehicle_selected"),
            "architecture_selected_for_flight": cost_rollup.get("architecture_selected_for_flight"),
        },
        "rollup": {
            "review_case_count": len(cases),
            "external_deliverable_count": len(deliverables),
            "third_party_review_completed": False,
            "independent_reproduction_completed": False,
            "independent_benchmark_completed": False,
            "high_fidelity_state_trace_complete": False,
            "external_red_team_completed": False,
            "external_validation_claimed": False,
            "all_cases_require_external_review": all(case["status"] == "external_required" for case in cases),
        },
        "blocked_claims": list(BLOCKED_CLAIMS),
        "external_evidence_gaps": [
            "third-party reproduction reports",
            "independent physics benchmark comparisons",
            "high-fidelity module state traces",
            "external red-team review findings",
            "public wording audit by a reviewer outside the repository",
        ],
        "interpretation_limits": [
            "The review pack is a checklist and evidence request, not a completed third-party review.",
            "Independent reproduction, benchmark comparison, high-fidelity traces, and external validation remain open.",
            "Browser UI may render this artifact but must not claim external review completion.",
        ],
    }
    payload["determinism_signature"] = hashlib.sha256(
        canonical_json(
            {
                "schema_version": payload["schema_version"],
                "source_artifacts": payload["source_artifacts"],
                "review_cases": [
                    {
                        "id": case["id"],
                        "status": case["status"],
                        "external_deliverable_ids": case["external_deliverable_ids"],
                    }
                    for case in cases
                ],
                "rollup": payload["rollup"],
            }
        ).encode("utf-8")
    ).hexdigest()
    return payload


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _source_hash_by_path(payload: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in payload.get("source_artifacts", []):
        if isinstance(item, Mapping) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str):
            out[str(item["path"])] = str(item["sha256"])
    return out


def _validate_sources(*, repo_root: Path, payload: Mapping[str, Any], errors: List[str]) -> None:
    expected = {
        SOURCE_DAG_BOUNDARY,
        SOURCE_EVIDENCE_UPGRADE,
        SOURCE_RUNTIME_GENERATION,
        SOURCE_COST_ARCHITECTURE,
        SOURCE_PROBABILITY_COUPLING,
        SOURCE_UNCERTAINTY_INTERACTIONS,
        SOURCE_CAPSULE_RISK,
        SOURCE_EVIDENCE_CLAIMS,
        SOURCE_EVIDENCE_ASSUMPTIONS,
        SOURCE_EVIDENCE_SOURCES,
        SOURCE_EVIDENCE_PACK_META,
        SOURCE_EVIDENCE_PACK_CHECKSUMS,
        SOURCE_GAPS,
        SOURCE_ROADMAP_DOC,
        SOURCE_ARTIFACT_POLICY,
        SOURCE_SPEC,
        SOURCE_IMPLEMENTATION,
        SOURCE_BUILDER,
        SOURCE_VALIDATOR,
    }
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


def validate_external_validation_review_pack(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if payload.get("generator") != GENERATOR:
        errors.append(f"generator must be {GENERATOR}")
    if payload.get("public_scope") != PUBLIC_SCOPE:
        errors.append(f"public_scope must be {PUBLIC_SCOPE}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, errors=errors)
    if payload.get("review_pack_status") != "repo_native_review_pack_ready_external_review_not_completed":
        errors.append("review_pack_status must keep external_review_not_completed")

    deliverables = payload.get("required_external_deliverables")
    if not isinstance(deliverables, list) or len(deliverables) != len(DELIVERABLE_IDS):
        errors.append("required_external_deliverables must include all deliverables")
        deliverables = []
    deliverable_ids = [item.get("id") for item in deliverables if isinstance(item, Mapping)]
    if deliverable_ids != DELIVERABLE_IDS:
        errors.append("required_external_deliverables ids/order mismatch")
    for index, item in enumerate(deliverables):
        if not isinstance(item, Mapping):
            errors.append(f"required_external_deliverables[{index}] must be object")
            continue
        if item.get("status") != "external_required":
            errors.append(f"required_external_deliverables[{index}].status must be external_required")
        if not isinstance(item.get("acceptance_fields"), list) or not item["acceptance_fields"]:
            errors.append(f"required_external_deliverables[{index}].acceptance_fields must be non-empty")

    cases = payload.get("review_cases")
    if not isinstance(cases, list) or len(cases) < 6:
        errors.append("review_cases must contain at least 6 cases")
        cases = []
    if payload.get("review_case_count") != len(cases):
        errors.append("review_case_count must equal len(review_cases)")
    case_ids: List[str] = []
    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            errors.append(f"review_cases[{index}] must be object")
            continue
        prefix = f"review_cases[{index}]"
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{prefix}.id must be non-empty")
        else:
            case_ids.append(case_id)
        if case.get("status") != "external_required":
            errors.append(f"{prefix}.status must be external_required")
        if case.get("independent_result_available") is not False:
            errors.append(f"{prefix}.independent_result_available must be false")
        for field in ("source_inputs", "review_questions", "expected_failure_modes", "external_deliverable_ids", "blocked_claims"):
            if not isinstance(case.get(field), list) or not case[field]:
                errors.append(f"{prefix}.{field} must be non-empty list")
        for deliverable_id in case.get("external_deliverable_ids", []):
            if deliverable_id not in DELIVERABLE_IDS:
                errors.append(f"{prefix}.external_deliverable_ids contains unknown deliverable {deliverable_id}")
        if not isinstance(case.get("acceptance_record_required"), Mapping):
            errors.append(f"{prefix}.acceptance_record_required must be object")
        blocked = case.get("blocked_claims")
        if isinstance(blocked, list) and "external validation completed" not in blocked:
            errors.append(f"{prefix}.blocked_claims must block external validation completion")
    if len(case_ids) != len(set(case_ids)):
        errors.append("review case ids must be unique")

    dag = payload.get("dag_review_surface")
    if not isinstance(dag, Mapping):
        errors.append("dag_review_surface must be object")
        dag = {}
    if dag.get("module_count") != 6:
        errors.append("dag_review_surface.module_count must be 6")
    if dag.get("state_trace_contract_complete") is not True:
        errors.append("dag_review_surface.state_trace_contract_complete must be true")
    for field in (
        "independent_backend_complete",
        "high_fidelity_state_traces_available",
        "cross_backend_comparison_available",
        "external_reproduction_completed",
    ):
        if dag.get(field) is not False:
            errors.append(f"dag_review_surface.{field} must be false")

    evidence = payload.get("evidence_review_surface")
    if not isinstance(evidence, Mapping):
        errors.append("evidence_review_surface must be object")
        evidence = {}
    if evidence.get("claim_count") != 66:
        errors.append("evidence_review_surface.claim_count must be 66")
    if evidence.get("trust_grade_distribution") != {"B": 8, "C": 56, "D": 2}:
        errors.append("evidence_review_surface.trust_grade_distribution mismatch")
    for field in ("automatic_trust_upgrade_claimed", "source_correctness_claimed"):
        if evidence.get(field) is not False:
            errors.append(f"evidence_review_surface.{field} must be false")

    runtime = payload.get("runtime_review_surface")
    if not isinstance(runtime, Mapping):
        errors.append("runtime_review_surface must be object")
        runtime = {}
    if runtime.get("generation_row_count") != 15:
        errors.append("runtime_review_surface.generation_row_count must be 15")
    for field in ("remote_execution_claimed", "persistent_reviewed_archive_claimed"):
        if runtime.get(field) is not False:
            errors.append(f"runtime_review_surface.{field} must be false")

    cost = payload.get("cost_procurement_review_surface")
    if not isinstance(cost, Mapping):
        errors.append("cost_procurement_review_surface must be object")
        cost = {}
    if cost.get("architecture_row_count") != 15:
        errors.append("cost_procurement_review_surface.architecture_row_count must be 15")
    for field in ("procurement_grade_estimate_available", "launch_vehicle_selected", "architecture_selected_for_flight"):
        if cost.get(field) is not False:
            errors.append(f"cost_procurement_review_surface.{field} must be false")
    if cost.get("vendor_quote_count") != 0:
        errors.append("cost_procurement_review_surface.vendor_quote_count must be 0")

    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("review_case_count") != len(cases):
        errors.append("rollup.review_case_count mismatch")
    if rollup.get("external_deliverable_count") != len(DELIVERABLE_IDS):
        errors.append("rollup.external_deliverable_count mismatch")
    for field in (
        "third_party_review_completed",
        "independent_reproduction_completed",
        "independent_benchmark_completed",
        "high_fidelity_state_trace_complete",
        "external_red_team_completed",
        "external_validation_claimed",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    if rollup.get("all_cases_require_external_review") is not True:
        errors.append("rollup.all_cases_require_external_review must be true")

    blocked_claims = payload.get("blocked_claims")
    if not isinstance(blocked_claims, list):
        errors.append("blocked_claims must be list")
    else:
        for claim in BLOCKED_CLAIMS:
            if claim not in blocked_claims:
                errors.append(f"blocked_claims missing {claim}")
    if not isinstance(payload.get("interpretation_limits"), list) or not payload["interpretation_limits"]:
        errors.append("interpretation_limits must be non-empty")
    if not isinstance(payload.get("external_evidence_gaps"), list) or not payload["external_evidence_gaps"]:
        errors.append("external_evidence_gaps must be non-empty")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors
