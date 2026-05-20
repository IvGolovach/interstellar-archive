#!/usr/bin/env python3
"""Validate objective-function contract and baseline objective artifact."""

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

DEFAULT_CONTRACT = Path("mission/objectives/objective_contract.v1.json")
DEFAULT_ARTIFACT = Path("artifacts/objective_score_baseline.v1.json")
DEFAULT_P_SUCCESS_DEFENSIBILITY = Path("artifacts/p_success_defensibility.json")
DEFAULT_RISK_SPEC = Path("mission/objectives/risk_envelope.v1.json")

REQUIRED_MODES = ("realistic", "speculative")
REQUIRED_REALISTIC_CONSTRAINTS = {"no_D_grade_influence", "evidence_completeness_1.0"}
FORBIDDEN_REALISTIC_METRICS = {"trust_weighted_score"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _find_secondary(mode_set: Mapping[str, Any], metric: str) -> Mapping[str, Any] | None:
    secondary = mode_set.get("secondary")
    if not isinstance(secondary, list):
        return None
    for item in secondary:
        if isinstance(item, Mapping) and item.get("metric") == metric:
            return item
    return None


def _available_metrics(contract: Mapping[str, Any], mode: str) -> List[str]:
    objective_sets = contract.get("objective_sets", {})
    definitions = contract.get("definitions", {})
    mode_set = objective_sets.get(mode, {}) if isinstance(objective_sets, Mapping) else {}
    aggregation = mode_set.get("aggregation", {}) if isinstance(mode_set, Mapping) else {}

    dimensions = aggregation.get("dimensions") if isinstance(aggregation, Mapping) else None
    ordered = dimensions if isinstance(dimensions, list) else aggregation.get("order", [])
    if not isinstance(ordered, list):
        return []

    available: List[str] = []
    for metric in ordered:
        if not isinstance(metric, str):
            continue
        def_item = definitions.get(metric, {}) if isinstance(definitions, Mapping) else {}
        secondary_item = _find_secondary(mode_set, metric)

        def_status = def_item.get("status") if isinstance(def_item, Mapping) else None
        secondary_status = secondary_item.get("status") if isinstance(secondary_item, Mapping) else None
        if def_status == "N/A_v1" or secondary_status == "N/A_v1":
            continue
        available.append(metric)
    return available


def validate_contract(
    *,
    contract: Mapping[str, Any],
    artifact: Mapping[str, Any],
    contract_path: Path,
    p_success_defensibility_path: Path,
    risk_spec_path: Path,
) -> Dict[str, Any]:
    errors: List[str] = []

    if contract.get("schema_version") != "objective_contract.v1":
        errors.append("contract.schema_version must be objective_contract.v1")

    modes = contract.get("modes")
    if modes != list(REQUIRED_MODES):
        errors.append("contract.modes must equal ['realistic', 'speculative']")

    objective_sets = contract.get("objective_sets")
    if not isinstance(objective_sets, Mapping):
        errors.append("contract.objective_sets must be object")
        objective_sets = {}

    definitions = contract.get("definitions")
    if not isinstance(definitions, Mapping):
        errors.append("contract.definitions must be object")
        definitions = {}

    p_success_def = definitions.get("p_success") if isinstance(definitions, Mapping) else None
    if not isinstance(p_success_def, Mapping):
        errors.append("contract.definitions.p_success must be object")
        p_success_ref = ""
    else:
        p_success_ref = str(p_success_def.get("source", ""))
        if p_success_ref != str(p_success_defensibility_path):
            errors.append(
                "contract.definitions.p_success.source must equal "
                f"'{p_success_defensibility_path}', got {p_success_ref!r}"
            )

    risk_def = definitions.get("risk_envelope") if isinstance(definitions, Mapping) else None
    if not isinstance(risk_def, Mapping):
        errors.append("contract.definitions.risk_envelope must be object")
    else:
        if risk_def.get("source") != str(risk_spec_path):
            errors.append(
                "contract.definitions.risk_envelope.source must equal "
                f"'{risk_spec_path}', got {risk_def.get('source')!r}"
            )
        if risk_def.get("method") != "lower_quantile":
            errors.append("contract.definitions.risk_envelope.method must be lower_quantile")
        quantile = risk_def.get("quantile")
        if not _is_number(quantile) or not (0.0 < float(quantile) < 1.0):
            errors.append("contract.definitions.risk_envelope.quantile must be numeric in (0,1)")

    for mode in REQUIRED_MODES:
        mode_set = objective_sets.get(mode) if isinstance(objective_sets, Mapping) else None
        if not isinstance(mode_set, Mapping):
            errors.append(f"contract.objective_sets.{mode} must be object")
            continue

        primary = mode_set.get("primary")
        if not isinstance(primary, Mapping):
            errors.append(f"contract.objective_sets.{mode}.primary must be object")
        else:
            if primary.get("metric") != "p_success":
                errors.append(f"contract.objective_sets.{mode}.primary.metric must be p_success")
            if primary.get("maximize") is not True:
                errors.append(f"contract.objective_sets.{mode}.primary.maximize must be true")

        aggregation = mode_set.get("aggregation")
        if not isinstance(aggregation, Mapping):
            errors.append(f"contract.objective_sets.{mode}.aggregation must be object")
        else:
            if mode == "realistic":
                if aggregation.get("type") != "pareto":
                    errors.append("contract.objective_sets.realistic.aggregation.type must be pareto")
                dimensions = aggregation.get("dimensions")
                if dimensions != ["p_success", "risk_envelope"]:
                    errors.append(
                        "contract.objective_sets.realistic.aggregation.dimensions must be ['p_success','risk_envelope']"
                    )
            else:
                if aggregation.get("type") not in {"lexicographic", "weighted"}:
                    errors.append(f"contract.objective_sets.{mode}.aggregation.type invalid")
                order = aggregation.get("order")
                if not isinstance(order, list) or not order or any(not isinstance(item, str) for item in order):
                    errors.append(f"contract.objective_sets.{mode}.aggregation.order must be non-empty string list")

        if mode == "realistic":
            secondary = mode_set.get("secondary", [])
            if isinstance(secondary, list):
                for item in secondary:
                    if isinstance(item, Mapping):
                        metric = item.get("metric")
                        if metric in FORBIDDEN_REALISTIC_METRICS:
                            errors.append(
                                "contract.objective_sets.realistic.secondary contains forbidden metric "
                                f"{metric!r}"
                            )

            constraints = mode_set.get("constraints")
            if not isinstance(constraints, list):
                errors.append("contract.objective_sets.realistic.constraints must be list")
            else:
                constraint_ids = {
                    str(item.get("id"))
                    for item in constraints
                    if isinstance(item, Mapping) and isinstance(item.get("id"), str)
                }
                missing = sorted(REQUIRED_REALISTIC_CONSTRAINTS - constraint_ids)
                if missing:
                    errors.append(
                        "contract.objective_sets.realistic.constraints missing required ids: " + ", ".join(missing)
                    )

    if artifact.get("schema_version") != "objective_score.v1":
        errors.append("artifact.schema_version must be objective_score.v1")

    contract_ref = artifact.get("contract_ref")
    if contract_ref != str(contract_path):
        errors.append(f"artifact.contract_ref must equal '{contract_path}', got {contract_ref!r}")

    contract_snapshot = artifact.get("contract_snapshot")
    if not isinstance(contract_snapshot, Mapping):
        errors.append("artifact.contract_snapshot must be object")
    else:
        if contract_snapshot != contract:
            errors.append("artifact.contract_snapshot must match mission/objectives/objective_contract.v1.json")

    defensibility = artifact.get("defensibility")
    if not isinstance(defensibility, Mapping):
        errors.append("artifact.defensibility must be object")
    else:
        if defensibility.get("p_success_ref") != str(p_success_defensibility_path):
            errors.append(
                "artifact.defensibility.p_success_ref must equal "
                f"'{p_success_defensibility_path}'"
            )

    scores = artifact.get("scores")
    if not isinstance(scores, Mapping):
        errors.append("artifact.scores must be object")
        scores = {}

    realistic_quantile = None
    if isinstance(risk_def, Mapping) and _is_number(risk_def.get("quantile")):
        realistic_quantile = float(risk_def.get("quantile"))

    for mode in REQUIRED_MODES:
        score = scores.get(mode)
        if not isinstance(score, Mapping):
            errors.append(f"artifact.scores.{mode} must be object")
            continue

        p_success = score.get("p_success")
        if not _is_number(p_success):
            errors.append(f"artifact.scores.{mode}.p_success must be numeric")

        vector = score.get("objective_vector")
        if not isinstance(vector, list):
            errors.append(f"artifact.scores.{mode}.objective_vector must be list")
            vector = []
        elif any(not _is_number(item) for item in vector):
            errors.append(f"artifact.scores.{mode}.objective_vector must contain only numbers")

        available = _available_metrics(contract, mode)
        if len(vector) != len(available):
            errors.append(
                f"artifact.scores.{mode}.objective_vector length mismatch: expected {len(available)}, got {len(vector)}"
            )

        for idx, metric in enumerate(available):
            expected_value = None
            if metric == "p_success":
                expected_value = float(p_success) if _is_number(p_success) else None
            else:
                metric_value = score.get(metric)
                if _is_number(metric_value):
                    expected_value = float(metric_value)
                else:
                    errors.append(f"artifact.scores.{mode}.{metric} must be numeric when active in objective_vector")

            if expected_value is not None and idx < len(vector):
                actual = float(vector[idx])
                if abs(actual - expected_value) > 1e-12:
                    errors.append(
                        f"artifact.scores.{mode}.objective_vector[{idx}] must equal {metric} ({expected_value}), got {actual}"
                    )

        if mode == "realistic":
            risk_value = score.get("risk_envelope")
            if not _is_number(risk_value):
                errors.append("artifact.scores.realistic.risk_envelope must be numeric")
            elif not (0.0 <= float(risk_value) <= 1.0):
                errors.append("artifact.scores.realistic.risk_envelope must be in [0,1]")

            risk_meta = score.get("risk_meta")
            if not isinstance(risk_meta, Mapping):
                errors.append("artifact.scores.realistic.risk_meta must be object")
            else:
                if risk_meta.get("method") != "lower_quantile":
                    errors.append("artifact.scores.realistic.risk_meta.method must be lower_quantile")
                if not _is_number(risk_meta.get("quantile")):
                    errors.append("artifact.scores.realistic.risk_meta.quantile must be numeric")
                elif realistic_quantile is not None and abs(float(risk_meta.get("quantile")) - realistic_quantile) > 1e-12:
                    errors.append("artifact.scores.realistic.risk_meta.quantile must match contract quantile")
                if not isinstance(risk_meta.get("distribution_size"), int) or int(risk_meta.get("distribution_size")) <= 1:
                    errors.append("artifact.scores.realistic.risk_meta.distribution_size must be int > 1")
                if not _is_number(risk_meta.get("q_value")):
                    errors.append("artifact.scores.realistic.risk_meta.q_value must be numeric")

    constraints_status = artifact.get("constraints_status")
    if not isinstance(constraints_status, Mapping):
        errors.append("artifact.constraints_status must be object")
    else:
        realistic_constraints = constraints_status.get("realistic")
        if not isinstance(realistic_constraints, list):
            errors.append("artifact.constraints_status.realistic must be list")
        else:
            by_id: Dict[str, Mapping[str, Any]] = {}
            for item in realistic_constraints:
                if isinstance(item, Mapping) and isinstance(item.get("id"), str):
                    by_id[str(item["id"])] = item
            for required_id in sorted(REQUIRED_REALISTIC_CONSTRAINTS):
                if required_id not in by_id:
                    errors.append(f"artifact.constraints_status.realistic missing id '{required_id}'")
                    continue
                status = by_id[required_id].get("status")
                if status not in {"PASS", "FAIL"}:
                    errors.append(
                        f"artifact.constraints_status.realistic[{required_id}].status must be PASS|FAIL"
                    )

    return {
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
    }


def _render_text(result: Mapping[str, Any]) -> str:
    lines = [
        f"{result['status']}: objective contract validation",
        f"- error_count: {result['error_count']}",
    ]
    if result["errors"]:
        lines.append("- errors:")
        for item in result["errors"]:
            lines.append(f"  - {item}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--p-success-defensibility", default=str(DEFAULT_P_SUCCESS_DEFENSIBILITY))
    parser.add_argument("--risk-spec", default=str(DEFAULT_RISK_SPEC))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        contract = load_json(Path(args.contract).resolve())
        artifact = load_json(Path(args.artifact).resolve())
        p_success_path = Path(args.p_success_defensibility).resolve()
        if not p_success_path.exists():
            print(f"FAIL: missing p_success defensibility file: {p_success_path}")
            return EXIT_VIOLATION if args.strict else EXIT_PASS

        result = validate_contract(
            contract=contract,
            artifact=artifact,
            contract_path=Path(args.contract),
            p_success_defensibility_path=Path(args.p_success_defensibility),
            risk_spec_path=Path(args.risk_spec),
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
