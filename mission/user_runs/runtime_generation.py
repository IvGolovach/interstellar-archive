"""Runtime scenario generation contract for user-owned mission runs.

This module turns the selected-run catalog into a reviewable generation
contract. It describes how a user-owned local run pack is produced without
claiming remote execution, a persistent reviewed archive, or mission readiness.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

from mission.user_runs.catalog import (
    DEFAULT_OUTPUT_ROOT,
    SOURCE_BASELINE_SCENARIO,
    SOURCE_CATALOG_SPEC,
    SOURCE_DAG_SCENARIO,
    SOURCE_MISSION_SCHEMA,
    SOURCE_PACK_VALIDATOR,
    SOURCE_RUNNER,
    SUMMARY_SCHEMA_VERSION,
    canonical_json,
    validate_user_mission_run_catalog,
)


SCHEMA_VERSION = "runtime_scenario_generation.v1"
GENERATOR = "scripts/build_runtime_scenario_generation_artifact.py"
PUBLIC_SCOPE = "runtime_scenario_generation_user_owned_runs"
SOURCE_CATALOG = "artifacts/user_mission_run_catalog.v1.json"
SUPPORTED_MODES = ["realistic", "speculative", "dual"]
OUTPUT_FILES = [
    "COMPILED_MISSION_SCENARIO.json",
    "USER_RUN_SUMMARY.json",
    "DAG_RUN_SUMMARY.json",
    "SOURCE_MANIFEST.json",
    "RUN_REPORT.md",
    "meta.json",
]
BLOCKED_CLAIMS = [
    "remote execution isolation completed",
    "persistent reviewed run archive",
    "mission feasible",
    "flight ready",
    "certified local run pack",
    "guaranteed arrival or archive recovery",
]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _row_command(row: Mapping[str, Any]) -> str:
    args = row["runtime_pack_template"]["args"]
    ordered = [
        "--target-id",
        str(args["--target-id"]),
        "--velocity-id",
        str(args["--velocity-id"]),
        "--mode",
        str(args["--mode"]),
        "--seed",
        str(args["--seed"]),
        "--run-id",
        str(args["--run-id"]),
        "--verify-deterministic",
    ]
    return " ".join(["python3", SOURCE_RUNNER, *ordered])


def _target_options(rows: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        selection = row["selection"]
        target_id = str(selection["target_id"])
        by_id[target_id] = {
            "target_id": target_id,
            "target_label": selection["target_label"],
            "target_detail": selection["target_detail"],
            "distance_ly": selection["distance_ly"],
        }
    return [by_id[target_id] for target_id in sorted(by_id)]


def _velocity_options(rows: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        selection = row["selection"]
        velocity_id = str(selection["velocity_id"])
        by_id[velocity_id] = {
            "velocity_id": velocity_id,
            "velocity_label": selection["velocity_label"],
            "velocity_detail": selection["velocity_detail"],
            "velocity_km_s": selection["velocity_km_s"],
            "velocity_fraction_c": selection["velocity_fraction_c"],
        }
    return [by_id[velocity_id] for velocity_id in sorted(by_id)]


def _generation_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    selection = row["selection"]
    exposure = row.get("exposure_snapshot", {})
    dust_screen = exposure.get("dust_screen", {}) if isinstance(exposure, Mapping) else {}
    if not isinstance(dust_screen, Mapping):
        dust_screen = {}
    return {
        "run_id": row["run_id"],
        "selection_hash": row["selection_hash"],
        "target_id": selection["target_id"],
        "target_label": selection["target_label"],
        "velocity_id": selection["velocity_id"],
        "velocity_label": selection["velocity_label"],
        "flight_years": selection["flight_years"],
        "time_horizon_class": selection["time_horizon_class"],
        "command_preview": _row_command(row),
        "cli_args": dict(row["runtime_pack_template"]["args"]),
        "compiled_scenario_delta": {
            "mission_mode_policy": "realistic for realistic or dual, speculative for speculative",
            "seed_policy": "user-mission-run:{run_id}:{seed}",
            "bh_parameters.distance_from_earth_ly": selection["distance_ly"],
            "environment_model.dust_flux_scale": dust_screen.get("dust_flux_scale"),
            "velocity_runtime_policy": "selection metadata only in v1; velocity shapes catalog flight-time and risk rows, not a new MISSION_SCHEMA_v1 runtime field",
        },
        "run_pack_contract": {
            "output_root": DEFAULT_OUTPUT_ROOT,
            "summary_schema_version": SUMMARY_SCHEMA_VERSION,
            "output_files": list(OUTPUT_FILES),
            "validation_function": "mission.user_runs.catalog.validate_user_run_summary",
            "determinism_flag": "--verify-deterministic",
            "writes_tracked_files": False,
        },
        "ownership_boundary": {
            "user_owned": True,
            "remote_execution": False,
            "persistent_reviewed_archive": False,
            "tracked_by_default": False,
        },
        "external_evidence_gaps": list(row.get("external_evidence_gaps", [])),
        "blocked_claims": list(dict.fromkeys([*row.get("blocked_claims", []), *BLOCKED_CLAIMS])),
    }


def build_runtime_scenario_generation(repo_root: Path) -> Dict[str, Any]:
    catalog = _load_json(repo_root / SOURCE_CATALOG)
    errors = validate_user_mission_run_catalog(catalog)
    if errors:
        raise ValueError("user mission run catalog invalid: " + "; ".join(errors))
    rows = [row for row in catalog.get("run_rows", []) if isinstance(row, Mapping)]
    rows.sort(key=lambda row: str(row["run_id"]))
    generation_rows = [_generation_row(row) for row in rows]
    source_paths = [
        SOURCE_CATALOG,
        SOURCE_RUNNER,
        SOURCE_PACK_VALIDATOR,
        SOURCE_DAG_SCENARIO,
        SOURCE_BASELINE_SCENARIO,
        SOURCE_MISSION_SCHEMA,
        SOURCE_CATALOG_SPEC,
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "public_scope": PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": [{"path": path, "sha256": _sha256_file(repo_root / path)} for path in source_paths],
        "selection_axes": {
            "target_count": catalog.get("target_count"),
            "velocity_count": catalog.get("velocity_count"),
            "target_options": _target_options(rows),
            "velocity_options": _velocity_options(rows),
            "supported_modes": list(SUPPORTED_MODES),
            "default_seed": 1,
            "default_run_id": catalog.get("default_run_id"),
        },
        "scenario_generation_contract": {
            "source_catalog": SOURCE_CATALOG,
            "runner": SOURCE_RUNNER,
            "allowed_user_inputs": ["target_id", "velocity_id", "mode", "seed", "run_id"],
            "scenario_compiler": "mission.user_runs.catalog.compile_selected_mission_scenario",
            "forbidden_runtime_claims": list(BLOCKED_CLAIMS),
            "browser_execution_policy": "browser may render and prepare run-pack metadata, but does not execute mission physics or write tracked files",
        },
        "run_pack_contract": {
            "output_root": DEFAULT_OUTPUT_ROOT,
            "tracked_by_default": False,
            "writes_tracked_files": False,
            "summary_schema_version": SUMMARY_SCHEMA_VERSION,
            "output_files": list(OUTPUT_FILES),
            "required_summary_fields": [
                "selection_hash",
                "compiled_mission_scenario_sha256",
                "dag_execution.manifest_hash",
                "dag_execution.hashchain_status",
                "source_manifest",
                "verdict",
            ],
        },
        "generation_row_count": len(generation_rows),
        "generation_rows": generation_rows,
        "rollup": {
            "rows_with_command_preview": sum(1 for row in generation_rows if row.get("command_preview")),
            "rows_writing_tracked_files": sum(
                1 for row in generation_rows if row["run_pack_contract"].get("writes_tracked_files") is not False
            ),
            "remote_execution_claimed": False,
            "persistent_reviewed_archive_claimed": False,
            "determinism_flag_required": True,
        },
        "blocked_claims": list(BLOCKED_CLAIMS),
        "interpretation_limits": [
            "Runtime scenario generation is a local review-pack contract, not a hosted execution service.",
            "Generated packs are user-owned artifacts under ops/reports or exported JSON, not repository truth by default.",
            "The browser may display command previews and pack contracts, but it must not recompute mission physics.",
        ],
        "determinism_signature": hashlib.sha256(
            canonical_json(
                {
                    "schema_version": SCHEMA_VERSION,
                    "rows": [
                        {
                            "run_id": row["run_id"],
                            "selection_hash": row["selection_hash"],
                            "command_preview": row["command_preview"],
                        }
                        for row in generation_rows
                    ],
                    "output_files": OUTPUT_FILES,
                }
            ).encode("utf-8")
        ).hexdigest(),
    }


def validate_runtime_scenario_generation(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if payload.get("generator") != GENERATOR:
        errors.append(f"generator must be {GENERATOR}")
    if payload.get("public_scope") != PUBLIC_SCOPE:
        errors.append(f"public_scope must be {PUBLIC_SCOPE}")
    if payload.get("non_certification_notice") is not True:
        errors.append("non_certification_notice must be true")
    source_artifacts = payload.get("source_artifacts")
    if not isinstance(source_artifacts, list) or len(source_artifacts) != 7:
        errors.append("source_artifacts must include catalog, runner, pack validator, DAG scenario, baseline, schema, and spec")
    axes = payload.get("selection_axes")
    if not isinstance(axes, Mapping):
        errors.append("selection_axes must be object")
        axes = {}
    if axes.get("target_count") != 3 or axes.get("velocity_count") != 5:
        errors.append("selection_axes target/velocity counts must be 3 x 5")
    if axes.get("supported_modes") != SUPPORTED_MODES:
        errors.append("selection_axes.supported_modes must be realistic/speculative/dual")
    contract = payload.get("scenario_generation_contract")
    if not isinstance(contract, Mapping):
        errors.append("scenario_generation_contract must be object")
        contract = {}
    if contract.get("runner") != SOURCE_RUNNER:
        errors.append("scenario_generation_contract.runner mismatch")
    if "browser" not in str(contract.get("browser_execution_policy", "")).lower():
        errors.append("scenario_generation_contract.browser_execution_policy must be explicit")
    pack = payload.get("run_pack_contract")
    if not isinstance(pack, Mapping):
        errors.append("run_pack_contract must be object")
        pack = {}
    if pack.get("tracked_by_default") is not False or pack.get("writes_tracked_files") is not False:
        errors.append("run_pack_contract must not write tracked files by default")
    if pack.get("output_files") != OUTPUT_FILES:
        errors.append("run_pack_contract.output_files mismatch")
    rows = payload.get("generation_rows")
    if not isinstance(rows, list) or len(rows) != 15:
        errors.append("generation_rows must contain exactly 15 rows")
        rows = []
    if payload.get("generation_row_count") != len(rows):
        errors.append("generation_row_count must equal len(generation_rows)")
    default_seen = False
    run_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"generation_rows[{index}] must be object")
            continue
        prefix = f"generation_rows[{index}]"
        run_id = row.get("run_id")
        if not isinstance(run_id, str) or not run_id.startswith("umr-"):
            errors.append(f"{prefix}.run_id must be stable umr-* string")
        elif run_id in run_ids:
            errors.append(f"{prefix}.run_id duplicated")
        else:
            run_ids.add(run_id)
        if row.get("target_id") == "reference-black-hole" and row.get("velocity_id") == "conditional-45":
            default_seen = row.get("run_id") == axes.get("default_run_id")
        if not isinstance(row.get("selection_hash"), str) or len(str(row.get("selection_hash"))) != 64:
            errors.append(f"{prefix}.selection_hash must be sha256")
        command = row.get("command_preview")
        if not isinstance(command, str) or not command.startswith(f"python3 {SOURCE_RUNNER} "):
            errors.append(f"{prefix}.command_preview must call {SOURCE_RUNNER}")
        elif "--verify-deterministic" not in command:
            errors.append(f"{prefix}.command_preview must include --verify-deterministic")
        row_pack = row.get("run_pack_contract")
        if not isinstance(row_pack, Mapping):
            errors.append(f"{prefix}.run_pack_contract must be object")
            row_pack = {}
        if row_pack.get("output_files") != OUTPUT_FILES:
            errors.append(f"{prefix}.run_pack_contract.output_files mismatch")
        if row_pack.get("writes_tracked_files") is not False:
            errors.append(f"{prefix}.run_pack_contract.writes_tracked_files must be false")
        ownership = row.get("ownership_boundary")
        if not isinstance(ownership, Mapping):
            errors.append(f"{prefix}.ownership_boundary must be object")
        else:
            for field in ("remote_execution", "persistent_reviewed_archive", "tracked_by_default"):
                if ownership.get(field) is not False:
                    errors.append(f"{prefix}.ownership_boundary.{field} must be false")
        blocked = row.get("blocked_claims")
        if not isinstance(blocked, list) or "flight ready" not in blocked or "persistent reviewed run archive" not in blocked:
            errors.append(f"{prefix}.blocked_claims must include flight ready and persistent archive boundaries")
        if not isinstance(row.get("external_evidence_gaps"), list) or not row["external_evidence_gaps"]:
            errors.append(f"{prefix}.external_evidence_gaps must be non-empty")
    if not default_seen:
        errors.append("selection_axes.default_run_id must reference reference-black-hole conditional-45")
    rollup = payload.get("rollup")
    if not isinstance(rollup, Mapping):
        errors.append("rollup must be object")
    else:
        if rollup.get("rows_with_command_preview") != 15:
            errors.append("rollup.rows_with_command_preview must be 15")
        if rollup.get("rows_writing_tracked_files") != 0:
            errors.append("rollup.rows_writing_tracked_files must be 0")
        if rollup.get("remote_execution_claimed") is not False:
            errors.append("rollup.remote_execution_claimed must be false")
        if rollup.get("persistent_reviewed_archive_claimed") is not False:
            errors.append("rollup.persistent_reviewed_archive_claimed must be false")
    blocked_claims = payload.get("blocked_claims")
    if not isinstance(blocked_claims, list) or not set(BLOCKED_CLAIMS).issubset(set(blocked_claims)):
        errors.append("blocked_claims must include all runtime overclaim boundaries")
    if not isinstance(payload.get("determinism_signature"), str) or len(str(payload.get("determinism_signature"))) != 64:
        errors.append("determinism_signature must be sha256")
    return errors
