#!/usr/bin/env python3
"""Build deterministic module-level parameter dynamic trace index from mission DAG artifacts."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_json, write_json
except ImportError:
    from script_io import load_json, render_json, write_json
from typing import Any, Dict, List, Mapping

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.dag import hashchain


def _git_head(repo_root: Path) -> str:
    return (
        subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            env={**os.environ, "LANG": "C", "LC_ALL": "C"},
            text=True,
        )
        .strip()
    )


def _parse_command_outputs(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    out: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def build_index(*, repo_root: Path, run_dir: Path) -> Dict[str, Any]:
    summary_path = run_dir / "DAG_RUN_SUMMARY.json"
    hashchain_path = run_dir / "hashchain.jsonl"
    command_outputs_path = run_dir / "COMMAND_OUTPUTS.log"
    meta_path = run_dir / "meta.json"

    summary = load_json(summary_path)
    entries = hashchain.read_jsonl(hashchain_path)
    hashchain_ok, _ = hashchain.verify_chain(entries)
    command_values = _parse_command_outputs(command_outputs_path)

    commit_sha = _git_head(repo_root)
    if meta_path.exists():
        meta = load_json(meta_path)
        candidate = meta.get("head_sha")
        if isinstance(candidate, str) and candidate:
            commit_sha = candidate

    events: List[Dict[str, Any]] = []
    modules_root = run_dir / "modules"
    for module_file in sorted(modules_root.rglob("*.json")):
        payload = load_json(module_file)
        mode = module_file.parent.name
        failure = payload.get("failure", {}) if isinstance(payload.get("failure"), Mapping) else {}
        drivers_raw = failure.get("dominant_driver_parameter_ids")
        drivers = sorted(str(item) for item in drivers_raw) if isinstance(drivers_raw, list) else []
        events.append(
            {
                "mode": str(payload.get("mode", mode)),
                "node_id": module_file.stem,
                "module_id": str(payload.get("module_id", "")),
                "inputs_hash": str(payload.get("inputs_hash", "")),
                "outputs_hash": str(payload.get("outputs_hash", "")),
                "failure_mode": failure.get("failure_mode"),
                "dominant_driver_parameter_ids": drivers,
            }
        )

    events.sort(key=lambda item: (item["mode"], item["node_id"], item["module_id"]))

    run_id = str(summary.get("run_id") or run_dir.name)
    index = {
        "run_id": run_id,
        "commit_sha": commit_sha,
        "mode": str(summary.get("mode", command_values.get("mode", "dual"))),
        "seed": int(summary.get("seed", command_values.get("seed", 0))),
        "scenario_path": command_values.get("scenario", "mission/dag/scenarios/mission_dag_baseline.v1.json"),
        "artifact_hash": str(summary.get("manifest_hash", "")),
        "hashchain_verified": bool(hashchain_ok),
        "events": events,
    }
    return index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    run_dir = Path(args.run_dir).resolve()
    output_path = Path(args.output).resolve()

    payload = build_index(repo_root=repo_root, run_dir=run_dir)
    write_json(output_path, payload)

    if args.format == "json":
        print(render_json(payload))
    else:
        print("PASS: parameter dynamic trace index built")
        print(f"- run_id: {payload['run_id']}")
        print(f"- mode: {payload['mode']}")
        print(f"- seed: {payload['seed']}")
        print(f"- hashchain_verified: {payload['hashchain_verified']}")
        print(f"- events: {len(payload['events'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
