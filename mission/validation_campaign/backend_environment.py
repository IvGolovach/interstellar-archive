"""Backend and line-of-sight environment validation-campaign artifacts.

These builders are repo-native planning/status surfaces only. They make the
missing external backend, state-trace, and line-of-sight environment evidence
auditable without converting local constants or assumptions into validation.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


BACKEND_SCHEMA_VERSION = "validation_campaign_independent_backend_execution.v1"
ENVIRONMENT_SCHEMA_VERSION = "validation_campaign_line_of_sight_environment.v1"

BACKEND_GENERATOR = "mission/validation_campaign/backend_environment.py:build_independent_backend_execution_plan"
ENVIRONMENT_GENERATOR = "mission/validation_campaign/backend_environment.py:build_line_of_sight_environment_model"
BACKEND_PUBLIC_SCOPE = "validation_campaign_independent_backend_execution_plan"
ENVIRONMENT_PUBLIC_SCOPE = "validation_campaign_line_of_sight_environment_model"

SOURCE_IMPLEMENTATION = "mission/validation_campaign/backend_environment.py"
SOURCE_INIT = "mission/validation_campaign/__init__.py"
SOURCE_DAG_BOUNDARY = "artifacts/mission_dag_v2_boundary.v1.json"
SOURCE_PHYSICS_COMPARISON = "artifacts/independent_physics_backend_comparison.v1.json"
SOURCE_REVIEW_PACK = "artifacts/external_validation_review_pack.v1.json"
SOURCE_FEASIBILITY = "artifacts/mission_feasibility_screen.v1.json"
SOURCE_BASELINE = "mission/BASELINE_SCENARIO_v1.json"
SOURCE_ENV_BRIEF = "docs/research/CAPSULE_ENVIRONMENT_DATA_BRIEF_v1.md"
SOURCE_PARAMETER_CLAIMS = "parameters/registry/parameter_claims.v1.json"
SOURCE_EVIDENCE_SOURCES = "parameters/registry/evidence_sources.v1.json"

BACKEND_SOURCE_PATHS = [
    SOURCE_DAG_BOUNDARY,
    SOURCE_PHYSICS_COMPARISON,
    SOURCE_REVIEW_PACK,
    SOURCE_IMPLEMENTATION,
    SOURCE_INIT,
]
ENVIRONMENT_SOURCE_PATHS = [
    SOURCE_FEASIBILITY,
    SOURCE_BASELINE,
    SOURCE_ENV_BRIEF,
    SOURCE_PARAMETER_CLAIMS,
    SOURCE_EVIDENCE_SOURCES,
    SOURCE_IMPLEMENTATION,
    SOURCE_INIT,
]

BLOCKED_CLAIMS = [
    "external validation completed",
    "third-party validated",
    "independent reproduction completed",
    "independent physics backend validated",
    "backend validation completed",
    "cross-backend comparison completed",
    "high-fidelity state trace complete",
    "certified",
    "flight-ready",
    "fixed mm/cm dust truth",
    "whole-path dust model validated",
    "target-region plasma validated",
]
BACKEND_FALSE_FIELDS = {
    "independent_external_backend_complete",
    "independent_physics_backend_validated",
    "independent_backend_validated",
    "cross_backend_comparison_completed",
    "cross_backend_comparison_available",
    "high_fidelity_state_trace_complete",
    "high_fidelity_state_trace_available",
    "external_validation_completed",
    "certification_go",
    "flight_readiness_go",
}
ENVIRONMENT_FALSE_FIELDS = {
    "line_of_sight_environment_validated",
    "fixed_mm_cm_dust_truth_claimed",
    "mm_cm_dust_truth_fixed",
    "fixed_truth_claimed",
    "target_region_plasma_validated",
    "whole_path_dust_model_validated",
    "external_validation_completed",
    "certification_go",
    "flight_readiness_go",
}
REQUIRED_BLOCKED_CLAIMS = {
    "external validation completed",
    "independent physics backend validated",
    "certified",
    "fixed mm/cm dust truth",
}


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


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


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


def _forbidden_true_paths(value: Any, field_names: set[str], prefix: str = "") -> List[str]:
    paths: List[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_str = str(key)
            path = f"{prefix}.{key_str}" if prefix else key_str
            if key_str in field_names and item is True:
                paths.append(path)
            paths.extend(_forbidden_true_paths(item, field_names, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            paths.extend(_forbidden_true_paths(item, field_names, path))
    return paths


def _validate_no_overclaims(payload: Mapping[str, Any], field_names: set[str], errors: List[str]) -> None:
    for path in _forbidden_true_paths(payload, field_names):
        errors.append(f"{path} cannot be true")


def _validate_blocked_claims(payload: Mapping[str, Any], errors: List[str]) -> None:
    blocked = payload.get("blocked_claims")
    if not isinstance(blocked, list):
        errors.append("blocked_claims must be list")
        return
    missing = sorted(REQUIRED_BLOCKED_CLAIMS - set(str(item) for item in blocked))
    for claim in missing:
        errors.append(f"blocked_claims missing {claim}")


def _sorted_strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value if isinstance(item, str))


def build_independent_backend_execution_plan(repo_root: Path) -> Dict[str, Any]:
    dag_boundary = _load_json(repo_root / SOURCE_DAG_BOUNDARY)
    physics_comparison = _load_json(repo_root / SOURCE_PHYSICS_COMPARISON)
    review_pack = _load_json(repo_root / SOURCE_REVIEW_PACK)
    modules = dag_boundary.get("module_boundaries", [])
    if not isinstance(modules, list):
        modules = []

    module_rows: List[Dict[str, Any]] = []
    for module in sorted(
        (item for item in modules if isinstance(item, Mapping)),
        key=lambda item: str(item.get("module_id", "")),
    ):
        support = module.get("current_v1_support", {})
        if not isinstance(support, Mapping):
            support = {}
        module_rows.append(
            {
                "module_id": module.get("module_id"),
                "module_type": module.get("module_type"),
                "module_version": module.get("module_version"),
                "domain": module.get("domain"),
                "entrypoint": module.get("entrypoint"),
                "execution_status": "external_required",
                "repo_native_support_status": "reduced_order_wrapper_only"
                if support.get("wrapper_over_reduced_order_baseline") is True
                else "repo_native_contract_only",
                "independent_backend_id_declared": support.get("independent_backend_id_declared") is True,
                "high_fidelity_state_trace_available": support.get("high_fidelity_state_trace_available") is True,
                "cross_backend_comparison_available": support.get("cross_backend_comparison_available") is True,
                "state_trace_plan_status": "state_trace_contract_present_external_trace_missing",
                "external_backend_plan_status": "independent_backend_required",
                "open_external_evidence_gaps": _sorted_strings(module.get("open_external_evidence_gaps")),
                "v2_boundary_requirements": _sorted_strings(module.get("v2_boundary_requirements")),
                "blocked_claims": sorted(set(_sorted_strings(module.get("blocked_claims")) + list(BLOCKED_CLAIMS))),
            }
        )

    execution_tracks = [
        {
            "track_id": "independent_backend_implementation",
            "execution_status": "external_required",
            "acceptance_evidence": [
                "backend identifier outside the repository-native reduced-order implementation",
                "scenario-compatible input/output schema mapping",
                "reviewer-owned execution record",
            ],
        },
        {
            "track_id": "high_fidelity_state_trace_bundle",
            "execution_status": "external_required",
            "acceptance_evidence": [
                "per-module state trace hashes",
                "replayable fixtures for representative scenarios",
                "trace provenance tied to backend version",
            ],
        },
        {
            "track_id": "cross_backend_comparison_report",
            "execution_status": "external_required",
            "acceptance_evidence": [
                "signed comparison summary",
                "exception log for model disagreements",
                "raw outputs or immutable report URI",
            ],
        },
    ]
    physics_rollup = physics_comparison.get("rollup", {})
    if not isinstance(physics_rollup, Mapping):
        physics_rollup = {}
    review_rollup = review_pack.get("rollup", {})
    if not isinstance(review_rollup, Mapping):
        review_rollup = {}

    payload: Dict[str, Any] = {
        "schema_version": BACKEND_SCHEMA_VERSION,
        "generator": BACKEND_GENERATOR,
        "public_scope": BACKEND_PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, BACKEND_SOURCE_PATHS),
        "execution_plan_status": "repo_native_plan_ready_external_backend_not_complete",
        "review_pack_ref": SOURCE_REVIEW_PACK,
        "module_execution_count": len(module_rows),
        "module_execution_rows": module_rows,
        "execution_track_count": len(execution_tracks),
        "execution_tracks": execution_tracks,
        "readiness_snapshot": {
            "repo_analytic_check_count": physics_comparison.get("analytic_check_count"),
            "repo_analytic_checks_match": physics_rollup.get("all_repo_analytic_checks_match") is True,
            "review_case_count": review_pack.get("review_case_count"),
            "all_review_cases_require_external_review": review_rollup.get("all_cases_require_external_review") is True,
        },
        "rollup": {
            "module_execution_count": len(module_rows),
            "execution_track_count": len(execution_tracks),
            "all_modules_require_external_backend": all(
                row["execution_status"] == "external_required" for row in module_rows
            ),
            "repo_analytic_crosscheck_available": physics_rollup.get("all_repo_analytic_checks_match") is True,
            "external_validation_completed": False,
            "independent_external_backend_complete": False,
            "independent_physics_backend_validated": False,
            "cross_backend_comparison_completed": False,
            "high_fidelity_state_trace_complete": False,
            "certification_go": False,
            "flight_readiness_go": False,
        },
        "blocked_claims": list(BLOCKED_CLAIMS),
        "external_evidence_gaps": [
            "independent backend implementation outside this repository",
            "per-module high-fidelity state trace bundle",
            "cross-backend comparison report",
            "reviewer-owned execution record with raw outputs or report URI",
        ],
        "interpretation_limits": [
            "This is an execution plan and status surface, not backend validation.",
            "Repository analytic checks remain useful arithmetic guards, not independent physics proof.",
            "No certification, external validation, or high-fidelity state trace completion is unlocked here.",
        ],
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "module_execution_rows": [
                {
                    "module_id": row["module_id"],
                    "execution_status": row["execution_status"],
                    "external_backend_plan_status": row["external_backend_plan_status"],
                }
                for row in module_rows
            ],
            "execution_tracks": [
                {"track_id": row["track_id"], "execution_status": row["execution_status"]}
                for row in execution_tracks
            ],
            "rollup": payload["rollup"],
        }
    )
    return payload


def validate_independent_backend_execution_plan(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != BACKEND_SCHEMA_VERSION:
        errors.append(f"schema_version must be {BACKEND_SCHEMA_VERSION}")
    if payload.get("generator") != BACKEND_GENERATOR:
        errors.append(f"generator must be {BACKEND_GENERATOR}")
    if payload.get("public_scope") != BACKEND_PUBLIC_SCOPE:
        errors.append(f"public_scope must be {BACKEND_PUBLIC_SCOPE}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("execution_plan_status") != "repo_native_plan_ready_external_backend_not_complete":
        errors.append("execution_plan_status must keep external_backend_not_complete")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, required_paths=BACKEND_SOURCE_PATHS, errors=errors)

    rows = payload.get("module_execution_rows")
    if not isinstance(rows, list) or len(rows) != 6:
        errors.append("module_execution_rows must contain 6 rows")
        rows = []
    if payload.get("module_execution_count") != len(rows):
        errors.append("module_execution_count must equal len(module_execution_rows)")
    module_ids: List[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"module_execution_rows[{index}] must be object")
            continue
        prefix = f"module_execution_rows[{index}]"
        module_id = row.get("module_id")
        if not isinstance(module_id, str) or not module_id:
            errors.append(f"{prefix}.module_id must be non-empty string")
        else:
            module_ids.append(module_id)
        if row.get("execution_status") != "external_required":
            errors.append(f"{prefix}.execution_status must be external_required")
        if row.get("external_backend_plan_status") != "independent_backend_required":
            errors.append(f"{prefix}.external_backend_plan_status must be independent_backend_required")
        if row.get("state_trace_plan_status") != "state_trace_contract_present_external_trace_missing":
            errors.append(f"{prefix}.state_trace_plan_status must keep external trace missing")
        for field in (
            "independent_backend_id_declared",
            "high_fidelity_state_trace_available",
            "cross_backend_comparison_available",
        ):
            if row.get(field) is not False:
                errors.append(f"{prefix}.{field} must be false")
        if not isinstance(row.get("open_external_evidence_gaps"), list) or not row["open_external_evidence_gaps"]:
            errors.append(f"{prefix}.open_external_evidence_gaps must be non-empty list")
        row_blocked = row.get("blocked_claims")
        if not isinstance(row_blocked, list) or "independent physics backend validated" not in row_blocked:
            errors.append(f"{prefix}.blocked_claims must block independent physics backend validation")
    if len(module_ids) != len(set(module_ids)):
        errors.append("module_execution_rows module ids must be unique")

    tracks = payload.get("execution_tracks")
    if not isinstance(tracks, list) or len(tracks) != 3:
        errors.append("execution_tracks must contain 3 tracks")
        tracks = []
    if payload.get("execution_track_count") != len(tracks):
        errors.append("execution_track_count must equal len(execution_tracks)")
    for index, track in enumerate(tracks):
        if not isinstance(track, Mapping):
            errors.append(f"execution_tracks[{index}] must be object")
            continue
        if track.get("execution_status") != "external_required":
            errors.append(f"execution_tracks[{index}].execution_status must be external_required")
        if not isinstance(track.get("acceptance_evidence"), list) or not track["acceptance_evidence"]:
            errors.append(f"execution_tracks[{index}].acceptance_evidence must be non-empty")

    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("module_execution_count") != len(rows):
        errors.append("rollup.module_execution_count must equal len(module_execution_rows)")
    if rollup.get("execution_track_count") != len(tracks):
        errors.append("rollup.execution_track_count must equal len(execution_tracks)")
    if rollup.get("all_modules_require_external_backend") is not True:
        errors.append("rollup.all_modules_require_external_backend must be true")
    for field in (
        "external_validation_completed",
        "independent_external_backend_complete",
        "independent_physics_backend_validated",
        "cross_backend_comparison_completed",
        "high_fidelity_state_trace_complete",
        "certification_go",
        "flight_readiness_go",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")

    _validate_no_overclaims(payload, BACKEND_FALSE_FIELDS, errors)
    _validate_blocked_claims(payload, errors)
    if not isinstance(payload.get("external_evidence_gaps"), list) or not payload["external_evidence_gaps"]:
        errors.append("external_evidence_gaps must be non-empty")
    if not isinstance(payload.get("interpretation_limits"), list) or not payload["interpretation_limits"]:
        errors.append("interpretation_limits must be non-empty")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors


def _source_backed_anchors() -> List[Dict[str, Any]]:
    return [
        {
            "anchor_id": "local_neutral_h_density_vlism",
            "category": "gas",
            "evidence_class": "source_backed_anchor",
            "quantity": "local interstellar neutral hydrogen density",
            "value": 0.127,
            "sigma": 0.015,
            "units": "cm^-3",
            "converted_value_m3": 127000.0,
            "source_ref": SOURCE_ENV_BRIEF + "#interstellar-gas-and-plasma-anchors",
            "applicability_limits": [
                "local heliosphere/VLISM anchor only",
                "not a whole-path density average",
                "not target-region plasma validation",
            ],
        },
        {
            "anchor_id": "voyager_interstellar_plasma_density",
            "category": "plasma",
            "evidence_class": "source_backed_anchor",
            "quantity": "Voyager plasma/electron density order near heliopause",
            "value": 0.08,
            "units": "cm^-3",
            "converted_value_m3": 80000.0,
            "source_ref": SOURCE_ENV_BRIEF + "#interstellar-gas-and-plasma-anchors",
            "applicability_limits": [
                "local plasma-wave measurement context",
                "not a dense black-hole target environment",
                "not a universal trajectory average",
            ],
        },
        {
            "anchor_id": "ulysses_interstellar_dust_mass_density",
            "category": "dust",
            "evidence_class": "source_backed_anchor",
            "quantity": "Ulysses local interstellar dust mass density",
            "value": 2.1e-24,
            "sigma": 0.6e-24,
            "units": "kg/m^3",
            "source_ref": SOURCE_ENV_BRIEF + "#interstellar-dust-density-and-flux-anchors",
            "applicability_limits": [
                "local in-situ dust mass-density prior",
                "not a fixed mm/cm impact-tail flux",
                "not a whole-path deep-interstellar dust truth",
            ],
        },
        {
            "anchor_id": "alpha_centauri_distance_anchor",
            "category": "target",
            "evidence_class": "source_backed_anchor",
            "quantity": "Alpha Centauri approximate distance scale",
            "value": 4.3,
            "units": "ly",
            "source_ref": SOURCE_ENV_BRIEF + "#target-distance-and-time-of-flight-anchors",
            "applicability_limits": [
                "nearby-star scaling anchor",
                "not a navigation or arrival authority claim",
            ],
        },
        {
            "anchor_id": "sgr_a_distance_anchor",
            "category": "target",
            "evidence_class": "source_backed_anchor",
            "quantity": "Galactic-center distance anchor",
            "value": 26670.0,
            "units": "ly",
            "source_ref": SOURCE_ENV_BRIEF + "#target-distance-and-time-of-flight-anchors",
            "applicability_limits": [
                "precision astronomy distance anchor",
                "repo rows may use rounded scenario values",
                "not a target-corridor environment model",
            ],
        },
    ]


def _assumption_bound_tails(baseline: Mapping[str, Any]) -> List[Dict[str, Any]]:
    environment = baseline.get("environment_model", {})
    bh_parameters = baseline.get("bh_parameters", {})
    if not isinstance(environment, Mapping):
        environment = {}
    if not isinstance(bh_parameters, Mapping):
        bh_parameters = {}
    return [
        {
            "tail_id": "target_reference_black_hole_corridor",
            "category": "target",
            "evidence_class": "assumption_bound",
            "status": "external_evidence_required",
            "target_ids": ["reference-black-hole"],
            "source_anchor_ids": [],
            "fixed_truth_claimed": False,
            "claim_boundary": "Project-owned compact-object scenario; no external target-state or corridor model is claimed.",
        },
        {
            "tail_id": "mm_cm_dust_flux_tail",
            "category": "dust",
            "evidence_class": "assumption_bound",
            "status": "external_evidence_required",
            "source_anchor_ids": ["ulysses_interstellar_dust_mass_density"],
            "scenario_dust_flux_scale": environment.get("dust_flux_scale"),
            "scenario_max_dust_flux_scale": bh_parameters.get("max_dust_flux_scale"),
            "fixed_truth_claimed": False,
            "claim_boundary": "Local dust density anchors micron-class context; exact mm/cm deep-time flux remains unclosed.",
        },
        {
            "tail_id": "whole_path_ism_density_variation",
            "category": "dust",
            "evidence_class": "assumption_bound",
            "status": "external_evidence_required",
            "source_anchor_ids": [
                "local_neutral_h_density_vlism",
                "ulysses_interstellar_dust_mass_density",
            ],
            "fixed_truth_claimed": False,
            "claim_boundary": "Local ISM anchors are not whole-path averages for 4.3 ly, 1560 ly, or 26000 ly corridors.",
        },
        {
            "tail_id": "target_region_plasma_proxy",
            "category": "plasma",
            "evidence_class": "assumption_bound",
            "status": "external_evidence_required",
            "source_anchor_ids": ["voyager_interstellar_plasma_density"],
            "scenario_proxy_density_m3": environment.get("plasma_density_proxy_m3"),
            "scenario_max_proxy_density_m3": bh_parameters.get("max_plasma_density_proxy_m3"),
            "target_region_plasma_validated": False,
            "fixed_truth_claimed": False,
            "claim_boundary": "Black-hole/accretion plasma proxy is scenario-owned and not validated by local VLISM plasma anchors.",
        },
        {
            "tail_id": "target_state_and_navigation_stability",
            "category": "target",
            "evidence_class": "assumption_bound",
            "status": "external_evidence_required",
            "target_ids": ["alpha-centauri-scale", "reference-black-hole", "sgr-a-rounded"],
            "source_anchor_ids": ["alpha_centauri_distance_anchor", "sgr_a_distance_anchor"],
            "fixed_truth_claimed": False,
            "claim_boundary": "Distance anchors do not prove targetability, navigation authority, or target-state stability.",
        },
    ]


def _select_line_of_sight_rows(feasibility: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    scenario_rows = feasibility.get("scenario_rows", [])
    if not isinstance(scenario_rows, list):
        return []
    by_target: Dict[str, List[Mapping[str, Any]]] = {}
    for row in scenario_rows:
        if isinstance(row, Mapping) and isinstance(row.get("target_id"), str):
            by_target.setdefault(str(row["target_id"]), []).append(row)
    selected: List[Mapping[str, Any]] = []
    for target_id in sorted(by_target):
        rows = sorted(
            by_target[target_id],
            key=lambda item: (0 if item.get("velocity_id") == "conditional-45" else 1, str(item.get("velocity_id"))),
        )
        if rows:
            selected.append(rows[0])
    return selected


def _row_anchor_ids(target_id: str) -> List[str]:
    anchors = [
        "local_neutral_h_density_vlism",
        "voyager_interstellar_plasma_density",
        "ulysses_interstellar_dust_mass_density",
    ]
    if target_id == "alpha-centauri-scale":
        anchors.append("alpha_centauri_distance_anchor")
    if target_id == "sgr-a-rounded":
        anchors.append("sgr_a_distance_anchor")
    return sorted(anchors)


def _row_tail_ids(target_id: str) -> List[str]:
    tail_ids = [
        "mm_cm_dust_flux_tail",
        "whole_path_ism_density_variation",
        "target_region_plasma_proxy",
        "target_state_and_navigation_stability",
    ]
    if target_id == "reference-black-hole":
        tail_ids.append("target_reference_black_hole_corridor")
    return sorted(tail_ids)


def build_line_of_sight_environment_model(repo_root: Path) -> Dict[str, Any]:
    feasibility = _load_json(repo_root / SOURCE_FEASIBILITY)
    baseline = _load_json(repo_root / SOURCE_BASELINE)
    anchors = _source_backed_anchors()
    tails = _assumption_bound_tails(baseline)
    target_rows = []
    for row in _select_line_of_sight_rows(feasibility):
        target_id = str(row.get("target_id"))
        dust_screen = row.get("dust_screen", {})
        gas_screen = row.get("gas_screen", {})
        if not isinstance(dust_screen, Mapping):
            dust_screen = {}
        if not isinstance(gas_screen, Mapping):
            gas_screen = {}
        target_rows.append(
            {
                "target_id": target_id,
                "target_label": row.get("target_label"),
                "selected_feasibility_row_id": row.get("id"),
                "distance_ly": row.get("distance_ly"),
                "velocity_id": row.get("velocity_id"),
                "flight_years": row.get("flight_years"),
                "source_backed_anchor_ids": _row_anchor_ids(target_id),
                "assumption_bound_tail_ids": _row_tail_ids(target_id),
                "environment_validation_status": "line_of_sight_evidence_required",
                "local_dust_density_kg_m3": dust_screen.get("local_dust_density_kg_m3"),
                "local_neutral_h_mass_density_kg_m3": gas_screen.get("local_neutral_h_mass_density_kg_m3"),
                "fixed_mm_cm_dust_truth_claimed": False,
                "target_region_plasma_validated": False,
                "whole_path_dust_model_validated": False,
                "claim_boundary": "Line-of-sight row binds source anchors to explicit tails; it does not validate the target corridor.",
            }
        )
    target_rows.sort(key=lambda item: str(item["target_id"]))
    tail_categories = sorted({str(item["category"]) for item in tails})

    payload: Dict[str, Any] = {
        "schema_version": ENVIRONMENT_SCHEMA_VERSION,
        "generator": ENVIRONMENT_GENERATOR,
        "public_scope": ENVIRONMENT_PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": _source_artifacts(repo_root, ENVIRONMENT_SOURCE_PATHS),
        "environment_model_status": "repo_native_line_of_sight_environment_model_open",
        "source_backed_anchor_count": len(anchors),
        "source_backed_anchors": anchors,
        "assumption_bound_tail_count": len(tails),
        "assumption_bound_tails": tails,
        "assumption_tail_categories": tail_categories,
        "line_of_sight_target_count": len(target_rows),
        "line_of_sight_rows": target_rows,
        "rollup": {
            "source_backed_anchor_count": len(anchors),
            "assumption_bound_tail_count": len(tails),
            "line_of_sight_target_count": len(target_rows),
            "source_backed_anchors_separated_from_assumption_tails": True,
            "line_of_sight_environment_validated": False,
            "fixed_mm_cm_dust_truth_claimed": False,
            "target_region_plasma_validated": False,
            "whole_path_dust_model_validated": False,
            "external_validation_completed": False,
            "certification_go": False,
            "flight_readiness_go": False,
        },
        "blocked_claims": list(BLOCKED_CLAIMS),
        "external_evidence_gaps": [
            "target-specific line-of-sight dust and gas model",
            "mm/cm interstellar dust-tail evidence for selected corridors",
            "target-region plasma and accretion-state model",
            "navigation and target-state stability review",
        ],
        "interpretation_limits": [
            "Source-backed local anchors are not whole-path or target-region truth.",
            "Dust, target, and plasma tails remain assumption-bound until external evidence replaces them.",
            "No fixed mm/cm dust flux, certification, or external validation is claimed.",
        ],
    }
    payload["determinism_signature"] = _determinism_signature(
        {
            "schema_version": payload["schema_version"],
            "source_backed_anchor_ids": [item["anchor_id"] for item in anchors],
            "assumption_bound_tail_ids": [item["tail_id"] for item in tails],
            "line_of_sight_rows": [
                {
                    "target_id": row["target_id"],
                    "source_backed_anchor_ids": row["source_backed_anchor_ids"],
                    "assumption_bound_tail_ids": row["assumption_bound_tail_ids"],
                    "environment_validation_status": row["environment_validation_status"],
                }
                for row in target_rows
            ],
            "rollup": payload["rollup"],
        }
    )
    return payload


def validate_line_of_sight_environment_model(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != ENVIRONMENT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {ENVIRONMENT_SCHEMA_VERSION}")
    if payload.get("generator") != ENVIRONMENT_GENERATOR:
        errors.append(f"generator must be {ENVIRONMENT_GENERATOR}")
    if payload.get("public_scope") != ENVIRONMENT_PUBLIC_SCOPE:
        errors.append(f"public_scope must be {ENVIRONMENT_PUBLIC_SCOPE}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    if payload.get("environment_model_status") != "repo_native_line_of_sight_environment_model_open":
        errors.append("environment_model_status must keep environment model open")
    if repo_root is not None:
        _validate_sources(repo_root=repo_root, payload=payload, required_paths=ENVIRONMENT_SOURCE_PATHS, errors=errors)

    anchors = payload.get("source_backed_anchors")
    if not isinstance(anchors, list) or not anchors:
        errors.append("source_backed_anchors must be non-empty list")
        anchors = []
    if payload.get("source_backed_anchor_count") != len(anchors):
        errors.append("source_backed_anchor_count must equal len(source_backed_anchors)")
    anchor_ids: set[str] = set()
    for index, anchor in enumerate(anchors):
        if not isinstance(anchor, Mapping):
            errors.append(f"source_backed_anchors[{index}] must be object")
            continue
        anchor_id = anchor.get("anchor_id")
        if not isinstance(anchor_id, str) or not anchor_id:
            errors.append(f"source_backed_anchors[{index}].anchor_id must be non-empty string")
        else:
            anchor_ids.add(anchor_id)
        if anchor.get("evidence_class") != "source_backed_anchor":
            errors.append(f"source_backed_anchors[{index}].evidence_class must be source_backed_anchor")
        if not isinstance(anchor.get("applicability_limits"), list) or not anchor["applicability_limits"]:
            errors.append(f"source_backed_anchors[{index}].applicability_limits must be non-empty")
        if anchor.get("fixed_truth_claimed") is True:
            errors.append(f"source_backed_anchors[{index}].fixed_truth_claimed cannot be true")

    tails = payload.get("assumption_bound_tails")
    if not isinstance(tails, list) or not tails:
        errors.append("assumption_bound_tails must be non-empty list")
        tails = []
    if payload.get("assumption_bound_tail_count") != len(tails):
        errors.append("assumption_bound_tail_count must equal len(assumption_bound_tails)")
    tail_ids: set[str] = set()
    tail_categories: set[str] = set()
    for index, tail in enumerate(tails):
        if not isinstance(tail, Mapping):
            errors.append(f"assumption_bound_tails[{index}] must be object")
            continue
        prefix = f"assumption_bound_tails[{index}]"
        tail_id = tail.get("tail_id")
        if not isinstance(tail_id, str) or not tail_id:
            errors.append(f"{prefix}.tail_id must be non-empty string")
        else:
            tail_ids.add(tail_id)
        category = tail.get("category")
        if category not in {"target", "dust", "plasma"}:
            errors.append(f"{prefix}.category must be target, dust, or plasma")
        else:
            tail_categories.add(str(category))
        if tail.get("evidence_class") != "assumption_bound":
            errors.append(f"{prefix}.evidence_class must be assumption_bound")
        if tail.get("status") != "external_evidence_required":
            errors.append(f"{prefix}.status must be external_evidence_required")
        if tail.get("fixed_truth_claimed") is not False:
            errors.append(f"{prefix}.fixed_truth_claimed must be false")
        if category == "dust" and tail_id == "mm_cm_dust_flux_tail" and tail.get("fixed_truth_claimed") is not False:
            errors.append(f"{prefix}.fixed_truth_claimed must keep mm/cm dust tail open")
        for source_anchor_id in _sorted_strings(tail.get("source_anchor_ids")):
            if source_anchor_id and source_anchor_id not in anchor_ids:
                errors.append(f"{prefix}.source_anchor_ids references unknown anchor {source_anchor_id}")
    if payload.get("assumption_tail_categories") != sorted(tail_categories):
        errors.append("assumption_tail_categories must match assumption_bound_tails categories")
    if not {"target", "dust", "plasma"}.issubset(tail_categories):
        errors.append("assumption_bound_tails must include target, dust, and plasma categories")

    rows = payload.get("line_of_sight_rows")
    if not isinstance(rows, list) or len(rows) != 3:
        errors.append("line_of_sight_rows must contain 3 rows")
        rows = []
    if payload.get("line_of_sight_target_count") != len(rows):
        errors.append("line_of_sight_target_count must equal len(line_of_sight_rows)")
    target_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"line_of_sight_rows[{index}] must be object")
            continue
        prefix = f"line_of_sight_rows[{index}]"
        target_id = row.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            errors.append(f"{prefix}.target_id must be non-empty string")
        else:
            target_ids.add(target_id)
        if row.get("environment_validation_status") != "line_of_sight_evidence_required":
            errors.append(f"{prefix}.environment_validation_status must be line_of_sight_evidence_required")
        for field in (
            "fixed_mm_cm_dust_truth_claimed",
            "target_region_plasma_validated",
            "whole_path_dust_model_validated",
        ):
            if row.get(field) is not False:
                errors.append(f"{prefix}.{field} must be false")
        source_ids = set(_sorted_strings(row.get("source_backed_anchor_ids")))
        if not source_ids:
            errors.append(f"{prefix}.source_backed_anchor_ids must be non-empty")
        if source_ids - anchor_ids:
            errors.append(f"{prefix}.source_backed_anchor_ids references unknown anchors")
        row_tail_ids = set(_sorted_strings(row.get("assumption_bound_tail_ids")))
        if not row_tail_ids:
            errors.append(f"{prefix}.assumption_bound_tail_ids must be non-empty")
        if row_tail_ids - tail_ids:
            errors.append(f"{prefix}.assumption_bound_tail_ids references unknown tails")
        for number_field in ("distance_ly", "flight_years"):
            if not _is_number(row.get(number_field)) or float(row.get(number_field)) <= 0.0:
                errors.append(f"{prefix}.{number_field} must be positive finite number")
    if target_ids != {"alpha-centauri-scale", "reference-black-hole", "sgr-a-rounded"}:
        errors.append("line_of_sight target ids must match feasibility targets")

    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
        rollup = {}
    if rollup.get("source_backed_anchor_count") != len(anchors):
        errors.append("rollup.source_backed_anchor_count must equal len(source_backed_anchors)")
    if rollup.get("assumption_bound_tail_count") != len(tails):
        errors.append("rollup.assumption_bound_tail_count must equal len(assumption_bound_tails)")
    if rollup.get("line_of_sight_target_count") != len(rows):
        errors.append("rollup.line_of_sight_target_count must equal len(line_of_sight_rows)")
    if rollup.get("source_backed_anchors_separated_from_assumption_tails") is not True:
        errors.append("rollup.source_backed_anchors_separated_from_assumption_tails must be true")
    for field in (
        "line_of_sight_environment_validated",
        "fixed_mm_cm_dust_truth_claimed",
        "target_region_plasma_validated",
        "whole_path_dust_model_validated",
        "external_validation_completed",
        "certification_go",
        "flight_readiness_go",
    ):
        if rollup.get(field) is not False:
            errors.append(f"rollup.{field} must be false")

    _validate_no_overclaims(payload, ENVIRONMENT_FALSE_FIELDS, errors)
    _validate_blocked_claims(payload, errors)
    if not isinstance(payload.get("external_evidence_gaps"), list) or not payload["external_evidence_gaps"]:
        errors.append("external_evidence_gaps must be non-empty")
    if not isinstance(payload.get("interpretation_limits"), list) or not payload["interpretation_limits"]:
        errors.append("interpretation_limits must be non-empty")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors
