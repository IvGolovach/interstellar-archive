#!/usr/bin/env python3
"""Build the deterministic Capsule Risk Budget v2 artifact."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, Mapping

try:
    from .script_io import load_json, render_json, write_json
except ImportError:
    from script_io import load_json, render_json, write_json

REPO_ROOT_FALLBACK = Path(__file__).resolve().parents[1]
if str(REPO_ROOT_FALLBACK) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FALLBACK))

from mission.survivability.risk_budget import (
    ATTACK_MODES,
    DEFAULT_ROW_ID,
    DEFAULT_SAMPLE_COUNT,
    FAILURE_MODES,
    MINIMUM_SAMPLE_COUNT,
    QUALIFICATION_ROADMAP,
    SCHEMA_VERSION,
    SOURCE_POLICY,
    SOURCE_ARTIFACT_REF,
    UNCERTAINTY_DIMENSIONS,
    attack_modes_payload,
    build_risk_budget_for_row,
    validate_capsule_risk_budget_artifact,
)


DEFAULT_SOURCE_ARTIFACT = Path(SOURCE_ARTIFACT_REF)
DEFAULT_OUTPUT = Path("artifacts/capsule_risk_budget.v1.json")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_refs(source: Mapping[str, Any]) -> Dict[str, Any]:
    source_index = source.get("source_index", [])
    source_data = source.get("source_data", [])
    return {
        "source_index_count": len(source_index) if isinstance(source_index, list) else 0,
        "source_data_count": len(source_data) if isinstance(source_data, list) else 0,
    }


def build_capsule_risk_budget_artifact(
    *,
    repo_root: Path,
    output_path: Path,
    sample_count: int = DEFAULT_SAMPLE_COUNT,
    seed: int = 20240509,
) -> Dict[str, Any]:
    if isinstance(sample_count, bool) or sample_count < MINIMUM_SAMPLE_COUNT:
        return {
            "status": "FAIL",
            "errors": [f"sample_count must be >= {MINIMUM_SAMPLE_COUNT}"],
            "risk_budget_count": 0,
            "artifact_sha256": None,
            "default_row_id": DEFAULT_ROW_ID,
        }

    source_path = repo_root / DEFAULT_SOURCE_ARTIFACT
    source = load_json(source_path)
    rows = source.get("rows", [])
    if not isinstance(rows, list) or not rows:
        return {
            "status": "FAIL",
            "errors": ["source artifact rows must be non-empty"],
            "risk_budget_count": 0,
            "artifact_sha256": None,
            "default_row_id": DEFAULT_ROW_ID,
        }

    risk_budgets = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        modes_for_row = ATTACK_MODES if row.get("rowId") == DEFAULT_ROW_ID else ATTACK_MODES[:1]
        for attack_mode in modes_for_row:
            risk_budgets.append(
                build_risk_budget_for_row(
                    row=row,
                    attack_mode=attack_mode,
                    sample_count=sample_count,
                    seed=seed,
                )
            )

    risk_budgets.sort(
        key=lambda item: (
            0 if item.get("row_id") == DEFAULT_ROW_ID and item.get("attack_mode_id") == "nominal" else 1,
            str(item.get("row_id")),
            str(item.get("attack_mode_id")),
        )
    )
    attack_modes = attack_modes_payload(DEFAULT_ROW_ID)
    default_mode_budget = {
        str(item["attack_mode_id"]): item
        for item in risk_budgets
        if item.get("row_id") == DEFAULT_ROW_ID
    }
    for mode in attack_modes["modes"]:
        default_budget = default_mode_budget.get(str(mode["id"]), {})
        risk_budget = default_budget.get("risk_budget", {})
        mode["total_capsule_survival"] = float((default_budget.get("quantiles") or {}).get("p50", 0.0))
        mode["media_integrity"] = float(risk_budget.get("data_integrity_probability", 0.0))
        media_integrity = max(float(mode["media_integrity"]), 1.0e-9)
        mode["structure_survival"] = max(0.0, min(1.0, float(mode["total_capsule_survival"]) / media_integrity))
        mode["integrated_hazards"] = {
            str(item.get("mode")): float(item.get("share", 0.0))
            for item in default_budget.get("failure_mode_contributions", [])
            if isinstance(item, Mapping)
        }

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generator": "scripts/build_capsule_risk_budget_artifact.py",
        "public_scope": "artifact_backed_capsule_risk_budget",
        "non_certification_notice": True,
        "source_artifact_ref": SOURCE_ARTIFACT_REF,
        "source_artifact_sha256": _sha256_file(source_path),
        "sample_count": int(sample_count),
        "seed": int(seed),
        "sampling_method": "deterministic_xorshift_monte_carlo_summary",
        "default_row_id": DEFAULT_ROW_ID,
        "risk_budget_count": len(risk_budgets),
        "source_policy": SOURCE_POLICY,
        "failure_modes": FAILURE_MODES,
        "qualification_roadmap": QUALIFICATION_ROADMAP,
        "uncertainty_dimensions": [dict(item) for item in UNCERTAINTY_DIMENSIONS],
        "attack_modes": attack_modes,
        "risk_budgets": risk_budgets,
        "source_summary": _source_refs(source),
        "interpretation_limits": [
            "Reduced-order Monte Carlo summary; not hardware qualification or mission certification.",
            "Driver shares expose assumption sensitivity, not measured failure attribution.",
            "Attack modes are deterministic review postures for claim criticism.",
        ],
    }
    errors = validate_capsule_risk_budget_artifact(payload)
    if errors:
        return {
            "status": "FAIL",
            "errors": errors,
            "risk_budget_count": len(risk_budgets),
            "artifact_sha256": None,
            "default_row_id": DEFAULT_ROW_ID,
        }

    output_abs = repo_root / output_path
    write_json(output_abs, payload)
    return {
        "status": "PASS",
        "errors": [],
        "risk_budget_count": len(risk_budgets),
        "artifact_sha256": _sha256_file(output_abs),
        "default_row_id": DEFAULT_ROW_ID,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT)
    parser.add_argument("--seed", type=int, default=20240509)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_capsule_risk_budget_artifact(
        repo_root=Path(args.repo_root).resolve(),
        output_path=Path(args.output),
        sample_count=args.sample_count,
        seed=args.seed,
    )
    if args.format == "json":
        print(render_json(result))
    else:
        print(f"{result['status']}: capsule risk budget artifact")
        print(f"- risk_budget_count: {result['risk_budget_count']}")
        print(f"- default_row_id: {result['default_row_id']}")
        if result.get("artifact_sha256"):
            print(f"- artifact_sha256: {result['artifact_sha256']}")
        for error in result.get("errors", []):
            print(f"  - {error}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
