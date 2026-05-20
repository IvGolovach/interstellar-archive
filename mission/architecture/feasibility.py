"""Roadmap item 13 cost/procurement/architecture feasibility screen.

This artifact deliberately models absence as first-class data: proxy cost
pressure is visible, while procurement-grade estimates, launch integration, and
flight architecture approval remain external evidence gates.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


SCHEMA_VERSION = "cost_procurement_architecture_feasibility.v1"
GENERATOR = "scripts/build_cost_procurement_architecture_feasibility_artifact.py"
PUBLIC_SCOPE = "roadmap_13_cost_procurement_architecture_screen"
SOURCE_MISSION_FEASIBILITY = "artifacts/mission_feasibility_screen.v1.json"
SOURCE_OPTIMIZATION_V2 = "artifacts/optimization_v2_frontier.v1.json"
SOURCE_OPTIMIZATION_SEARCH_SPACE = "artifacts/optimization_search_space.v1.json"
SOURCE_CAPSULE = "artifacts/capsule_survivability_lab.v1.json"
SOURCE_SPEC = "mission/COST_PROCUREMENT_ARCHITECTURE_FEASIBILITY_SPEC_v1.md"
SOURCE_ROADMAP_DOC = "docs/FULL_V2_ROADMAP_CLOSURE.md"
SOURCE_IMPLEMENTATION = "mission/architecture/feasibility.py"
SOURCE_BUILDER = "scripts/build_cost_procurement_architecture_feasibility_artifact.py"
SOURCE_VALIDATOR = "scripts/ci/cost_procurement_architecture_feasibility_validate.py"

BLOCKED_CLAIMS = [
    "procurement-grade cost estimate",
    "vendor quote obtained",
    "budget approved",
    "launch vehicle selected",
    "flight-ready architecture selected",
    "qualification complete",
    "regulatory or operations approval complete",
    "mission feasible",
]
PROCUREMENT_GATE_IDS = [
    "vendor_quote_gate",
    "launch_integration_gate",
    "basis_of_estimate_gate",
    "regulatory_operations_gate",
]
ARCHITECTURE_STATUSES = {"review_required", "blocked_external_evidence"}


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


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


def _mass_budget(capsule: Mapping[str, Any]) -> Dict[str, Any]:
    design = capsule.get("capsule_design", {})
    if not isinstance(design, Mapping):
        design = {}
    budget = design.get("mass_budget", {})
    if not isinstance(budget, Mapping):
        budget = {}
    mass = float(budget.get("total_mass_kg", budget.get("configured_capsule_mass_kg", 0.0)))
    if mass <= 0.0:
        mass = float(budget.get("component_mass_kg", 0.0))
    return {
        "capsule_mass_kg": _round(mass),
        "component_mass_kg": _round(float(budget.get("component_mass_kg", mass))),
        "configured_capsule_mass_kg": _round(float(budget.get("configured_capsule_mass_kg", mass))),
        "declared_margin_kg": _round(float(budget.get("declared_margin_kg", 0.0))),
        "layer_ids": list(budget.get("layer_ids", [])) if isinstance(budget.get("layer_ids"), list) else [],
    }


def _cost_model(capsule_mass_kg: float, optimization_v2: Mapping[str, Any]) -> Dict[str, Any]:
    candidates = [item for item in optimization_v2.get("candidates", []) if isinstance(item, Mapping)]
    cost_scores = [
        float(item.get("scores", {}).get("cost_proxy"))
        for item in candidates
        if isinstance(item.get("scores"), Mapping) and _is_number(item.get("scores", {}).get("cost_proxy"))
    ]
    qualification_cost_musd = 180.0 + 0.42 * capsule_mass_kg
    launch_architecture_cost_musd = 650.0 + 1.8 * capsule_mass_kg
    return {
        "method": "bounded_screening_proxy",
        "model": "order_of_magnitude_architecture_cost_screen_v1",
        "currency_year": None,
        "calibrated_cost_model_available": False,
        "cost_boundary": "screening proxy only; not procurement-grade estimate",
        "capsule_mass_kg": _round(capsule_mass_kg),
        "qualification_cost_proxy_musd": _round(qualification_cost_musd),
        "launch_architecture_cost_proxy_musd": _round(launch_architecture_cost_musd),
        "optimization_cost_proxy_min": _round(min(cost_scores)) if cost_scores else None,
        "optimization_cost_proxy_max": _round(max(cost_scores)) if cost_scores else None,
        "components": [
            {
                "id": "capsule_qualification_proxy",
                "value_musd": _round(qualification_cost_musd),
                "source_ref": SOURCE_CAPSULE,
                "boundary": "mass-scaled qualification proxy, not a vendor estimate",
            },
            {
                "id": "launch_architecture_proxy",
                "value_musd": _round(launch_architecture_cost_musd),
                "source_ref": SOURCE_CAPSULE,
                "boundary": "mass-scaled architecture proxy, not launch procurement pricing",
            },
            {
                "id": "kinetic_energy_pressure",
                "source_ref": f"{SOURCE_MISSION_FEASIBILITY}#scenario_rows[].cost_energy_proxy",
                "boundary": "energy scaling only",
            },
            {
                "id": "optimization_cost_pressure",
                "source_ref": f"{SOURCE_OPTIMIZATION_V2}#candidates[].scores.cost_proxy",
                "boundary": "engineering-resource screen only",
            },
        ],
    }


def _procurement_gates() -> List[Dict[str, Any]]:
    return [
        {
            "id": "vendor_quote_gate",
            "status": "external_required",
            "required_evidence": ["vendor quote", "basis of estimate", "assumptions/date/currency"],
            "blocked_claim": "vendor quote obtained",
        },
        {
            "id": "launch_integration_gate",
            "status": "external_required",
            "required_evidence": [
                "launch provider constraints",
                "payload interface assumptions",
                "trajectory/integration study",
            ],
            "blocked_claim": "launch vehicle selected",
        },
        {
            "id": "basis_of_estimate_gate",
            "status": "external_required",
            "required_evidence": ["work-breakdown structure", "confidence range", "review date and estimator"],
            "blocked_claim": "budget approved",
        },
        {
            "id": "regulatory_operations_gate",
            "status": "external_required",
            "required_evidence": ["regulatory review", "operations concept", "long-duration responsibility model"],
            "blocked_claim": "regulatory or operations approval complete",
        },
    ]


def _optimization_cost_axis(optimization_v2: Mapping[str, Any]) -> Dict[str, Any]:
    axis_contract = optimization_v2.get("axis_contract", {})
    axes = axis_contract.get("axes", []) if isinstance(axis_contract, Mapping) else []
    cost_axis = next(
        (axis for axis in axes if isinstance(axis, Mapping) and axis.get("id") == "cost_proxy"),
        {},
    )
    candidates = [item for item in optimization_v2.get("candidates", []) if isinstance(item, Mapping)]
    scores: List[float] = []
    top_candidate_id = optimization_v2.get("rollup", {}).get("top_candidate_id") if isinstance(optimization_v2.get("rollup"), Mapping) else None
    top_candidate: Mapping[str, Any] = {}
    for candidate in candidates:
        score = candidate.get("scores", {}).get("cost_proxy") if isinstance(candidate.get("scores"), Mapping) else None
        if _is_number(score):
            scores.append(float(score))
        if isinstance(top_candidate_id, str) and candidate.get("candidate_id") == top_candidate_id:
            top_candidate = candidate
    top_scores = top_candidate.get("scores", {}) if isinstance(top_candidate.get("scores"), Mapping) else {}
    rollup = optimization_v2.get("rollup", {})
    if not isinstance(rollup, Mapping):
        rollup = {}
    return {
        "axis_id": "cost_proxy",
        "status": cost_axis.get("status"),
        "method": cost_axis.get("method"),
        "source_ref": cost_axis.get("source_ref"),
        "candidate_count": optimization_v2.get("candidate_count"),
        "frontier_candidate_count": optimization_v2.get("frontier_candidate_count"),
        "min_score": _round(min(scores)) if scores else None,
        "max_score": _round(max(scores)) if scores else None,
        "top_candidate_id": top_candidate_id,
        "top_candidate_cost_proxy": _round(float(top_scores["cost_proxy"])) if _is_number(top_scores.get("cost_proxy")) else None,
        "top_candidate_qualification_gap": _round(float(top_scores["qualification_gap"]))
        if _is_number(top_scores.get("qualification_gap"))
        else None,
        "calibrated_cost_model_available": rollup.get("calibrated_cost_model_available"),
        "qualification_complete": rollup.get("qualification_complete"),
        "blocked_claims": list(optimization_v2.get("blocked_claims", [])),
        "external_evidence_gaps": list(optimization_v2.get("external_evidence_gaps", [])),
    }


def _row_status(row: Mapping[str, Any]) -> str:
    feasibility = row.get("feasibility", {})
    blockers = feasibility.get("blockers", []) if isinstance(feasibility, Mapping) else []
    if isinstance(blockers, list) and (
        "flight_horizon_exceeds_100_myr_review_band" in blockers
        or "black_hole_environment_model_external_required" in blockers
    ):
        return "blocked_external_evidence"
    return "review_required"


def _architecture_rows(
    mission_feasibility: Mapping[str, Any],
    *,
    capsule_mass_kg: float,
) -> List[Dict[str, Any]]:
    rows = [row for row in mission_feasibility.get("scenario_rows", []) if isinstance(row, Mapping)]
    relatives = [
        float(row.get("cost_energy_proxy", {}).get("relative_to_23_17_km_s"))
        for row in rows
        if isinstance(row.get("cost_energy_proxy"), Mapping)
        and _is_number(row.get("cost_energy_proxy", {}).get("relative_to_23_17_km_s"))
    ]
    max_relative = max(relatives) if relatives else 1.0
    out: List[Dict[str, Any]] = []
    default_id = mission_feasibility.get("default_scenario_id")
    for row in rows:
        cost = row.get("cost_energy_proxy", {})
        if not isinstance(cost, Mapping):
            cost = {}
        feasibility = row.get("feasibility", {})
        blockers = feasibility.get("blockers", []) if isinstance(feasibility, Mapping) else []
        relative = float(cost.get("relative_to_23_17_km_s", 0.0)) if _is_number(cost.get("relative_to_23_17_km_s")) else 0.0
        pressure = _clamp01(relative / max_relative) if max_relative > 0.0 else 0.0
        out.append(
            {
                "row_id": f"cost-arch-{row.get('target_id')}-{row.get('velocity_id')}",
                "source_feasibility_row_id": row.get("id"),
                "source_capsule_row_id": row.get("source_capsule_row_id"),
                "is_default_reference": row.get("id") == default_id,
                "target_id": row.get("target_id"),
                "target_label": row.get("target_label"),
                "velocity_id": row.get("velocity_id"),
                "velocity_label": row.get("velocity_label"),
                "flight_years": row.get("flight_years"),
                "time_horizon_class": row.get("time_horizon_class"),
                "capsule_mass_kg": _round(capsule_mass_kg),
                "capsule_kinetic_energy_j": cost.get("capsule_kinetic_energy_j"),
                "relative_to_23_17_km_s": cost.get("relative_to_23_17_km_s"),
                "cost_proxy_score": _round(pressure),
                "procurement_status": "external_required",
                "architecture_feasibility_status": _row_status(row),
                "scenario_feasibility_status": feasibility.get("status") if isinstance(feasibility, Mapping) else None,
                "review_blockers": list(blockers) if isinstance(blockers, list) else [],
                "claim_boundary": "Scenario row is an architecture screening proxy, not a selected mission design.",
                "external_evidence_gaps": list(
                    dict.fromkeys(
                        [
                            *row.get("external_evidence_gaps", []),
                            "vendor/procurement-grade estimates",
                            "launch vehicle integration data",
                            "architecture trade study with independently reviewed assumptions",
                        ]
                    )
                )
                if isinstance(row.get("external_evidence_gaps"), list)
                else [
                    "vendor/procurement-grade estimates",
                    "launch vehicle integration data",
                    "architecture trade study with independently reviewed assumptions",
                ],
                "blocked_claims": list(dict.fromkeys([*row.get("blocked_claims", []), *BLOCKED_CLAIMS]))
                if isinstance(row.get("blocked_claims"), list)
                else list(BLOCKED_CLAIMS),
            }
        )
    out.sort(key=lambda item: (str(item["target_id"]), float(item["flight_years"]), str(item["velocity_id"])))
    return out


def _architecture_options(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    def find(target_id: str, velocity_id: str) -> Mapping[str, Any]:
        return next(
            (
                row
                for row in rows
                if row.get("target_id") == target_id and row.get("velocity_id") == velocity_id
            ),
            {},
        )

    selections = [
        ("reference_black_hole_conditional_45", find("reference-black-hole", "conditional-45")),
        ("alpha_centauri_concept_95", find("alpha-centauri-scale", "concept-95")),
        ("sgr_a_concept_95", find("sgr-a-rounded", "concept-95")),
    ]
    out: List[Dict[str, Any]] = []
    for option_id, row in selections:
        out.append(
            {
                "id": option_id,
                "source_row_id": row.get("row_id"),
                "target_id": row.get("target_id"),
                "velocity_id": row.get("velocity_id"),
                "flight_years": row.get("flight_years"),
                "cost_proxy_score": row.get("cost_proxy_score"),
                "status": "review_required",
                "external_gates": list(PROCUREMENT_GATE_IDS),
                "claim_boundary": "Architecture option for trade review only; no option is selected for flight.",
            }
        )
    return out


def build_cost_procurement_architecture_feasibility(repo_root: Path) -> Dict[str, Any]:
    mission_feasibility = _load_json(repo_root / SOURCE_MISSION_FEASIBILITY)
    optimization_v2 = _load_json(repo_root / SOURCE_OPTIMIZATION_V2)
    optimization_search_space = _load_json(repo_root / SOURCE_OPTIMIZATION_SEARCH_SPACE)
    capsule = _load_json(repo_root / SOURCE_CAPSULE)

    mass = _mass_budget(capsule)
    capsule_mass_kg = float(mass["capsule_mass_kg"])
    architecture_rows = _architecture_rows(mission_feasibility, capsule_mass_kg=capsule_mass_kg)
    cost_model = _cost_model(capsule_mass_kg, optimization_v2)
    optimization_axis = _optimization_cost_axis(optimization_v2)
    source_paths = [
        SOURCE_MISSION_FEASIBILITY,
        SOURCE_OPTIMIZATION_V2,
        SOURCE_OPTIMIZATION_SEARCH_SPACE,
        SOURCE_CAPSULE,
        SOURCE_SPEC,
        SOURCE_ROADMAP_DOC,
        SOURCE_IMPLEMENTATION,
        SOURCE_BUILDER,
        SOURCE_VALIDATOR,
    ]

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "public_scope": PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, source_paths),
        "roadmap_item": {
            "id": "roadmap-13",
            "title": "Cost, procurement, and architecture feasibility",
            "implementation_mode": "tracked_cost_procurement_architecture_screen",
            "summary": "Tracks proxy cost pressure, procurement gates, and architecture review status without procurement or flight-readiness claims.",
            "external_evidence_gaps": [
                "vendor/procurement-grade estimates",
                "launch vehicle integration data",
                "independent architecture trade study",
                "regulatory and operations review",
            ],
        },
        "claim_boundaries": {
            "artifact_status": "repo_native_screening_contract",
            "cost_status": "order_of_magnitude_proxy_only",
            "procurement_status": "external_required",
            "architecture_status": "concept_trade_screen_only",
            "browser_policy": "render committed artifact values only",
        },
        "mass_budget": mass,
        "cost_model": cost_model,
        "procurement_gates": _procurement_gates(),
        "architecture_row_count": len(architecture_rows),
        "architecture_rows": architecture_rows,
        "architecture_options": _architecture_options(architecture_rows),
        "optimization_cost_axis": optimization_axis,
        "search_space_cost_inputs": [
            item
            for item in optimization_search_space.get("parameters_considered", [])
            if isinstance(item, Mapping)
            and item.get("parameter_id")
            in {
                "correction_window.delta_v_budget_mps",
                "correction_window.power_available_w",
                "correction_window.specific_impulse_s",
                "correction_window.max_duration_years",
                "bh_parameters.distance_from_earth_ly",
            }
        ],
        "rollup": {
            "row_count": len(architecture_rows),
            "procurement_grade_estimate_available": False,
            "vendor_quote_count": 0,
            "launch_vehicle_selected": False,
            "architecture_selected_for_flight": False,
            "calibrated_cost_model_available": False,
            "qualification_complete": False,
            "all_rows_review_required": all(
                row.get("architecture_feasibility_status") in ARCHITECTURE_STATUSES for row in architecture_rows
            ),
            "external_gate_count": len(PROCUREMENT_GATE_IDS),
        },
        "blocked_claims": list(BLOCKED_CLAIMS),
        "external_evidence_gaps": [
            "vendor/procurement-grade estimates",
            "launch vehicle integration data",
            "independent basis-of-estimate review",
            "architecture trade study with launch provider constraints",
        ],
        "interpretation_limits": [
            "Cost values are screening proxies and are not vendor quotes or approved budgets.",
            "Procurement gates intentionally remain external_required until external records exist.",
            "Architecture rows compare concepts; they do not select a launch vehicle or flight-ready design.",
            "Browser UI may render this artifact but must not derive procurement truth client-side.",
        ],
    }
    payload["determinism_signature"] = hashlib.sha256(
        canonical_json(
            {
                "schema_version": payload["schema_version"],
                "source_artifacts": payload["source_artifacts"],
                "architecture_rows": [
                    {
                        "row_id": row["row_id"],
                        "cost_proxy_score": row["cost_proxy_score"],
                        "procurement_status": row["procurement_status"],
                        "architecture_feasibility_status": row["architecture_feasibility_status"],
                    }
                    for row in architecture_rows
                ],
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
    expected = {
        SOURCE_MISSION_FEASIBILITY,
        SOURCE_OPTIMIZATION_V2,
        SOURCE_OPTIMIZATION_SEARCH_SPACE,
        SOURCE_CAPSULE,
        SOURCE_SPEC,
        SOURCE_ROADMAP_DOC,
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


def validate_cost_procurement_architecture_feasibility(
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

    boundaries = payload.get("claim_boundaries")
    if not isinstance(boundaries, Mapping):
        errors.append("claim_boundaries must be object")
        boundaries = {}
    if boundaries.get("procurement_status") != "external_required":
        errors.append("claim_boundaries.procurement_status must be external_required")
    if boundaries.get("cost_status") != "order_of_magnitude_proxy_only":
        errors.append("claim_boundaries.cost_status must remain order_of_magnitude_proxy_only")

    cost_model = payload.get("cost_model")
    if not isinstance(cost_model, Mapping):
        errors.append("cost_model must be object")
        cost_model = {}
    for field in ("capsule_mass_kg", "qualification_cost_proxy_musd", "launch_architecture_cost_proxy_musd"):
        if not _is_number(cost_model.get(field)) or float(cost_model.get(field)) <= 0.0:
            errors.append(f"cost_model.{field} must be positive finite proxy")
    if cost_model.get("calibrated_cost_model_available") is not False:
        errors.append("cost_model.calibrated_cost_model_available must be false")
    if "procurement-grade" not in str(cost_model.get("cost_boundary", "")):
        errors.append("cost_model.cost_boundary must explicitly block procurement-grade interpretation")

    gates = payload.get("procurement_gates")
    if not isinstance(gates, list) or len(gates) != len(PROCUREMENT_GATE_IDS):
        errors.append("procurement_gates must include all external gates")
        gates = []
    gate_ids = [gate.get("id") for gate in gates if isinstance(gate, Mapping)]
    if gate_ids != PROCUREMENT_GATE_IDS:
        errors.append("procurement_gates ids/order mismatch")
    for index, gate in enumerate(gates):
        if not isinstance(gate, Mapping):
            errors.append(f"procurement_gates[{index}] must be object")
            continue
        if gate.get("status") != "external_required":
            errors.append(f"procurement_gates[{index}].status must be external_required")
        if not isinstance(gate.get("required_evidence"), list) or not gate["required_evidence"]:
            errors.append(f"procurement_gates[{index}].required_evidence must be non-empty")

    rows = payload.get("architecture_rows")
    if not isinstance(rows, list) or len(rows) != 15:
        errors.append("architecture_rows must contain exactly 15 rows")
        rows = []
    if payload.get("architecture_row_count") != len(rows):
        errors.append("architecture_row_count must equal len(architecture_rows)")
    default_seen = False
    row_ids: List[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"architecture_rows[{index}] must be object")
            continue
        prefix = f"architecture_rows[{index}]"
        row_id = row.get("row_id")
        if not isinstance(row_id, str) or not row_id.startswith("cost-arch-"):
            errors.append(f"{prefix}.row_id must start with cost-arch-")
        else:
            row_ids.append(row_id)
        for field in ("flight_years", "capsule_mass_kg", "capsule_kinetic_energy_j", "relative_to_23_17_km_s"):
            if not _is_number(row.get(field)) or float(row.get(field)) <= 0.0:
                errors.append(f"{prefix}.{field} must be positive finite")
        if not _is_number(row.get("cost_proxy_score")) or not 0.0 <= float(row.get("cost_proxy_score")) <= 1.0:
            errors.append(f"{prefix}.cost_proxy_score must be in [0,1]")
        if row.get("procurement_status") != "external_required":
            errors.append(f"{prefix}.procurement_status must be external_required")
        if row.get("architecture_feasibility_status") not in ARCHITECTURE_STATUSES:
            errors.append(f"{prefix}.architecture_feasibility_status must be review_required or blocked_external_evidence")
        if row.get("is_default_reference") is True:
            default_seen = row.get("target_id") == "reference-black-hole" and row.get("velocity_id") == "conditional-45"
        if not isinstance(row.get("external_evidence_gaps"), list) or not row["external_evidence_gaps"]:
            errors.append(f"{prefix}.external_evidence_gaps must be non-empty")
        blocked = row.get("blocked_claims")
        if not isinstance(blocked, list) or "procurement-grade cost estimate" not in blocked:
            errors.append(f"{prefix}.blocked_claims must block procurement-grade cost estimate")
        if isinstance(blocked, list) and "flight-ready architecture selected" not in blocked:
            errors.append(f"{prefix}.blocked_claims must block flight-ready architecture")
    if len(row_ids) != len(set(row_ids)):
        errors.append("architecture row ids must be unique")
    if not default_seen:
        errors.append("default reference black-hole conditional-45 architecture row missing")

    axis = payload.get("optimization_cost_axis")
    if not isinstance(axis, Mapping):
        errors.append("optimization_cost_axis must be object")
        axis = {}
    if axis.get("axis_id") != "cost_proxy":
        errors.append("optimization_cost_axis.axis_id must be cost_proxy")
    if axis.get("status") != "screening_proxy":
        errors.append("optimization_cost_axis.status must be screening_proxy")
    if axis.get("calibrated_cost_model_available") is not False:
        errors.append("optimization_cost_axis.calibrated_cost_model_available must be false")
    if axis.get("qualification_complete") is not False:
        errors.append("optimization_cost_axis.qualification_complete must be false")
    for field in ("min_score", "max_score", "top_candidate_cost_proxy", "top_candidate_qualification_gap"):
        value = axis.get(field)
        if value is not None and (not _is_number(value) or not 0.0 <= float(value) <= 1.0):
            errors.append(f"optimization_cost_axis.{field} must be null or in [0,1]")
    blocked_axis = axis.get("blocked_claims")
    if not isinstance(blocked_axis, list) or "procurement-grade cost estimate" not in blocked_axis:
        errors.append("optimization_cost_axis.blocked_claims must block procurement-grade cost estimate")

    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("row_count") != 15:
        errors.append("rollup.row_count must be 15")
    for field in (
        "procurement_grade_estimate_available",
        "launch_vehicle_selected",
        "architecture_selected_for_flight",
        "calibrated_cost_model_available",
        "qualification_complete",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")
    if rollup.get("vendor_quote_count") != 0:
        errors.append("rollup.vendor_quote_count must be 0")
    if rollup.get("all_rows_review_required") is not True:
        errors.append("rollup.all_rows_review_required must be true")

    blocked_claims = payload.get("blocked_claims")
    if not isinstance(blocked_claims, list):
        errors.append("blocked_claims must be list")
    else:
        for claim in BLOCKED_CLAIMS:
            if claim not in blocked_claims:
                errors.append(f"blocked_claims missing {claim}")
    if not isinstance(payload.get("external_evidence_gaps"), list) or not payload["external_evidence_gaps"]:
        errors.append("external_evidence_gaps must be non-empty")
    if not isinstance(payload.get("interpretation_limits"), list) or not payload["interpretation_limits"]:
        errors.append("interpretation_limits must be non-empty")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors
