#!/usr/bin/env python3
"""Generate deterministic OAT sensitivity ranking for mission baseline p_success."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_output, write_json, write_text
except ImportError:
    from script_io import load_json, render_output, write_json, write_text
import sys
from typing import Any, Dict, List, Mapping, Tuple

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from mission.baseline import build_output, load_claims_map


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_BASELINE = Path("mission/BASELINE_SCENARIO_v1.json")
DEFAULT_SCHEMA = Path("mission/MISSION_SCHEMA_v1.json")
DEFAULT_PARAMETER_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_PARAMETER_CLAIMS = Path("parameters/registry/parameter_claims.v1.json")
DEFAULT_OUTPUT_DIR = Path("ops/reports/parameter-audit-latest")


def _set_path(payload: Dict[str, Any], path: str, value: float) -> None:
    cursor: Any = payload
    parts = path.split(".")
    for key in parts[:-1]:
        cursor = cursor[key]
    cursor[parts[-1]] = value


def _get_path(payload: Mapping[str, Any], path: str) -> float:
    cursor: Any = payload
    for key in path.split("."):
        cursor = cursor[key]
    if isinstance(cursor, bool) or not isinstance(cursor, (int, float)):
        raise TypeError(f"{path} is not numeric")
    return float(cursor)


def _collect_numeric_paths(scenario: Mapping[str, Any]) -> List[str]:
    sections = [
        "success_threshold",
        "bh_parameters",
        "trajectory_model",
        "correction_window",
        "capsule_model",
        "environment_model",
    ]
    out: List[str] = []
    for section in sections:
        if section == "success_threshold":
            out.append("success_threshold")
            continue
        value = scenario.get(section)
        if not isinstance(value, dict):
            continue
        for key, nested in value.items():
            if isinstance(nested, bool) or isinstance(nested, str):
                continue
            if isinstance(nested, (int, float)):
                out.append(f"{section}.{key}")
    out.sort()
    return out


def _schema_bounds(schema: Mapping[str, Any]) -> Dict[str, Tuple[float, float]]:
    out: Dict[str, Tuple[float, float]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            pid = node.get("parameter_id") if isinstance(node.get("parameter_id"), str) else None
            if pid and isinstance(node.get("minimum"), (int, float)) and isinstance(node.get("maximum"), (int, float)):
                out[pid] = (float(node["minimum"]), float(node["maximum"]))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)
    return out


def _trust_by_parameter(parameter_claims: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for claim in parameter_claims.get("claims", []):
        if isinstance(claim, dict) and isinstance(claim.get("parameter_id"), str):
            out[str(claim["parameter_id"])] = str(claim.get("trust_grade", ""))
    return out


def _build_output(
    scenario: Dict[str, Any],
    mode: str,
    claims_map: Mapping[str, Dict[str, Any]],
) -> Dict[str, Any]:
    return build_output(scenario, mode=mode, claims_map=claims_map)


def _score_parameter(
    scenario: Dict[str, Any],
    path: str,
    bounds_by_path: Mapping[str, Tuple[float, float]],
    mode: str,
    claims_map: Mapping[str, Dict[str, Any]],
) -> Dict[str, Any]:
    base_value = _get_path(scenario, path)
    base_output = _build_output(scenario, mode=mode, claims_map=claims_map)
    base_p = float(base_output["p_success"])

    low_bound, high_bound = bounds_by_path.get(path, (base_value, base_value))
    span = max(0.0, high_bound - low_bound)

    delta = abs(base_value) * 0.05
    if delta == 0.0 and span > 0.0:
        delta = span * 0.01
    if delta == 0.0:
        delta = 1e-6

    plus_value = min(high_bound, base_value + delta)
    minus_value = max(low_bound, base_value - delta)

    if plus_value == minus_value:
        return {
            "parameter_id": path,
            "base_value": base_value,
            "plus_value": plus_value,
            "minus_value": minus_value,
            "p_success_plus": base_p,
            "p_success_minus": base_p,
            "raw_delta_p_success": 0.0,
            "influence_score": 0.0,
        }

    plus = copy.deepcopy(scenario)
    minus = copy.deepcopy(scenario)
    _set_path(plus, path, plus_value)
    _set_path(minus, path, minus_value)

    p_plus = float(_build_output(plus, mode=mode, claims_map=claims_map)["p_success"])
    p_minus = float(_build_output(minus, mode=mode, claims_map=claims_map)["p_success"])

    raw_delta = abs(p_plus - p_minus)
    step = abs(plus_value - minus_value) / 2.0
    base_scale = abs(base_value) if abs(base_value) > 1e-12 else 1.0
    normalized_step = step / base_scale if step > 0 else 0.0
    influence = 0.0 if normalized_step == 0 else (raw_delta / 2.0) / normalized_step

    return {
        "parameter_id": path,
        "base_value": base_value,
        "plus_value": plus_value,
        "minus_value": minus_value,
        "p_success_plus": p_plus,
        "p_success_minus": p_minus,
        "raw_delta_p_success": round(raw_delta, 12),
        "influence_score": round(influence, 12),
    }


def run(
    scenario_path: Path,
    schema_path: Path,
    parameter_registry_path: Path,
    parameter_claims_path: Path,
    mode: str,
    output_dir: Path,
) -> Dict[str, Any]:
    scenario = load_json(scenario_path)
    schema = load_json(schema_path)
    parameter_registry = load_json(parameter_registry_path)
    parameter_claims = load_json(parameter_claims_path)
    claims_map = load_claims_map(Path.cwd())

    if mode not in {"realistic", "speculative"}:
        raise ValueError(f"unsupported mode: {mode}")

    candidate_paths = _collect_numeric_paths(scenario)
    bounds_map = _schema_bounds(schema)
    registry_entries = [
        item
        for item in parameter_registry.get("parameters", [])
        if isinstance(item, dict) and isinstance(item.get("parameter_id"), str)
    ]
    registry_ids = {item.get("parameter_id") for item in registry_entries}
    registry_by_id = {str(item["parameter_id"]): item for item in registry_entries}
    claim_ids = {
        item.get("parameter_id")
        for item in parameter_claims.get("claims", [])
        if isinstance(item, dict) and isinstance(item.get("parameter_id"), str)
    }

    missing_bindings = sorted(path for path in candidate_paths if path not in registry_ids or path not in claim_ids)
    if missing_bindings:
        raise ValueError("missing parameter bindings for sensitivity run: " + ", ".join(missing_bindings))

    filtered_paths: List[str] = []
    for path in candidate_paths:
        entry = registry_by_id[path]
        if not bool(entry.get("affects_core_probability", False)):
            continue
        domain = str(entry.get("domain", "realistic"))
        if mode == "realistic" and domain != "realistic":
            continue
        filtered_paths.append(path)

    if not filtered_paths:
        raise ValueError(f"no candidate paths for sensitivity mode={mode}")

    scored: List[Dict[str, Any]] = []
    for path in filtered_paths:
        score = _score_parameter(
            scenario,
            path,
            bounds_map,
            mode=mode,
            claims_map=claims_map,
        )
        score["domain"] = registry_by_id[path].get("domain", "realistic")
        scored.append(score)

    scored.sort(key=lambda item: (-float(item["influence_score"]), item["parameter_id"]))
    top_5 = scored[:5]
    negligible = [item for item in scored if float(item["raw_delta_p_success"]) <= 1e-5]

    trust_map = _trust_by_parameter(parameter_claims)
    trust_penalty = {"A": 0.1, "B": 0.3, "C": 0.6, "D": 1.0}
    gaps: List[Dict[str, Any]] = []
    for item in scored:
        trust = trust_map.get(item["parameter_id"], "D")
        impact = float(item["influence_score"]) * trust_penalty.get(trust, 1.0)
        gaps.append(
            {
                "parameter_id": item["parameter_id"],
                "trust_grade": trust,
                "impact_low_trust_score": round(impact, 12),
            }
        )
    gaps.sort(key=lambda item: (-float(item["impact_low_trust_score"]), item["parameter_id"]))

    speculative_drivers = [item for item in scored if item.get("domain") == "speculative"][:5]

    result = {
        "status": "PASS",
        "mode": mode,
        "baseline": str(scenario_path),
        "driver_count": len(scored),
        "top_5": top_5,
        "speculative_drivers": speculative_drivers,
        "negligible_parameters": negligible,
        "ranked": scored,
        "evidence_gaps": gaps[:10],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "SENSITIVITY_RESULTS.json", result)

    lines = ["# Dominant Drivers", "", f"Mode: `{mode}`.", "", "Top-5 parameters by deterministic OAT influence on `p_success`.", ""]
    for index, item in enumerate(top_5, start=1):
        lines.append(
            f"{index}. `{item['parameter_id']}` | influence={item['influence_score']:.6g} | "
            f"delta_p_success={item['raw_delta_p_success']:.6g}"
        )
    lines.append("")
    lines.append("Negligible impact threshold: `raw_delta_p_success <= 1e-5`.")
    if speculative_drivers:
        lines.append("")
        lines.append("Speculative drivers are listed separately and must not be used for realistic optimization.")
    (output_dir / "DOMINANT_DRIVERS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    gaps_lines = ["# Evidence Gaps", "", "Top parameters by `influence_score * trust_penalty` (higher means higher improvement priority).", ""]
    for index, item in enumerate(gaps[:10], start=1):
        gaps_lines.append(
            f"{index}. `{item['parameter_id']}` | trust={item['trust_grade']} | score={item['impact_low_trust_score']:.6g}"
        )
    (output_dir / "EVIDENCE_GAPS.md").write_text("\n".join(gaps_lines) + "\n", encoding="utf-8")

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--parameter-registry", default=str(DEFAULT_PARAMETER_REGISTRY))
    parser.add_argument("--parameter-claims", default=str(DEFAULT_PARAMETER_CLAIMS))
    parser.add_argument("--mode", choices=("realistic", "speculative"), default="realistic")
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def _render_text(payload: Mapping[str, Any]) -> str:
    lines = [
        "PASS: parameter sensitivity report",
        f"- mode: {payload['mode']}",
        f"- driver_count: {payload['driver_count']}",
        "- top_5:",
    ]
    for item in payload["top_5"]:
        lines.append(
            f"  - {item['parameter_id']}: influence={item['influence_score']:.6g}, "
            f"delta_p_success={item['raw_delta_p_success']:.6g}"
        )
    if payload.get("speculative_drivers"):
        lines.append("- speculative_drivers:")
        for item in payload["speculative_drivers"]:
            lines.append(
                f"  - {item['parameter_id']}: influence={item['influence_score']:.6g}, "
                f"delta_p_success={item['raw_delta_p_success']:.6g}"
            )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        result = run(
            scenario_path=Path(args.baseline),
            schema_path=Path(args.schema),
            parameter_registry_path=Path(args.parameter_registry),
            parameter_claims_path=Path(args.parameter_claims),
            mode=str(args.mode),
            output_dir=Path(args.output_dir),
        )
        rendered = render_output(result, output_format=args.format, text_renderer=_render_text)
        print(rendered)
        if args.output:
            write_text(Path(args.output), rendered)
        return EXIT_PASS
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return EXIT_VIOLATION
    except Exception as exc:  # noqa: BLE001
        message = f"INTERNAL ERROR: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
