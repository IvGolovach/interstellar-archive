#!/usr/bin/env python3
"""Run mission DAG v1 and emit deterministic proof artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_output, write_json, write_text
except ImportError:
    from script_io import load_json, render_output, write_json, write_text
from typing import Any, Dict, Iterable, List, Mapping

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.dag.runner_v1 import RunnerConfig, execute


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3


def _default_run_id(repo_root: Path) -> str:
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short_sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    return f"{ts}-{short_sha}-mission-dag-v1"


def _parse_force_failures(values: Iterable[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in values:
        if ":" not in raw:
            raise ValueError(f"--force-failure must be node_id:FAILURE_ID, got '{raw}'")
        node_id, failure_id = raw.split(":", 1)
        node_id = node_id.strip()
        failure_id = failure_id.strip()
        if not node_id or not failure_id:
            raise ValueError(f"--force-failure must be node_id:FAILURE_ID, got '{raw}'")
        out[node_id] = failure_id
    return out


def _read_git_status(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


def _read_git_branch(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


def _read_head_sha(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


def _render_determinism_markdown(result: Mapping[str, Any]) -> str:
    det = result["determinism"]
    primary_hash = result["primary"]["manifest"]["manifest_hash"]
    return "\n".join(
        [
            "# Determinism Proof",
            "",
            f"- requested: `{det['requested']}`",
            f"- primary_manifest_hash: `{primary_hash}`",
            f"- same_seed_manifest_hash: `{det.get('same_seed_manifest_hash')}`",
            f"- same_seed_match: `{det.get('same_seed_match')}`",
            f"- different_seed_manifest_hash: `{det.get('different_seed_manifest_hash')}`",
            f"- different_seed_differs: `{det.get('different_seed_differs')}`",
            f"- verdict: `{det['verdict']}`",
        ]
    )


def _render_run_notes(
    *,
    repo_root: Path,
    result: Mapping[str, Any],
    module_registry_path: Path,
) -> str:
    registry = load_json(module_registry_path)
    claims = load_json(repo_root / "parameters/registry/parameter_claims.v1.json")
    claim_by_id = {
        str(item["parameter_id"]): item
        for item in claims.get("claims", [])
        if isinstance(item, Mapping) and isinstance(item.get("parameter_id"), str)
    }

    modules = [
        item for item in registry.get("modules", []) if isinstance(item, Mapping)
    ]

    module_rows: List[str] = []
    for item in modules:
        module_rows.append(
            "| {module_id} | {module_type} | {entry} |".format(
                module_id=item["module_id"],
                module_type=item["module_type"],
                entry=item["implemented_by"]["python_entrypoint"],
            )
        )

    used_driver_ids = set()
    for mode_payload in result["primary"]["mode_summaries"].values():
        for param_id in mode_payload.get("speculative_parameters_used", []):
            used_driver_ids.add(str(param_id))

    module_files = []
    for rel_path in result["primary"]["module_artifacts"]:
        artifact = load_json(Path(result["output_dir"]) / rel_path)
        drivers = artifact["failure"].get("dominant_driver_parameter_ids", [])
        for item in drivers:
            used_driver_ids.add(str(item))
        module_files.append(artifact)

    weak_assumptions: List[str] = []
    for param_id in sorted(used_driver_ids):
        claim = claim_by_id.get(param_id)
        if not claim:
            continue
        trust = str(claim.get("trust_grade", "D"))
        if trust in {"C", "D"}:
            weak_assumptions.append(
                f"- `{param_id}` trust={trust} justification: {claim.get('justification', '').strip()}"
            )

    weak_assumptions = weak_assumptions[:10]
    if not weak_assumptions:
        weak_assumptions = ["- No low-trust dominant-driver assumptions detected in this run."]

    dominant_rows: List[str] = []
    counter: Dict[str, int] = {}
    for artifact in module_files:
        for pid in artifact["failure"].get("dominant_driver_parameter_ids", []):
            key = str(pid)
            counter[key] = counter.get(key, 0) + 1
    for pid, count in sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))[:8]:
        dominant_rows.append(f"- `{pid}` referenced by {count} module failure annotations")
    if not dominant_rows:
        dominant_rows.append("- No dominant drivers flagged (all module statuses PASS).")

    return "\n".join(
        [
            "# Mission DAG Notes",
            "",
            "## 1. Module boundaries and wrappers",
            "Mission DAG v1 sets boundaries at module contracts. All six module types are wrappers over existing deterministic mission baseline calculations in `scripts/mission_baseline_check.py` and derived proxies in `mission/dag/runner_v1.py`.",
            "",
            "## 2. Modules and IO contracts",
            "| Module ID | Module Type | Implemented by |",
            "|---|---|---|",
            *module_rows,
            "",
            "## 3. Weakest assumptions by trust grade",
            *weak_assumptions,
            "",
            "## 4. Dominant drivers (run-local)",
            *dominant_rows,
            "",
            "## 5. Follow-up implementation work",
            "Current outputs already support artifact-driven drilldown UI work: per-module outputs, failure taxonomy IDs, dominant-driver parameter IDs, manifest/hashchain state, and mode-separated summaries.",
            "",
            "Before adding user override workflows, the repository still needs an explicit override policy schema, per-override provenance fields, and override-level guardrail taxonomy with CI rejection rules.",
        ]
    )


def _render_precheck(repo_root: Path, run_id: str) -> str:
    return "\n".join(
        [
            "# PRECHECK",
            "",
            f"- run_id: `{run_id}`",
            f"- head_sha: `{_read_head_sha(repo_root)}`",
            f"- branch: `{_read_git_branch(repo_root)}`",
            f"- worktree_status: `{_read_git_status(repo_root) or 'clean'}`",
            f"- generated_at_utc: `{datetime.now(tz=timezone.utc).isoformat()}`",
        ]
    )


def _render_text(payload: Mapping[str, Any]) -> str:
    primary = payload["primary"]
    determinism = payload["determinism"]
    return "\n".join(
        [
            "PASS: mission DAG run",
            f"- run_id: {payload['run_id']}",
            f"- output_dir: {payload['output_dir']}",
            f"- mode: {primary['mode']}",
            f"- execution_modes: {','.join(primary['execution_modes'])}",
            f"- manifest_hash: {primary['manifest']['manifest_hash']}",
            f"- module_artifact_count: {primary['manifest']['module_artifact_count']}",
            f"- hashchain_status: {primary['hashchain_proof']['status']}",
            f"- taxonomy_status: {primary['failure_taxonomy_coverage']['status']}",
            f"- determinism_verdict: {determinism['verdict']}",
            f"- final_verdict: {payload['meta']['verdict']}",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="mission/dag/scenarios/mission_dag_baseline.v1.json")
    parser.add_argument("--mission-scenario", default="mission/BASELINE_SCENARIO_v1.json")
    parser.add_argument("--mode", choices=("realistic", "speculative", "dual"), default="dual")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--run-id")
    parser.add_argument("--output-root", default="ops/reports/mission-dag-v1")
    parser.add_argument("--verify-deterministic", action="store_true")
    parser.add_argument("--force-failure", action="append", default=[])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        forced_failures = _parse_force_failures(args.force_failure)
        run_id = args.run_id or _default_run_id(REPO_ROOT)
        output_dir = (REPO_ROOT / args.output_root / run_id).resolve()

        config = RunnerConfig(
            repo_root=REPO_ROOT,
            dag_scenario_path=(REPO_ROOT / args.scenario).resolve(),
            mission_scenario_path=(REPO_ROOT / args.mission_scenario).resolve(),
            mode=args.mode,
            seed=int(args.seed),
            output_dir=output_dir,
            verify_deterministic=bool(args.verify_deterministic),
            forced_failures=forced_failures,
        )

        result = execute(config)

        summary = {
            "run_id": run_id,
            "status": result["status"],
            "mode": args.mode,
            "seed": int(args.seed),
            "execution_modes": result["primary"]["execution_modes"],
            "mode_summaries": result["primary"]["mode_summaries"],
            "domain_guard": result["domain_guard"],
            "optimization_guard": result["optimization_guard"],
            "manifest_hash": result["primary"]["manifest"]["manifest_hash"],
            "module_artifact_count": result["primary"]["manifest"]["module_artifact_count"],
        }

        write_json(output_dir / "DAG_RUN_SUMMARY.json", summary)
        write_json(output_dir / "MODULE_ARTIFACT_MANIFEST.json", result["primary"]["manifest"])
        write_json(output_dir / "HASHCHAIN_PROOF.json", result["primary"]["hashchain_proof"])
        write_json(output_dir / "FAILURE_TAXONOMY_COVERAGE.json", result["primary"]["failure_taxonomy_coverage"])
        write_text(output_dir / "DETERMINISM_PROOF.md", _render_determinism_markdown(result))

        write_text(output_dir / "PRECHECK.md", _render_precheck(REPO_ROOT, run_id))

        log_lines = [
            f"run_id={run_id}",
            f"mode={args.mode}",
            f"seed={int(args.seed)}",
            f"scenario={args.scenario}",
            f"mission_scenario={args.mission_scenario}",
            f"verify_deterministic={bool(args.verify_deterministic)}",
            f"forced_failures={json.dumps(forced_failures, sort_keys=True)}",
        ]
        write_text(output_dir / "COMMAND_OUTPUTS.log", "\n".join(log_lines))

        notes = _render_run_notes(
            repo_root=REPO_ROOT,
            result={**result, "output_dir": str(output_dir)},
            module_registry_path=REPO_ROOT / "mission/dag/registry/module_registry.v1.json",
        )
        write_text(output_dir / "MISSION_DAG_NOTES.md", notes)

        meta = {
            "run_id": run_id,
            "head_sha": _read_head_sha(REPO_ROOT),
            "mode": args.mode,
            "seed": int(args.seed),
            "manifest_hash": result["primary"]["manifest"]["manifest_hash"],
            "domain_guard_pass": result["domain_guard"]["status"] == "PASS",
            "optimization_guard_pass": result["optimization_guard"]["status"] == "PASS",
            "determinism_verdict": result["determinism"]["verdict"],
            "verdict": "PASS" if result["status"] == "PASS" else "FAIL",
        }
        write_json(output_dir / "meta.json", meta)

        payload = {
            "run_id": run_id,
            "output_dir": str(output_dir),
            "primary": result["primary"],
            "determinism": result["determinism"],
            "meta": meta,
        }

        rendered = render_output(payload, output_format=args.format, text_renderer=_render_text)
        print(rendered)

        if args.output:
            write_text(Path(args.output), rendered)

        return EXIT_PASS if meta["verdict"] == "PASS" else EXIT_VIOLATION
    except ValueError as exc:
        message = f"FAIL: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_VIOLATION
    except Exception as exc:  # noqa: BLE001
        message = f"INTERNAL ERROR: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
