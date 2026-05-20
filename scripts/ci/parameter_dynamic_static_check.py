#!/usr/bin/env python3
"""Validate dynamic trace parameter-module usage against static usage graph contract."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_STATIC_GRAPH = Path("artifacts/parameter_static_usage_graph.json")


def validate_contract(
    *,
    static_graph: Mapping[str, Any],
    dynamic_trace: Mapping[str, Any],
) -> Dict[str, Any]:
    errors: List[str] = []
    violations: List[Dict[str, Any]] = []

    events = dynamic_trace.get("events")
    if not isinstance(events, list):
        errors.append("dynamic trace must contain list field 'events'")
        events = []

    checked_pairs = 0
    for index, event in enumerate(events):
        prefix = f"events[{index}]"
        if not isinstance(event, Mapping):
            errors.append(f"{prefix} must be object")
            continue

        module_id = event.get("module_id")
        if not isinstance(module_id, str) or not module_id:
            errors.append(f"{prefix}.module_id must be non-empty string")
            continue

        drivers = event.get("dominant_driver_parameter_ids")
        if not isinstance(drivers, list):
            errors.append(f"{prefix}.dominant_driver_parameter_ids must be list")
            continue

        for parameter_id in drivers:
            if not isinstance(parameter_id, str) or not parameter_id:
                errors.append(f"{prefix}.dominant_driver_parameter_ids contains invalid parameter id")
                continue
            checked_pairs += 1

            static_entry = static_graph.get(parameter_id)
            if not isinstance(static_entry, Mapping):
                violations.append(
                    {
                        "event_index": index,
                        "parameter_id": parameter_id,
                        "module_id": module_id,
                        "reason": "parameter_id missing in static usage graph",
                    }
                )
                continue

            modules = static_entry.get("modules")
            if not isinstance(modules, list):
                violations.append(
                    {
                        "event_index": index,
                        "parameter_id": parameter_id,
                        "module_id": module_id,
                        "reason": "static graph entry has invalid modules list",
                    }
                )
                continue

            if module_id not in modules:
                violations.append(
                    {
                        "event_index": index,
                        "parameter_id": parameter_id,
                        "module_id": module_id,
                        "reason": "dynamic trace module not declared in static usage graph",
                    }
                )

    status = "PASS" if not errors and not violations else "FAIL"
    return {
        "status": status,
        "checked_parameter_module_pairs": checked_pairs,
        "event_count": len(events),
        "violation_count": len(violations),
        "violations": violations,
        "errors": errors,
    }


def _render_text(payload: Mapping[str, Any]) -> str:
    lines = [
        f"{payload['status']}: dynamic/static parameter usage contract",
        f"- event_count: {payload['event_count']}",
        f"- checked_parameter_module_pairs: {payload['checked_parameter_module_pairs']}",
        f"- violation_count: {payload['violation_count']}",
    ]
    if payload.get("errors"):
        lines.append("- errors:")
        for item in payload["errors"]:
            lines.append(f"  - {item}")
    if payload.get("violations"):
        lines.append("- violations:")
        for item in payload["violations"]:
            lines.append(
                "  - event={event_index} parameter={parameter_id} module={module_id} reason={reason}".format(**item)
            )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static-graph", default=str(DEFAULT_STATIC_GRAPH))
    parser.add_argument("--dynamic-trace", required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = validate_contract(
            static_graph=load_json(Path(args.static_graph).resolve()),
            dynamic_trace=load_json(Path(args.dynamic_trace).resolve()),
        )
        rendered = render_output(result, output_format=args.format, text_renderer=_render_text)
        print(rendered)
        if args.output:
            write_text(Path(args.output), rendered)
        if result["status"] == "PASS":
            return EXIT_PASS
        return EXIT_VIOLATION if args.strict else EXIT_PASS
    except Exception as exc:  # noqa: BLE001
        message = f"INTERNAL ERROR: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
