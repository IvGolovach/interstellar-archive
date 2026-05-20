#!/usr/bin/env python3
"""Create a deterministic local review pack for a user-selected mission row."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import render_output
except ImportError:
    from script_io import render_output

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.user_runs.catalog import build_user_run_pack, canonical_json, sha256_hex


DEFAULT_OUTPUT_ROOT = Path("ops/reports/user-mission-runs")


def _load_default_selection(repo_root: Path) -> tuple[str, str, str]:
    catalog = json.loads((repo_root / "artifacts/user_mission_run_catalog.v1.json").read_text(encoding="utf-8"))
    default_run_id = catalog.get("default_run_id")
    for row in catalog.get("run_rows", []):
        if isinstance(row, Mapping) and row.get("run_id") == default_run_id:
            selection = row["selection"]
            return str(selection["target_id"]), str(selection["velocity_id"]), str(row["run_id"])
    raise ValueError("default run row not found in user mission run catalog")


def _summary_hash(result: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json(result["summary"]))


def _verify_deterministic(repo_root: Path, target_id: str, velocity_id: str, run_id: str, mode: str, seed: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
        first = build_user_run_pack(
            repo_root=repo_root,
            target_id=target_id,
            velocity_id=velocity_id,
            run_id=run_id,
            mode=mode,
            seed=seed,
            output_dir=Path(first_dir) / run_id,
        )
        second = build_user_run_pack(
            repo_root=repo_root,
            target_id=target_id,
            velocity_id=velocity_id,
            run_id=run_id,
            mode=mode,
            seed=seed,
            output_dir=Path(second_dir) / run_id,
        )
    first_hash = _summary_hash(first)
    second_hash = _summary_hash(second)
    return {
        "requested": True,
        "first_summary_sha256": first_hash,
        "second_summary_sha256": second_hash,
        "verdict": "PASS" if first_hash == second_hash else "FAIL",
    }


def _render_text(payload: Mapping[str, Any]) -> str:
    lines = [
        "PASS: user mission scenario review pack",
        f"- run_id: {payload['run_id']}",
        f"- output_dir: {payload['output_dir']}",
        f"- target_id: {payload['target_id']}",
        f"- velocity_id: {payload['velocity_id']}",
        f"- summary_sha256: {payload['summary_sha256']}",
        f"- determinism_verdict: {payload['determinism']['verdict']}",
        f"- final_verdict: {payload['verdict']}",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id")
    parser.add_argument("--velocity-id")
    parser.add_argument("--mode", choices=("realistic", "speculative", "dual"), default="dual")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--run-id")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--verify-deterministic", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        default_target, default_velocity, default_run_id = _load_default_selection(REPO_ROOT)
        target_id = args.target_id or default_target
        velocity_id = args.velocity_id or default_velocity
        run_id = args.run_id or default_run_id
        output_root = Path(args.output_root)
        if not output_root.is_absolute():
            output_root = REPO_ROOT / output_root
        output_dir = output_root / run_id
        result = build_user_run_pack(
            repo_root=REPO_ROOT,
            target_id=target_id,
            velocity_id=velocity_id,
            run_id=run_id,
            mode=args.mode,
            seed=int(args.seed),
            output_dir=output_dir,
        )
        summary_hash = _summary_hash(result)
        determinism = (
            _verify_deterministic(REPO_ROOT, target_id, velocity_id, run_id, args.mode, int(args.seed))
            if args.verify_deterministic
            else {"requested": False, "verdict": "SKIPPED"}
        )
        verdict = "PASS" if determinism["verdict"] in {"PASS", "SKIPPED"} else "FAIL"
        payload = {
            "run_id": run_id,
            "target_id": target_id,
            "velocity_id": velocity_id,
            "mode": args.mode,
            "seed": int(args.seed),
            "output_dir": str(output_dir),
            "summary_sha256": summary_hash,
            "determinism": determinism,
            "verdict": verdict,
        }
        rendered = render_output(payload, output_format=args.format, text_renderer=_render_text)
        print(rendered)
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        return 0 if verdict == "PASS" else 2
    except ValueError as exc:
        message = f"FAIL: {exc}"
        print(message)
        if args.output:
            Path(args.output).write_text(message, encoding="utf-8")
        return 2
    except Exception as exc:  # noqa: BLE001
        message = f"INTERNAL ERROR: {exc}"
        print(message)
        if args.output:
            Path(args.output).write_text(message, encoding="utf-8")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
