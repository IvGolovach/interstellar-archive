"""Deterministic evidence-upgrade campaign artifact.

The campaign ranks existing parameter claims by trust grade, source class,
public exposure, and sensitivity impact. It does not upgrade trust by itself;
it makes the work required to upgrade evidence reviewable and enforceable.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


SCHEMA_VERSION = "evidence_upgrade_campaign.v1"
GENERATOR = "scripts/build_evidence_upgrade_campaign_artifact.py"
PUBLIC_SCOPE = "parameter_evidence_upgrade_campaign"
SOURCE_PARAMETER_CLAIMS = "parameters/registry/parameter_claims.v1.json"
SOURCE_PARAMETER_REGISTRY = "parameters/registry/parameter_registry.v1.json"
SOURCE_EVIDENCE_SOURCES = "parameters/registry/evidence_sources.v1.json"
SOURCE_EVIDENCE_INDEX = "artifacts/parameter_evidence_index.json"
SOURCE_SENSITIVITY = "artifacts/parameter_sensitivity_summary.json"
SOURCE_P_SUCCESS = "artifacts/p_success_defensibility.json"

TRUST_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
TRUST_PENALTY = {"A": 0.0, "B": 1.0, "C": 3.0, "D": 5.0}
SOURCE_PENALTY = {"paper": 0.3, "report": 0.6, "dataset": 0.7, "assumption": 2.0}
SENSITIVITY_RE = re.compile(r"influence=([0-9.eE+-]+), delta_p_success=([0-9.eE+-]+)")
PUBLIC_VISIBILITY = "public"
INTERNAL_VISIBILITY = "internal"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _round(value: float, digits: int = 12) -> float:
    rounded = float(f"{float(value):.{digits}f}")
    return 0.0 if rounded == 0.0 else rounded


def _source_artifacts(repo_root: Path) -> List[Dict[str, str]]:
    paths = [
        SOURCE_PARAMETER_CLAIMS,
        SOURCE_PARAMETER_REGISTRY,
        SOURCE_EVIDENCE_SOURCES,
        SOURCE_EVIDENCE_INDEX,
        SOURCE_SENSITIVITY,
        SOURCE_P_SUCCESS,
    ]
    return [{"path": path, "sha256": _sha256_file(repo_root / path)} for path in paths]


def _source_lookup(sources: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {
        str(item["source_id"]): item
        for item in sources.get("sources", [])
        if isinstance(item, Mapping) and isinstance(item.get("source_id"), str)
    }


def _registry_lookup(registry: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {
        str(item["parameter_id"]): item
        for item in registry.get("parameters", [])
        if isinstance(item, Mapping) and isinstance(item.get("parameter_id"), str)
    }


def _public_surfaces(entry: Mapping[str, Any]) -> List[str]:
    surfaces = entry.get("public_surfaces")
    if not isinstance(surfaces, list):
        return []
    return sorted(str(item) for item in surfaces if isinstance(item, str))


def _visibility(entry: Mapping[str, Any]) -> str:
    raw = entry.get("visibility")
    if raw == PUBLIC_VISIBILITY:
        return PUBLIC_VISIBILITY
    return INTERNAL_VISIBILITY


def _sensitivity_for(parameter_id: str, sensitivity: Mapping[str, Any]) -> Dict[str, float | None]:
    summaries = sensitivity.get("summaries", {})
    raw = summaries.get(parameter_id) if isinstance(summaries, Mapping) else None
    if not isinstance(raw, str):
        return {"influence_score": None, "delta_p_success": None}
    match = SENSITIVITY_RE.search(raw)
    if not match:
        return {"influence_score": None, "delta_p_success": None}
    return {
        "influence_score": _round(float(match.group(1))),
        "delta_p_success": _round(float(match.group(2))),
    }


def _source_types(source_ids: Sequence[str], source_by_id: Mapping[str, Mapping[str, Any]]) -> List[str]:
    out = []
    for source_id in source_ids:
        source = source_by_id.get(source_id)
        if isinstance(source, Mapping):
            out.append(str(source.get("type", "unknown")))
        else:
            out.append("missing")
    return sorted(set(out))


def _source_quality_gaps(
    source_ids: Sequence[str],
    source_by_id: Mapping[str, Mapping[str, Any]],
) -> List[str]:
    gaps: List[str] = []
    for source_id in source_ids:
        source = source_by_id.get(source_id)
        if not isinstance(source, Mapping):
            gaps.append("source_id_not_registered")
            continue
        source_type = str(source.get("type", "unknown"))
        if source_type == "assumption":
            gaps.append("assumption_source_requires_external_replacement_or_bounds")
        elif source_type in {"paper", "report", "dataset"} and not source.get("url"):
            gaps.append("source_record_missing_public_url")
    return sorted(set(gaps))


def _target_grade(current: str, mode: str) -> str:
    if current == "D":
        return "keep_speculative_isolated" if mode == "speculative" else "invalid_realistic_D"
    if current == "C":
        return "B"
    if current == "B":
        return "A"
    return "maintain_A"


def _gap_types(
    *,
    trust: str,
    source_types: Sequence[str],
    evidence_index: Mapping[str, Any],
    source_quality_gaps: Sequence[str],
    visibility: str,
) -> List[str]:
    gaps: List[str] = []
    if trust == "C":
        gaps.append("trust_grade_C_upgrade")
    if trust == "B":
        gaps.append("trust_grade_B_upgrade")
    if trust == "D":
        gaps.append("speculative_parameter_quarantine")
    if "assumption" in source_types:
        gaps.append("assumption_backed_value")
    if "missing" in source_types:
        gaps.append("missing_source_binding")
    if visibility != PUBLIC_VISIBILITY:
        gaps.append("internal_audit_only_not_browser_surface")
    if "source_record_missing_public_url" in source_quality_gaps:
        gaps.append("source_record_missing_public_url")
    if visibility == PUBLIC_VISIBILITY and evidence_index.get("has_uncertainty") is not True:
        gaps.append("uncertainty_contract_missing")
    if visibility == PUBLIC_VISIBILITY and evidence_index.get("defensibility_status") != "PASS":
        gaps.append("defensibility_failure")
    return sorted(set(gaps))


def _recommended_actions(gaps: Sequence[str], target_grade: str) -> List[str]:
    actions: List[str] = []
    if "assumption_backed_value" in gaps:
        actions.append("replace or bound assumption with primary paper, dataset, or mission-specific test evidence")
    if "trust_grade_C_upgrade" in gaps:
        actions.append("narrow uncertainty bounds and add source-specific derivation notes before promoting to B")
    if "trust_grade_B_upgrade" in gaps:
        actions.append("add independent confirming source or dataset before promoting to A")
    if "speculative_parameter_quarantine" in gaps:
        actions.append("keep D-grade controls out of realistic reporting unless source-backed physics replaces them")
    if "internal_audit_only_not_browser_surface" in gaps:
        actions.append("keep internal audit literals out of public browser surfaces while preserving CI audit coverage")
    if "source_record_missing_public_url" in gaps:
        actions.append("add a stable public URL or archival reference where source licensing permits")
    if "uncertainty_contract_missing" in gaps:
        actions.append("add uncertainty distribution or interval contract")
    if "defensibility_failure" in gaps:
        actions.append("fix p_success defensibility errors before public use")
    if not actions and target_grade == "maintain_A":
        actions.append("schedule periodic source freshness review")
    return actions


def _row(
    *,
    claim: Mapping[str, Any],
    registry_entry: Mapping[str, Any],
    evidence_entry: Mapping[str, Any],
    source_by_id: Mapping[str, Mapping[str, Any]],
    sensitivity: Mapping[str, Any],
) -> Dict[str, Any]:
    parameter_id = str(claim["parameter_id"])
    source_ids = [str(item) for item in claim.get("evidence_source_ids", []) if isinstance(item, str)]
    source_types = _source_types(source_ids, source_by_id)
    source_quality_gaps = _source_quality_gaps(source_ids, source_by_id)
    trust = str(claim.get("trust_grade", "D"))
    mode = str(claim.get("mode", "realistic"))
    affects_core = bool(registry_entry.get("affects_core_probability", False))
    public_surfaces = _public_surfaces(registry_entry)
    visibility = _visibility(registry_entry)
    sensitivity_values = _sensitivity_for(parameter_id, sensitivity)
    influence = float(sensitivity_values["influence_score"] or 0.0)
    source_score = sum(SOURCE_PENALTY.get(source_type, 1.5) for source_type in source_types)
    priority_score = (
        TRUST_PENALTY.get(trust, 5.0)
        + source_score
        + (1.25 if affects_core else 0.0)
        + (0.75 if "browser" in public_surfaces else 0.0)
        + min(5.0, influence)
    )
    target_grade = _target_grade(trust, mode)
    gaps = _gap_types(
        trust=trust,
        source_types=source_types,
        evidence_index=evidence_entry,
        source_quality_gaps=source_quality_gaps,
        visibility=visibility,
    )
    return {
        "campaign_id": "euc-" + parameter_id.replace(".", "-").replace("_", "-"),
        "parameter_id": parameter_id,
        "visibility": visibility,
        "current_trust_grade": trust,
        "target_trust_grade": target_grade,
        "mode": mode,
        "classification": registry_entry.get("classification"),
        "category": registry_entry.get("category"),
        "affects_core_probability": affects_core,
        "public_surfaces": public_surfaces,
        "evidence_source_ids": source_ids,
        "source_types": source_types,
        "source_quality_gaps": source_quality_gaps,
        "value_origin_type": evidence_entry.get("value_origin_type"),
        "has_uncertainty": evidence_entry.get("has_uncertainty") is True,
        "defensibility_status": evidence_entry.get("defensibility_status"),
        "sensitivity": sensitivity_values,
        "priority_score": _round(priority_score, 9),
        "gap_types": gaps,
        "recommended_actions": _recommended_actions(gaps, target_grade),
        "acceptance_criteria": [
            "new or upgraded source ids resolve in parameters/registry/evidence_sources.v1.json",
            "parameter claim justification explains the promoted trust grade",
            "uncertainty bounds are narrowed only when source evidence supports it",
            "strict evidence, parameter, and browser-dataset validators pass",
        ],
        "blocked_claims": [
            "automatic trust promotion",
            "trust upgraded without source change",
            "assumption treated as measured evidence",
            "realistic mode uses D-grade parameter",
            "certified or flight-ready evidence closure",
        ],
    }


def build_evidence_upgrade_campaign(repo_root: Path) -> Dict[str, Any]:
    claims = _load_json(repo_root / SOURCE_PARAMETER_CLAIMS)
    registry = _load_json(repo_root / SOURCE_PARAMETER_REGISTRY)
    sources = _load_json(repo_root / SOURCE_EVIDENCE_SOURCES)
    evidence_index = _load_json(repo_root / SOURCE_EVIDENCE_INDEX)
    sensitivity = _load_json(repo_root / SOURCE_SENSITIVITY)
    source_by_id = _source_lookup(sources)
    registry_by_id = _registry_lookup(registry)
    rows = []
    distribution: Dict[str, int] = {}
    for claim in claims.get("claims", []):
        if not isinstance(claim, Mapping) or not isinstance(claim.get("parameter_id"), str):
            continue
        parameter_id = str(claim["parameter_id"])
        trust = str(claim.get("trust_grade", "D"))
        distribution[trust] = distribution.get(trust, 0) + 1
        rows.append(
            _row(
                claim=claim,
                registry_entry=registry_by_id.get(parameter_id, {}),
                evidence_entry=evidence_index.get(parameter_id, {}),
                source_by_id=source_by_id,
                sensitivity=sensitivity,
            )
        )
    rows.sort(key=lambda item: (-float(item["priority_score"]), item["parameter_id"]))
    public_rows = [row for row in rows if row.get("visibility") == PUBLIC_VISIBILITY]
    internal_rows = [row for row in rows if row.get("visibility") == INTERNAL_VISIBILITY]
    assumption_rows = [row for row in rows if "assumption" in row["source_types"]]
    public_distribution: Dict[str, int] = {}
    source_type_distribution: Dict[str, int] = {}
    for row in rows:
        if row.get("visibility") == PUBLIC_VISIBILITY:
            grade = str(row.get("current_trust_grade"))
            public_distribution[grade] = public_distribution.get(grade, 0) + 1
        for source_type in row.get("source_types", []):
            source_type_distribution[str(source_type)] = source_type_distribution.get(str(source_type), 0) + 1
    top_priorities = rows[:15]
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "public_scope": PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root),
        "campaign_policy": {
            "ranking_method": "trust_penalty + source_type_penalty + public_surface_bonus + core_probability_bonus + capped_sensitivity",
            "trust_upgrade_policy": "C targets B, B targets A, D remains speculative unless source-backed physics replaces it",
            "no_auto_upgrade": True,
        },
        "claim_count": len(rows),
        "trust_distribution": dict(sorted(distribution.items())),
        "public_trust_distribution": dict(sorted(public_distribution.items())),
        "public_campaign_count": len(public_rows),
        "internal_audit_count": len(internal_rows),
        "assumption_backed_count": len(assumption_rows),
        "source_type_distribution": dict(sorted(source_type_distribution.items())),
        "top_priority_count": len(top_priorities),
        "top_priorities": top_priorities,
        "campaign_rows": rows,
        "public_campaign_rows": public_rows,
        "internal_audit_rollup": {
            "visibility": INTERNAL_VISIBILITY,
            "row_count": len(internal_rows),
            "trust_distribution": dict(
                sorted(
                    {
                        grade: sum(1 for row in internal_rows if row.get("current_trust_grade") == grade)
                        for grade in TRUST_ORDER
                    }.items()
                )
            ),
            "public_surface_policy": "internal audit rows remain excluded from browser route detail views",
        },
        "rollup": {
            "grade_A_count": distribution.get("A", 0),
            "grade_B_count": distribution.get("B", 0),
            "grade_C_count": distribution.get("C", 0),
            "grade_D_count": distribution.get("D", 0),
            "rows_targeting_A": sum(1 for row in rows if row["target_trust_grade"] == "A"),
            "rows_targeting_B": sum(1 for row in rows if row["target_trust_grade"] == "B"),
            "speculative_quarantine_count": sum(1 for row in rows if row["target_trust_grade"] == "keep_speculative_isolated"),
            "public_upgrade_candidate_count": sum(
                1
                for row in public_rows
                if row.get("target_trust_grade") in {"A", "B", "keep_speculative_isolated"}
            ),
        },
        "external_evidence_gaps": [
            "primary-source replacements for assumption-backed priors",
            "independent datasets for B-to-A promotion",
            "source-backed uncertainty narrowing for high-priority C-grade parameters",
            "stable public URLs or archival references for source records that currently lack public URLs",
            "periodic source freshness review",
        ],
        "blocked_claims": [
            "evidence campaign completed",
            "trust grades upgraded automatically",
            "source correctness proven",
            "external validation completed",
            "certified or flight-ready",
        ],
        "interpretation_limits": [
            "This artifact ranks evidence-upgrade work; it does not change trust grades.",
            "Priority scores are repository triage aids, not scientific truth scores.",
            "External source review remains required before any trust-grade promotion.",
        ],
    }


def _source_hashes(payload: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    items = payload.get("source_artifacts")
    if not isinstance(items, list):
        return out
    for item in items:
        if isinstance(item, Mapping) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str):
            out[str(item["path"])] = str(item["sha256"])
    return out


def validate_evidence_upgrade_campaign(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r}")
    if payload.get("generator") != GENERATOR:
        errors.append(f"generator mismatch: {payload.get('generator')!r}")
    if payload.get("public_scope") != PUBLIC_SCOPE:
        errors.append(f"public_scope mismatch: {payload.get('public_scope')!r}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    source_hashes = _source_hashes(payload)
    for path in (
        SOURCE_PARAMETER_CLAIMS,
        SOURCE_PARAMETER_REGISTRY,
        SOURCE_EVIDENCE_SOURCES,
        SOURCE_EVIDENCE_INDEX,
        SOURCE_SENSITIVITY,
        SOURCE_P_SUCCESS,
    ):
        if len(source_hashes.get(path, "")) != 64:
            errors.append(f"source_artifacts missing sha256 for {path}")
    rows = payload.get("campaign_rows")
    if not isinstance(rows, list) or not rows:
        errors.append("campaign_rows must be non-empty list")
        rows = []
    if payload.get("claim_count") != len(rows):
        errors.append("claim_count must match campaign_rows length")
    public_rows = payload.get("public_campaign_rows")
    if not isinstance(public_rows, list) or not public_rows:
        errors.append("public_campaign_rows must be non-empty list")
        public_rows = []
    if payload.get("public_campaign_count") != len(public_rows):
        errors.append("public_campaign_count must match public_campaign_rows length")
    internal_rollup = payload.get("internal_audit_rollup")
    if not isinstance(internal_rollup, Mapping):
        errors.append("internal_audit_rollup must be object")
        internal_rollup = {}
    if payload.get("internal_audit_count") != internal_rollup.get("row_count"):
        errors.append("internal_audit_count must match internal_audit_rollup.row_count")
    source_type_distribution = payload.get("source_type_distribution")
    if not isinstance(source_type_distribution, Mapping) or not source_type_distribution:
        errors.append("source_type_distribution must be non-empty object")
    top = payload.get("top_priorities")
    if not isinstance(top, list) or not top:
        errors.append("top_priorities must be non-empty list")
        top = []
    if payload.get("top_priority_count") != len(top):
        errors.append("top_priority_count must match top_priorities length")
    if len(top) > 15:
        errors.append("top_priorities must contain at most 15 rows")
    seen: set[str] = set()
    previous_score: float | None = None
    distribution: Dict[str, int] = {}
    public_distribution: Dict[str, int] = {}
    public_ids: set[str] = set()
    internal_count = 0
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"campaign_rows[{index}] must be object")
            continue
        campaign_id = row.get("campaign_id")
        parameter_id = row.get("parameter_id")
        if not isinstance(campaign_id, str) or not campaign_id.startswith("euc-"):
            errors.append(f"campaign_rows[{index}].campaign_id must start with euc-")
        if not isinstance(parameter_id, str) or not parameter_id:
            errors.append(f"campaign_rows[{index}].parameter_id must be non-empty string")
        elif parameter_id in seen:
            errors.append(f"duplicate campaign parameter_id: {parameter_id}")
        else:
            seen.add(parameter_id)
        trust = row.get("current_trust_grade")
        if trust not in TRUST_ORDER:
            errors.append(f"campaign_rows[{index}].current_trust_grade invalid")
        else:
            distribution[str(trust)] = distribution.get(str(trust), 0) + 1
        visibility = row.get("visibility")
        if visibility == PUBLIC_VISIBILITY:
            public_ids.add(str(parameter_id))
            if trust in TRUST_ORDER:
                public_distribution[str(trust)] = public_distribution.get(str(trust), 0) + 1
        elif visibility == INTERNAL_VISIBILITY:
            internal_count += 1
        else:
            errors.append(f"campaign_rows[{index}].visibility invalid")
        score = row.get("priority_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or float(score) < 0.0:
            errors.append(f"campaign_rows[{index}].priority_score must be >= 0")
        else:
            if previous_score is not None and float(score) > previous_score + 1e-12:
                errors.append("campaign_rows must be sorted by descending priority_score")
            previous_score = float(score)
        if row.get("mode") == "realistic" and trust == "D":
            errors.append(f"campaign_rows[{index}] realistic mode cannot target D-grade as valid")
        if trust == "D" and row.get("target_trust_grade") != "keep_speculative_isolated":
            errors.append(f"campaign_rows[{index}] D-grade rows must stay speculative-isolated")
        for field in (
            "evidence_source_ids",
            "source_types",
            "source_quality_gaps",
            "gap_types",
            "recommended_actions",
            "acceptance_criteria",
            "blocked_claims",
        ):
            value = row.get(field)
            if not isinstance(value, list):
                errors.append(f"campaign_rows[{index}].{field} must be list")
        blocked = row.get("blocked_claims")
        if isinstance(blocked, list):
            if "trust upgraded without source change" not in blocked:
                errors.append(f"campaign_rows[{index}].blocked_claims must block source-free upgrades")
            if "automatic trust promotion" not in blocked:
                errors.append(f"campaign_rows[{index}].blocked_claims must block automatic trust promotion")
    if payload.get("trust_distribution") != dict(sorted(distribution.items())):
        errors.append("trust_distribution must match campaign rows")
    if payload.get("public_trust_distribution") != dict(sorted(public_distribution.items())):
        errors.append("public_trust_distribution must match public campaign rows")
    if internal_count <= 0:
        errors.append("internal audit count must be positive")
    if internal_count != payload.get("internal_audit_count"):
        errors.append("internal_audit_count must match campaign rows")
    public_row_ids = {
        str(row.get("parameter_id"))
        for row in public_rows
        if isinstance(row, Mapping) and isinstance(row.get("parameter_id"), str)
    }
    if public_ids != public_row_ids:
        errors.append("public_campaign_rows must equal public campaign row subset")
    expected_top_ids = [
        str(row.get("parameter_id"))
        for row in rows[: len(top)]
        if isinstance(row, Mapping) and isinstance(row.get("parameter_id"), str)
    ]
    actual_top_ids = [
        str(row.get("parameter_id"))
        for row in top
        if isinstance(row, Mapping) and isinstance(row.get("parameter_id"), str)
    ]
    if actual_top_ids != expected_top_ids:
        errors.append("top_priorities must equal the first ranked campaign rows")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
    else:
        if rollup.get("grade_C_count", 0) <= 0:
            errors.append("rollup.grade_C_count must be positive for current campaign")
        if rollup.get("rows_targeting_B", 0) <= 0:
            errors.append("rollup.rows_targeting_B must be positive")
        if rollup.get("speculative_quarantine_count") != distribution.get("D", 0):
            errors.append("rollup.speculative_quarantine_count must match D-grade rows")
    for field in ("external_evidence_gaps", "blocked_claims", "interpretation_limits"):
        value = payload.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"{field} must be non-empty list")
    blocked = payload.get("blocked_claims")
    if isinstance(blocked, list) and "trust grades upgraded automatically" not in blocked:
        errors.append("blocked_claims must block automatic trust upgrades")
    if isinstance(blocked, list) and "source correctness proven" not in blocked:
        errors.append("blocked_claims must block source correctness proof")
    return errors
