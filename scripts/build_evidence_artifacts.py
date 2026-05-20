#!/usr/bin/env python3
"""Build machine-readable and human-readable evidence artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from models.claim_calculations import compute_claim_values
from models.evidence_io import load_assumptions, load_claims, load_sources, value_at_path


ARTIFACTS_DIR = REPO_ROOT / "artifacts"
ARTIFACT_PACK_DIR = ARTIFACTS_DIR / "evidence-pack-v1"
ARTIFACT_SCHEMA_VERSION = "v1"


def _resolve_artifacts_dir(repo_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.9g}"
    return str(value)


def _check_pass(actual: float, minimum: float, maximum: float) -> bool:
    return minimum <= actual <= maximum


def build_claim_values(values: Dict[str, Dict[str, float]]) -> None:
    path = ARTIFACTS_DIR / "claim_values.json"
    path.write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_claims_table(claims: List[Dict[str, Any]], values: Dict[str, Dict[str, float]]) -> int:
    rows: List[Dict[str, Any]] = []
    pass_count = 0
    for claim in claims:
        claim_id = claim["id"]
        claim_values = values[claim_id]
        for check in claim["checks"]:
            actual = float(value_at_path(claim_values, check["path"]))
            minimum = float(check["min"])
            maximum = float(check["max"])
            passed = _check_pass(actual, minimum, maximum)
            if passed:
                pass_count += 1
            rows.append(
                {
                    "claim_id": claim_id,
                    "metric": check["path"],
                    "unit": check["unit"],
                    "actual": _format_value(actual),
                    "expected_min": _format_value(minimum),
                    "expected_max": _format_value(maximum),
                    "pass": str(passed).lower(),
                }
            )

    path = ARTIFACTS_DIR / "claims_table.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "claim_id",
                "metric",
                "unit",
                "actual",
                "expected_min",
                "expected_max",
                "pass",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return pass_count


def build_traceability_matrix(
    claims: List[Dict[str, Any]],
    assumptions: Dict[str, Dict[str, Any]],
    sources: Dict[str, Dict[str, Any]],
) -> None:
    path = ARTIFACTS_DIR / "traceability_matrix.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "claim_id",
                "statement",
                "assumptions",
                "models",
                "artifacts",
                "sources",
                "whitepaper_refs",
            ]
        )
        for claim in claims:
            assumption_titles = [
                f"{assumption_id}:{assumptions[assumption_id]['title']}"
                for assumption_id in claim["assumption_ids"]
            ]
            source_titles = [
                f"{source_id}:{sources[source_id]['title']}" for source_id in claim["source_ids"]
            ]
            writer.writerow(
                [
                    claim["id"],
                    claim["statement"],
                    " | ".join(assumption_titles),
                    f"{claim['model']['module']}.{claim['model']['function']}",
                    " | ".join(claim["artifacts"]),
                    " | ".join(source_titles),
                    " | ".join(claim["whitepaper_refs"]),
                ]
            )


def build_markdown_report(
    claims: List[Dict[str, Any]],
    values: Dict[str, Dict[str, float]],
    pass_count: int,
) -> None:
    total_checks = sum(len(claim["checks"]) for claim in claims)
    lines = [
        "# Evidence Report",
        "",
        "This report is generated from deterministic models and structured claim metadata.",
        "",
        "## Summary",
        "",
        f"- Claims covered: {len(claims)}",
        f"- Numeric checks: {total_checks}",
        f"- Passed checks: {pass_count}",
        f"- Failed checks: {total_checks - pass_count}",
        "",
        "## Claim Snapshot",
        "",
        "| Claim ID | Key Metrics |",
        "| --- | --- |",
    ]

    for claim in claims:
        claim_values = values[claim["id"]]
        metric_pairs = [f"`{k}`={_format_value(v)}" for k, v in claim_values.items()]
        lines.append(f"| {claim['id']} | {'; '.join(metric_pairs)} |")

    lines.extend(
        [
            "",
            "## Rebuild Commands",
            "",
            "```bash",
            "python3 scripts/build_evidence_artifacts.py",
            "python3 scripts/audit_claim_chain.py",
            "python3 -m unittest discover -s tests -p 'test_*.py'",
            "```",
            "",
            "## Traceability",
            "",
            "See `artifacts/traceability_matrix.csv` for claim -> assumption -> model -> artifact -> source linkage.",
            "",
        ]
    )

    (ARTIFACTS_DIR / "claims_report.md").write_text("\n".join(lines), encoding="utf-8")


def compute_output_metrics(claims_count: int, total_checks: int, pass_count: int) -> Dict[str, Any]:
    failed_checks = total_checks - pass_count
    pass_rate = 0.0 if total_checks == 0 else pass_count / total_checks
    return {
        "claims_total": claims_count,
        "checks_total": total_checks,
        "checks_passed": pass_count,
        "checks_failed": failed_checks,
        "checks_pass_rate": pass_rate,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head_sha() -> str:
    return (
        subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True)
        .strip()
    )


def build_artifact_integrity_pack(output_metrics: Dict[str, Any]) -> None:
    ARTIFACT_PACK_DIR.mkdir(parents=True, exist_ok=True)

    input_files = [
        REPO_ROOT / "evidence" / "claims.json",
        REPO_ROOT / "evidence" / "assumptions.json",
        REPO_ROOT / "evidence" / "sources.json",
        REPO_ROOT / "models" / "constants.py",
        REPO_ROOT / "models" / "core_physics.py",
        REPO_ROOT / "models" / "claim_calculations.py",
    ]
    output_metrics_path = ARTIFACT_PACK_DIR / "output_metrics.json"
    output_metrics_path.write_text(
        json.dumps(output_metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    output_files = [
        ARTIFACTS_DIR / "claim_values.json",
        ARTIFACTS_DIR / "claims_table.csv",
        ARTIFACTS_DIR / "traceability_matrix.csv",
        ARTIFACTS_DIR / "claims_report.md",
        output_metrics_path,
    ]

    input_manifest = {
        "artifact_id": "evidence-pack-v1",
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "golden_run": {
            "scenario_id": "golden-run-v1",
            "deterministic": True,
            "entrypoint": "python3 scripts/run_golden.py",
        },
        "input_files": [
            {"path": str(path.relative_to(REPO_ROOT)), "sha256": _sha256(path)} for path in input_files
        ],
    }
    (ARTIFACT_PACK_DIR / "input_parameters.json").write_text(
        json.dumps(input_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    checksums_path = ARTIFACT_PACK_DIR / "checksums.sha256"
    checksums_lines = [
        f"{_sha256(path)}  {path.relative_to(REPO_ROOT)}" for path in sorted(output_files)
    ]
    checksums_path.write_text("\n".join(checksums_lines) + "\n", encoding="utf-8")

    commit_sha = _git_head_sha()
    timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    metadata = {
        "artifact_id": "evidence-pack-v1",
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "commit_sha": commit_sha,
        "timestamp_utc": timestamp_utc,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "generated_at_utc": timestamp_utc,
        "generation_commit_sha": commit_sha,
        "generator_script": "scripts/build_evidence_artifacts.py",
        "input_parameters_file": str((ARTIFACT_PACK_DIR / "input_parameters.json").relative_to(REPO_ROOT)),
        "output_metrics_file": str(output_metrics_path.relative_to(REPO_ROOT)),
        "checksums_file": str(checksums_path.relative_to(REPO_ROOT)),
        "outputs": [str(path.relative_to(REPO_ROOT)) for path in output_files],
    }
    (ARTIFACT_PACK_DIR / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    global REPO_ROOT, ARTIFACTS_DIR, ARTIFACT_PACK_DIR  # noqa: PLW0603

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root path")
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts",
        help="Artifacts output directory (absolute or repo-relative)",
    )
    args = parser.parse_args()
    REPO_ROOT = Path(args.repo_root).resolve()
    ARTIFACTS_DIR = _resolve_artifacts_dir(REPO_ROOT, args.artifacts_dir)
    ARTIFACT_PACK_DIR = ARTIFACTS_DIR / "evidence-pack-v1"

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    claim_registry = load_claims()
    claims = claim_registry["claims"]
    assumptions = load_assumptions()
    sources = load_sources()
    values = compute_claim_values()

    build_claim_values(values)
    pass_count = build_claims_table(claims=claims, values=values)
    build_traceability_matrix(claims=claims, assumptions=assumptions, sources=sources)
    build_markdown_report(claims=claims, values=values, pass_count=pass_count)

    total_checks = sum(len(claim["checks"]) for claim in claims)
    output_metrics = compute_output_metrics(
        claims_count=len(claims),
        total_checks=total_checks,
        pass_count=pass_count,
    )
    build_artifact_integrity_pack(output_metrics=output_metrics)
    print(
        f"Built artifacts in {ARTIFACTS_DIR} | claims={len(claims)} checks={total_checks} passed={pass_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
