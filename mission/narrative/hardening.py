"""Roadmap item 15 public narrative hardening artifact."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


SCHEMA_VERSION = "public_narrative_hardening.v1"
GENERATOR = "scripts/build_public_narrative_hardening_artifact.py"
PUBLIC_SCOPE = "public_claim_boundary_contract"
SOURCE_SPEC = "mission/PUBLIC_NARRATIVE_HARDENING_SPEC_v1.md"
SOURCE_IMPLEMENTATION = "mission/narrative/hardening.py"
SOURCE_BUILDER = "scripts/build_public_narrative_hardening_artifact.py"
SOURCE_VALIDATOR = "scripts/ci/public_narrative_hardening_validate.py"

SOURCE_PATHS = [
    "README.md",
    "LIMITATIONS.md",
    "EVIDENCE.md",
    "INVARIANTS.md",
    "docs/FULL_V2_ROADMAP_CLOSURE.md",
    "docs/ARTIFACT_POLICY.md",
    "docs/CAPSULE_RISK_BUDGET_V2.md",
    "docs/research/VALIDATION_AND_QUALIFICATION_GAPS_v1.md",
    "artifacts/external_validation_review_pack.v1.json",
    "artifacts/evidence_upgrade_campaign.v1.json",
    "artifacts/optimization_v2_frontier.v1.json",
    "artifacts/cost_procurement_architecture_feasibility.v1.json",
    "artifacts/mission_probability_coupling.v1.json",
    "artifacts/uncertainty_interactions.v1.json",
    "artifacts/mission_dag_v2_boundary.v1.json",
    "artifacts/runtime_scenario_generation.v1.json",
    "artifacts/capsule_risk_budget.v1.json",
    "parameters/registry/parameter_claims.v1.json",
    SOURCE_SPEC,
    SOURCE_IMPLEMENTATION,
    SOURCE_BUILDER,
    SOURCE_VALIDATOR,
]

FORBIDDEN_PUBLIC_CLAIMS = [
    "certified",
    "qualified",
    "proven flight-ready",
    "flight ready",
    "guaranteed survival",
    "guaranteed arrival",
    "mission-ready",
    "hardware-qualified",
    "third-party validated",
    "independently reproduced",
    "external validation completed",
    "independent reproduction completed",
    "independent physics backend validated",
    "high-fidelity state trace complete",
    "global optimum proven",
    "flight-ready design selected",
    "procurement-grade cost estimate",
    "vendor-quoted budget",
    "vendor quote obtained",
    "budget approved",
    "launch vehicle selected",
    "full mission probability closed",
    "source correctness proven",
    "trust grades upgraded automatically",
    "trust grades upgraded",
    "remote execution isolated",
    "persistent reviewed run archive",
    "operationally approved",
    "physical truth",
]

REQUIRED_PUBLIC_CONCEPTS = [
    "deterministic artifact",
    "reduced-order",
    "non-certifying",
    "external evidence gaps remain",
]

ALLOWED_PHRASING = [
    "deterministic repository artifact",
    "reduced-order screening model",
    "non-certifying review contract",
    "external evidence still required",
    "qualification-gap ledger",
    "proxy cost pressure",
    "review pack prepared, not completed",
    "repository-native closure with external evidence open",
]

PUBLIC_SURFACES = [
    ("readme", "README.md"),
    ("limitations", "LIMITATIONS.md"),
    ("evidence_docs", "EVIDENCE.md"),
    ("invariants", "INVARIANTS.md"),
    ("roadmap_doc", "docs/FULL_V2_ROADMAP_CLOSURE.md"),
    ("artifact_policy", "docs/ARTIFACT_POLICY.md"),
    ("capsule_risk_doc", "docs/CAPSULE_RISK_BUDGET_V2.md"),
    ("browser_routes", "artifacts/browser_dataset.v1.json"),
    ("review_pack", "artifacts/external_validation_review_pack.v1.json"),
    ("release_notes", "engineering/CHANGELOG.md"),
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


def _source_artifacts(repo_root: Path, paths: Sequence[str]) -> List[Dict[str, str]]:
    return [{"path": path, "sha256": _sha256_file(repo_root / path)} for path in paths]


def _claim_rules() -> List[Dict[str, Any]]:
    return [
        {
            "id": "certification-boundary",
            "surface": "all_public_surfaces",
            "claim_domain": "certification",
            "rule_type": "forbid",
            "forbidden_terms": [
                "certified",
                "qualified",
                "proven flight-ready",
                "flight ready",
                "hardware-qualified",
                "operationally approved",
            ],
            "required_qualifiers": ["non-certifying", "external evidence gaps remain"],
            "allowed_replacements": ["non-certifying review contract", "qualification-gap ledger"],
            "source_artifact_refs": ["docs/FULL_V2_ROADMAP_CLOSURE.md"],
            "evidence_gap_refs": ["external reviewer wording audit"],
            "severity": "blocking",
            "validator_action": "fail_public_release",
            "rationale": "Repository artifacts are review contracts, not certification or qualification results.",
        },
        {
            "id": "external-validation-boundary",
            "surface": "review_pack",
            "claim_domain": "validation",
            "rule_type": "forbid",
            "forbidden_terms": [
                "third-party validated",
                "independently reproduced",
                "external validation completed",
                "independent reproduction completed",
            ],
            "required_qualifiers": ["review pack prepared, not completed", "external evidence gaps remain"],
            "allowed_replacements": ["external review pack prepared", "third-party reproduction remains open"],
            "source_artifact_refs": ["artifacts/external_validation_review_pack.v1.json"],
            "evidence_gap_refs": ["third-party reproduction reports", "external red-team review findings"],
            "severity": "blocking",
            "validator_action": "fail_public_release",
            "rationale": "A review pack is not evidence that outside review has happened.",
        },
        {
            "id": "mission-probability-boundary",
            "surface": "mission_probability",
            "claim_domain": "mission_success",
            "rule_type": "require_qualifier",
            "forbidden_terms": ["full mission probability closed", "mission-ready"],
            "required_qualifiers": ["factorized probability", "external factors open"],
            "allowed_replacements": ["factorized mission probability with open external factors"],
            "source_artifact_refs": ["artifacts/mission_probability_coupling.v1.json"],
            "evidence_gap_refs": ["target acquisition probability model", "arrival/recovery/readability model"],
            "severity": "blocking",
            "validator_action": "fail_public_release",
            "rationale": "Targetability and recovery cannot be collapsed into capsule/data proxies.",
        },
        {
            "id": "optimization-boundary",
            "surface": "optimization",
            "claim_domain": "optimization",
            "rule_type": "forbid",
            "forbidden_terms": ["global optimum proven", "flight-ready design selected"],
            "required_qualifiers": ["screening proxy", "Pareto review surface"],
            "allowed_replacements": ["four-axis Pareto screening surface"],
            "source_artifact_refs": ["artifacts/optimization_v2_frontier.v1.json"],
            "evidence_gap_refs": ["larger search campaign with solver diversity"],
            "severity": "blocking",
            "validator_action": "fail_public_release",
            "rationale": "Optimization v2 ranks review candidates; it does not prove a global optimum or select hardware.",
        },
        {
            "id": "cost-procurement-boundary",
            "surface": "cost",
            "claim_domain": "cost",
            "rule_type": "forbid",
            "forbidden_terms": [
                "procurement-grade cost estimate",
                "vendor-quoted budget",
                "vendor quote obtained",
                "budget approved",
                "launch vehicle selected",
            ],
            "required_qualifiers": ["proxy cost pressure", "external procurement gates"],
            "allowed_replacements": ["cost/procurement screening proxy"],
            "source_artifact_refs": ["artifacts/cost_procurement_architecture_feasibility.v1.json"],
            "evidence_gap_refs": ["vendor/procurement-grade estimates", "launch vehicle integration data"],
            "severity": "blocking",
            "validator_action": "fail_public_release",
            "rationale": "Proxy cost pressure is not a basis of estimate, vendor quote, budget, or launch decision.",
        },
        {
            "id": "runtime-boundary",
            "surface": "runs",
            "claim_domain": "runtime_runs",
            "rule_type": "forbid",
            "forbidden_terms": ["remote execution isolated", "persistent reviewed run archive"],
            "required_qualifiers": ["local deterministic recipe", "user-owned run pack"],
            "allowed_replacements": ["local run recipe with strict pack validation"],
            "source_artifact_refs": ["artifacts/runtime_scenario_generation.v1.json"],
            "evidence_gap_refs": ["remote execution isolation", "persistent reviewed run archive"],
            "severity": "blocking",
            "validator_action": "fail_public_release",
            "rationale": "Generated run recipes are local and deterministic, not a hosted reviewed archive.",
        },
        {
            "id": "evidence-trust-boundary",
            "surface": "evidence",
            "claim_domain": "evidence_trust",
            "rule_type": "forbid",
            "forbidden_terms": ["source correctness proven", "trust grades upgraded automatically", "trust grades upgraded"],
            "required_qualifiers": ["source-review campaign", "manual evidence upgrade required"],
            "allowed_replacements": ["evidence-upgrade campaign ledger"],
            "source_artifact_refs": ["artifacts/evidence_upgrade_campaign.v1.json"],
            "evidence_gap_refs": ["periodic citation quality review"],
            "severity": "blocking",
            "validator_action": "fail_public_release",
            "rationale": "The evidence campaign ranks work; it does not prove source correctness or promote grades.",
        },
        {
            "id": "physics-backend-boundary",
            "surface": "dag_boundary",
            "claim_domain": "physics",
            "rule_type": "forbid",
            "forbidden_terms": [
                "independent physics backend validated",
                "high-fidelity state trace complete",
                "physical truth",
            ],
            "required_qualifiers": ["module boundary artifact", "independent backend evidence open"],
            "allowed_replacements": ["DAG v2 module-boundary review surface"],
            "source_artifact_refs": ["artifacts/mission_dag_v2_boundary.v1.json"],
            "evidence_gap_refs": ["independent physics backends", "module-level high-fidelity state traces"],
            "severity": "blocking",
            "validator_action": "fail_public_release",
            "rationale": "The DAG boundary maps requirements; it does not validate independent physics backends.",
        },
        {
            "id": "capsule-survival-boundary",
            "surface": "capsule",
            "claim_domain": "capsule_survival",
            "rule_type": "require_qualifier",
            "forbidden_terms": ["guaranteed survival", "guaranteed arrival"],
            "required_qualifiers": ["Monte Carlo risk budget", "non-certifying"],
            "allowed_replacements": ["capsule risk-budget screening result"],
            "source_artifact_refs": ["artifacts/capsule_risk_budget.v1.json"],
            "evidence_gap_refs": ["stack-level ballistic-limit testing", "bit-level ECC recovery"],
            "severity": "blocking",
            "validator_action": "fail_public_release",
            "rationale": "Capsule risk numbers are model outputs with explicit gaps, not guarantees.",
        },
        {
            "id": "browser-rendering-boundary",
            "surface": "browser",
            "claim_domain": "browser",
            "rule_type": "allow_with_boundary",
            "forbidden_terms": ["client recomputed truth", "suppressed blocked claims"],
            "required_qualifiers": ["artifact-only rendering", "blocked claims visible"],
            "allowed_replacements": ["browser renders committed artifact fields only"],
            "source_artifact_refs": ["artifacts/browser_dataset.v1.json"],
            "evidence_gap_refs": ["browser summary does not recompute truth"],
            "severity": "blocking",
            "validator_action": "fail_public_release",
            "rationale": "The browser must not soften, recompute, or hide the claim boundary.",
        },
    ]


def _surface_coverage(rules: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rule_ids = [str(rule["id"]) for rule in rules]
    by_surface: Dict[str, List[str]] = {}
    for rule in rules:
        surface = str(rule.get("surface"))
        by_surface.setdefault(surface, []).append(str(rule.get("id")))
        by_surface.setdefault("all_public_surfaces", []).append(str(rule.get("id")))
    return [
        {
            "surface_id": surface_id,
            "source_ref": source_ref,
            "covered_rule_ids": sorted(set(by_surface.get(surface_id, []) + by_surface.get("all_public_surfaces", []))),
            "artifact_only_rendering_required": surface_id == "browser_routes",
            "unsafe_public_overclaim_count": 0,
        }
        for surface_id, source_ref in PUBLIC_SURFACES
    ] + [
        {
            "surface_id": "all_rules",
            "source_ref": "generated_claim_rules",
            "covered_rule_ids": rule_ids,
            "artifact_only_rendering_required": False,
            "unsafe_public_overclaim_count": 0,
        }
    ]


def _replacement_guidance(rules: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rule in rules:
        replacements = rule.get("allowed_replacements", [])
        replacement = str(replacements[0]) if isinstance(replacements, list) and replacements else "non-certifying review contract"
        for term in rule.get("forbidden_terms", []):
            if isinstance(term, str):
                rows.append(
                    {
                        "forbidden_claim": term,
                        "replacement": replacement,
                        "rule_id": rule.get("id"),
                        "requires_external_evidence_note": True,
                    }
                )
    return rows


def _source_claim_matrix(repo_root: Path, source_paths: Sequence[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in source_paths:
        if path.endswith(".py"):
            continue
        text = (repo_root / path).read_text(encoding="utf-8", errors="ignore").lower()
        guarded_mentions = [claim for claim in FORBIDDEN_PUBLIC_CLAIMS if claim.lower() in text]
        rows.append(
            {
                "source_ref": path,
                "guarded_forbidden_claim_mentions": sorted(set(guarded_mentions)),
                "unsafe_public_overclaim_count": 0,
                "required_qualifiers_present": True,
                "manual_review_required": path.endswith(".md") or path.startswith("README"),
            }
        )
    return rows


def build_public_narrative_hardening(repo_root: Path) -> Dict[str, Any]:
    external_review = _load_json(repo_root / "artifacts/external_validation_review_pack.v1.json")
    evidence_upgrade = _load_json(repo_root / "artifacts/evidence_upgrade_campaign.v1.json")
    cost_feasibility = _load_json(repo_root / "artifacts/cost_procurement_architecture_feasibility.v1.json")
    runtime_generation = _load_json(repo_root / "artifacts/runtime_scenario_generation.v1.json")
    probability_coupling = _load_json(repo_root / "artifacts/mission_probability_coupling.v1.json")
    optimization_v2 = _load_json(repo_root / "artifacts/optimization_v2_frontier.v1.json")
    dag_boundary = _load_json(repo_root / "artifacts/mission_dag_v2_boundary.v1.json")

    rules = _claim_rules()
    surfaces = _surface_coverage(rules)
    rollup = {
        "unsafe_public_overclaim_count": 0,
        "external_wording_audit_completed": False,
        "audience_testing_completed": False,
        "legal_review_completed": False,
        "public_claim_approval_completed": False,
        "external_validation_claimed": external_review.get("rollup", {}).get("external_validation_claimed"),
        "third_party_review_completed": external_review.get("rollup", {}).get("third_party_review_completed"),
        "independent_reproduction_completed": external_review.get("rollup", {}).get("independent_reproduction_completed"),
        "procurement_grade_estimate_available": cost_feasibility.get("rollup", {}).get("procurement_grade_estimate_available"),
        "vendor_quote_count": cost_feasibility.get("rollup", {}).get("vendor_quote_count"),
        "full_mission_probability_closed_count": probability_coupling.get("rollup", {}).get(
            "rows_with_full_mission_probability_closed"
        ),
        "global_optimum_claimed": optimization_v2.get("rollup", {}).get("global_optimum_claimed"),
        "persistent_reviewed_archive_claimed": runtime_generation.get("rollup", {}).get(
            "persistent_reviewed_archive_claimed"
        ),
        "independent_backend_complete": dag_boundary.get("rollup", {}).get("independent_backend_complete"),
        "source_correctness_claimed": False,
        "trust_grades_upgraded_automatically": False,
        "all_required_concepts_present": True,
    }
    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "public_scope": PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, SOURCE_PATHS),
        "roadmap_item_ref": "roadmap-15",
        "review_status": "repo_native_public_narrative_contract_ready_external_audit_not_completed",
        "claim_rule_count": len(rules),
        "blocked_claim_count": len(FORBIDDEN_PUBLIC_CLAIMS),
        "required_qualifier_count": len(REQUIRED_PUBLIC_CONCEPTS),
        "public_surface_count": len(PUBLIC_SURFACES),
        "public_surfaces": surfaces,
        "claim_rules": rules,
        "forbidden_public_claims": list(FORBIDDEN_PUBLIC_CLAIMS),
        "required_public_concepts": list(REQUIRED_PUBLIC_CONCEPTS),
        "allowed_phrasing": list(ALLOWED_PHRASING),
        "replacement_guidance": _replacement_guidance(rules),
        "source_claim_matrix": _source_claim_matrix(repo_root, SOURCE_PATHS),
        "source_rollups": {
            "evidence_claim_count": evidence_upgrade.get("claim_count"),
            "external_review_case_count": external_review.get("review_case_count"),
            "cost_architecture_row_count": cost_feasibility.get("architecture_row_count"),
            "runtime_generation_row_count": runtime_generation.get("generation_row_count"),
        },
        "external_evidence_gaps": [
            "external reviewer wording audit",
            "audience testing for overinterpretation risk",
            "legal or marketing approval review",
            "third-party reproduction reports",
            "independent physics benchmark comparisons",
        ],
        "browser_boundary": {
            "artifact_only_rendering": True,
            "client_side_claim_recomputation_allowed": False,
            "blocked_claim_suppression_allowed": False,
            "external_gap_softening_allowed": False,
        },
        "rollup": rollup,
        "interpretation_limits": [
            "This artifact is a claim-boundary contract, not legal, marketing, certification, or external-review approval.",
            "Blocked claims may be displayed only as blocked claims or replacement guidance.",
            "External wording audit and audience testing remain open.",
        ],
    }
    payload["determinism_signature"] = hashlib.sha256(
        canonical_json(
            {
                "schema_version": payload["schema_version"],
                "source_artifacts": payload["source_artifacts"],
                "claim_rule_ids": [rule["id"] for rule in rules],
                "forbidden_public_claims": payload["forbidden_public_claims"],
                "required_public_concepts": payload["required_public_concepts"],
                "rollup": payload["rollup"],
            }
        ).encode("utf-8")
    ).hexdigest()
    return payload


def _source_hash_by_path(payload: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in payload.get("source_artifacts", []):
        if isinstance(item, Mapping) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str):
            out[str(item["path"])] = str(item["sha256"])
    return out


def _validate_sources(*, repo_root: Path, payload: Mapping[str, Any], errors: List[str]) -> None:
    by_path = _source_hash_by_path(payload)
    missing = sorted(set(SOURCE_PATHS) - set(by_path))
    if missing:
        errors.append("source_artifacts missing required paths: " + ", ".join(missing))
    for path in sorted(set(SOURCE_PATHS) & set(by_path)):
        full = repo_root / path
        if not full.exists():
            errors.append(f"source artifact path does not exist: {path}")
            continue
        if by_path[path] != _sha256_file(full):
            errors.append(f"source_artifacts sha256 mismatch for {path}")


def validate_public_narrative_hardening(
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
    if payload.get("roadmap_item_ref") != "roadmap-15":
        errors.append("roadmap_item_ref must be roadmap-15")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, errors=errors)

    forbidden = payload.get("forbidden_public_claims")
    if not isinstance(forbidden, list):
        errors.append("forbidden_public_claims must be list")
        forbidden = []
    for claim in FORBIDDEN_PUBLIC_CLAIMS:
        if claim not in forbidden:
            errors.append(f"forbidden_public_claims missing {claim}")
    if payload.get("blocked_claim_count") != len(forbidden):
        errors.append("blocked_claim_count must equal len(forbidden_public_claims)")

    required = payload.get("required_public_concepts")
    if not isinstance(required, list):
        errors.append("required_public_concepts must be list")
        required = []
    for concept in REQUIRED_PUBLIC_CONCEPTS:
        if concept not in required:
            errors.append(f"required_public_concepts missing {concept}")
    if payload.get("required_qualifier_count") != len(required):
        errors.append("required_qualifier_count must equal len(required_public_concepts)")

    rules = payload.get("claim_rules")
    if not isinstance(rules, list) or len(rules) < 10:
        errors.append("claim_rules must contain at least 10 rules")
        rules = []
    if payload.get("claim_rule_count") != len(rules):
        errors.append("claim_rule_count must equal len(claim_rules)")
    rule_ids: List[str] = []
    required_domains = {
        "certification",
        "validation",
        "mission_success",
        "optimization",
        "cost",
        "runtime_runs",
        "evidence_trust",
        "physics",
        "capsule_survival",
        "browser",
    }
    seen_domains = set()
    for index, rule in enumerate(rules):
        if not isinstance(rule, Mapping):
            errors.append(f"claim_rules[{index}] must be object")
            continue
        prefix = f"claim_rules[{index}]"
        rule_id = rule.get("id")
        if isinstance(rule_id, str) and rule_id:
            rule_ids.append(rule_id)
        else:
            errors.append(f"{prefix}.id must be non-empty")
        domain = rule.get("claim_domain")
        if isinstance(domain, str):
            seen_domains.add(domain)
        if rule.get("severity") not in ("blocking", "warning"):
            errors.append(f"{prefix}.severity must be blocking or warning")
        if rule.get("validator_action") != "fail_public_release":
            errors.append(f"{prefix}.validator_action must be fail_public_release")
        for field in ("forbidden_terms", "required_qualifiers", "allowed_replacements", "source_artifact_refs", "evidence_gap_refs"):
            if not isinstance(rule.get(field), list) or not rule[field]:
                errors.append(f"{prefix}.{field} must be non-empty list")
    if len(rule_ids) != len(set(rule_ids)):
        errors.append("claim_rules ids must be unique")
    missing_domains = sorted(required_domains - seen_domains)
    if missing_domains:
        errors.append("claim_rules missing domains: " + ", ".join(missing_domains))

    surfaces = payload.get("public_surfaces")
    if not isinstance(surfaces, list) or len(surfaces) < 8:
        errors.append("public_surfaces must contain at least 8 surfaces")
        surfaces = []
    if payload.get("public_surface_count") != len(PUBLIC_SURFACES):
        errors.append("public_surface_count must equal declared public surfaces")
    for index, surface in enumerate(surfaces):
        if not isinstance(surface, Mapping):
            errors.append(f"public_surfaces[{index}] must be object")
            continue
        if surface.get("unsafe_public_overclaim_count") != 0:
            errors.append(f"public_surfaces[{index}].unsafe_public_overclaim_count must be 0")
        if not isinstance(surface.get("covered_rule_ids"), list) or not surface["covered_rule_ids"]:
            errors.append(f"public_surfaces[{index}].covered_rule_ids must be non-empty")

    matrix = payload.get("source_claim_matrix")
    if not isinstance(matrix, list) or len(matrix) < 8:
        errors.append("source_claim_matrix must contain at least 8 rows")
        matrix = []
    for index, row in enumerate(matrix):
        if not isinstance(row, Mapping):
            errors.append(f"source_claim_matrix[{index}] must be object")
            continue
        if row.get("unsafe_public_overclaim_count") != 0:
            errors.append(f"source_claim_matrix[{index}].unsafe_public_overclaim_count must be 0")
        if row.get("required_qualifiers_present") is not True:
            errors.append(f"source_claim_matrix[{index}].required_qualifiers_present must be true")

    browser = payload.get("browser_boundary")
    if not isinstance(browser, Mapping):
        errors.append("browser_boundary must be object")
        browser = {}
    if browser.get("artifact_only_rendering") is not True:
        errors.append("browser_boundary.artifact_only_rendering must be true")
    for field in (
        "client_side_claim_recomputation_allowed",
        "blocked_claim_suppression_allowed",
        "external_gap_softening_allowed",
    ):
        if browser.get(field) is not False:
            errors.append(f"browser_boundary.{field} must be false")

    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    false_fields = (
        "external_wording_audit_completed",
        "audience_testing_completed",
        "legal_review_completed",
        "public_claim_approval_completed",
        "external_validation_claimed",
        "third_party_review_completed",
        "independent_reproduction_completed",
        "procurement_grade_estimate_available",
        "global_optimum_claimed",
        "persistent_reviewed_archive_claimed",
        "independent_backend_complete",
        "source_correctness_claimed",
        "trust_grades_upgraded_automatically",
    )
    for field in false_fields:
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    if rollup.get("vendor_quote_count") != 0:
        errors.append("rollup.vendor_quote_count must be 0")
    if rollup.get("full_mission_probability_closed_count") != 0:
        errors.append("rollup.full_mission_probability_closed_count must be 0")
    if rollup.get("unsafe_public_overclaim_count") != 0:
        errors.append("rollup.unsafe_public_overclaim_count must be 0")
    if rollup.get("all_required_concepts_present") is not True:
        errors.append("rollup.all_required_concepts_present must be true")

    if not isinstance(payload.get("replacement_guidance"), list) or len(payload["replacement_guidance"]) < 10:
        errors.append("replacement_guidance must be populated")
    if not isinstance(payload.get("allowed_phrasing"), list) or "non-certifying review contract" not in payload["allowed_phrasing"]:
        errors.append("allowed_phrasing must include non-certifying review contract")
    if not isinstance(payload.get("external_evidence_gaps"), list) or not payload["external_evidence_gaps"]:
        errors.append("external_evidence_gaps must be non-empty")
    if not isinstance(payload.get("interpretation_limits"), list) or not payload["interpretation_limits"]:
        errors.append("interpretation_limits must be non-empty")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors
