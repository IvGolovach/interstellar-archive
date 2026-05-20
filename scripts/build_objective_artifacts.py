#!/usr/bin/env python3
"""Build deterministic objective contract artifacts for F0."""

from __future__ import annotations

import argparse
import copy
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
from typing import Any, Dict, List, Mapping, Sequence

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.dag import contracts
from mission.baseline import build_output, load_claims_map
from mission.optimization import risk_envelope
from scripts.ci import parameter_domain_guard, parameter_evidence_validate


DEFAULT_CONTRACT = Path("mission/objectives/objective_contract.v1.json")
DEFAULT_RISK_SPEC = Path("mission/objectives/risk_envelope.v1.json")
DEFAULT_SCENARIO = Path("mission/BASELINE_SCENARIO_v1.json")
DEFAULT_P_SUCCESS_DEFENSIBILITY = Path("artifacts/p_success_defensibility.json")
DEFAULT_DETERMINISM_STATUS = Path("artifacts/determinism_status.json")
DEFAULT_PARAMETER_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_PARAMETER_CLAIMS = Path("parameters/registry/parameter_claims.v1.json")
DEFAULT_EVIDENCE_SOURCES = Path("parameters/registry/evidence_sources.v1.json")
DEFAULT_OUTPUT = Path("artifacts/objective_score_baseline.v1.json")


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _read_commit_sha(determinism_status: Mapping[str, Any], engine_commit: str) -> str:
    if engine_commit != "AUTO":
        return engine_commit
    value = determinism_status.get("last_verified_commit_sha")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unknown"


def _available_metrics(contract: Mapping[str, Any], mode: str) -> List[str]:
    objective_sets = contract.get("objective_sets", {})
    definitions = contract.get("definitions", {})
    mode_set = objective_sets.get(mode, {}) if isinstance(objective_sets, Mapping) else {}

    aggregation = mode_set.get("aggregation", {}) if isinstance(mode_set, Mapping) else {}
    dimensions = aggregation.get("dimensions") if isinstance(aggregation, Mapping) else None
    ordered = dimensions if isinstance(dimensions, list) else aggregation.get("order", [])
    if not isinstance(ordered, list):
        return []

    secondary_by_metric: Dict[str, Mapping[str, Any]] = {}
    secondary = mode_set.get("secondary", []) if isinstance(mode_set, Mapping) else []
    if isinstance(secondary, list):
        for item in secondary:
            if isinstance(item, Mapping) and isinstance(item.get("metric"), str):
                secondary_by_metric[str(item["metric"])] = item

    available: List[str] = []
    for metric in ordered:
        if not isinstance(metric, str):
            continue
        metric_def = definitions.get(metric, {}) if isinstance(definitions, Mapping) else {}
        metric_secondary = secondary_by_metric.get(metric, {})

        def_status = metric_def.get("status") if isinstance(metric_def, Mapping) else None
        secondary_status = metric_secondary.get("status") if isinstance(metric_secondary, Mapping) else None

        if def_status == "N/A_v1" or secondary_status == "N/A_v1":
            continue
        available.append(metric)
    return available


def _constraint_status(
    *,
    repo_root: Path,
    scenario_path: Path,
    parameter_registry_path: Path,
    parameter_claims_path: Path,
    evidence_sources_path: Path,
) -> List[Dict[str, Any]]:
    domain_result = parameter_domain_guard.run_guard(
        repo_root=repo_root,
        parameter_registry_path=parameter_registry_path,
        parameter_claims_path=parameter_claims_path,
        scenario_path=scenario_path,
        mission_script_path=Path("scripts/mission_baseline_check.py"),
        divergence_threshold=20.0,
    )

    evidence_result = parameter_evidence_validate.validate(
        parameter_registry=load_json(repo_root / parameter_registry_path),
        evidence_sources_payload=load_json(repo_root / evidence_sources_path),
        parameter_claims_payload=load_json(repo_root / parameter_claims_path),
    )

    no_d_ok = bool(domain_result.get("status") == "PASS" and domain_result.get("realistic_mode_verified"))
    completeness = float(evidence_result.get("evidence_completeness_ratio", 0.0))
    evidence_ok = bool(
        evidence_result.get("status") == "PASS"
        and int(evidence_result.get("missing_evidence_count", 1)) == 0
        and int(evidence_result.get("realistic_D_violations", 1)) == 0
        and abs(completeness - 1.0) <= 1e-12
    )

    return [
        {
            "id": "no_D_grade_influence",
            "status": "PASS" if no_d_ok else "FAIL",
            "details": {
                "realistic_mode_verified": bool(domain_result.get("realistic_mode_verified", False)),
                "domain_guard_status": str(domain_result.get("status", "FAIL")),
            },
        },
        {
            "id": "evidence_completeness_1.0",
            "status": "PASS" if evidence_ok else "FAIL",
            "details": {
                "evidence_completeness_ratio": _round(completeness, 6),
                "missing_evidence_count": int(evidence_result.get("missing_evidence_count", 0)),
                "realistic_D_violations": int(evidence_result.get("realistic_D_violations", 0)),
                "evidence_validate_status": str(evidence_result.get("status", "FAIL")),
            },
        },
    ]


def _score_block(
    *,
    contract: Mapping[str, Any],
    mode: str,
    output: Mapping[str, Any],
    risk_score: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    available = _available_metrics(contract, mode)

    block: Dict[str, Any] = {
        "p_success": _round(float(output.get("p_success", 0.0))),
        "objective_vector": [],
        "rank_key": "pareto" if mode == "realistic" else "lexicographic",
    }

    values: Dict[str, float | None] = {
        "p_success": _round(float(output.get("p_success", 0.0))),
    }
    if mode == "realistic":
        if not isinstance(risk_score, Mapping):
            raise ValueError("realistic score requires risk_score")
        values["risk_envelope"] = _round(float(risk_score["risk_envelope"]))
        block["risk_envelope"] = _round(float(risk_score["risk_envelope"]))
        block["risk_meta"] = {
            "method": str(risk_score.get("method", "lower_quantile")),
            "quantile": _round(float(risk_score.get("quantile", 0.05))),
            "distribution_size": int(risk_score.get("distribution_size", 0)),
            "q_value": _round(float(risk_score.get("q_value", 0.0))),
        }

    vector: List[float] = []
    for metric in available:
        if metric in values and values[metric] is not None:
            vector.append(float(values[metric]))
    block["objective_vector"] = vector
    return block


def build_artifact(
    *,
    repo_root: Path,
    contract_path: Path,
    risk_spec_path: Path,
    scenario_path: Path,
    p_success_defensibility_path: Path,
    determinism_status_path: Path,
    parameter_registry_path: Path,
    parameter_claims_path: Path,
    evidence_sources_path: Path,
    output_path: Path,
) -> Dict[str, Any]:
    contract = load_json(repo_root / contract_path)
    risk_spec = load_json(repo_root / risk_spec_path)
    scenario = load_json(repo_root / scenario_path)
    p_success_defensibility = load_json(repo_root / p_success_defensibility_path)
    determinism_status = load_json(repo_root / determinism_status_path)

    claims_map = load_claims_map(repo_root)
    realistic_output = build_output(
        copy.deepcopy(scenario),
        mode="realistic",
        claims_map=claims_map,
    )
    speculative_output = build_output(
        copy.deepcopy(scenario),
        mode="speculative",
        claims_map=claims_map,
    )

    definitions = contract.get("definitions", {})
    p_success_def = definitions.get("p_success", {}) if isinstance(definitions, Mapping) else {}
    p_success_ref = str(p_success_def.get("source", "")) if isinstance(p_success_def, Mapping) else ""
    if p_success_ref != str(p_success_defensibility_path):
        raise ValueError(
            "objective contract definitions.p_success.source must equal "
            f"'{p_success_defensibility_path}', got {p_success_ref!r}"
        )

    if p_success_defensibility.get("schema_version") != "p_success_defensibility.v1":
        raise ValueError("artifacts/p_success_defensibility.json schema_version must be p_success_defensibility.v1")
    if risk_spec.get("schema_version") != "risk_envelope.v1":
        raise ValueError("risk spec schema_version must be risk_envelope.v1")

    risk_quantile = risk_envelope.parse_quantile_from_spec(risk_spec)
    risk_samples = risk_envelope.parse_samples_from_spec(risk_spec, default=64)
    risk_realistic = risk_envelope.risk_envelope_from_scenario(
        scenario=scenario,
        claims_map=claims_map,
        mode="realistic",
        seed=int(risk_spec.get("deterministic_seed", 1)),
        samples=int(risk_samples),
        quantile=float(risk_quantile),
    )

    realistic_constraints = _constraint_status(
        repo_root=repo_root,
        scenario_path=scenario_path,
        parameter_registry_path=parameter_registry_path,
        parameter_claims_path=parameter_claims_path,
        evidence_sources_path=evidence_sources_path,
    )

    engine_commit = str(contract.get("engine_commit", "AUTO"))
    payload: Dict[str, Any] = {
        "schema_version": "objective_score.v1",
        "contract_ref": str(contract_path),
        "contract_snapshot": contract,
        "engine": {
            "commit_sha": _read_commit_sha(determinism_status, engine_commit),
            "seed": scenario.get("seed"),
            "mode": "dual",
            "scenario_ref": str(scenario_path),
        },
        "scores": {
            "realistic": _score_block(
                contract=contract,
                mode="realistic",
                output=realistic_output,
                risk_score=risk_realistic,
            ),
            "speculative": _score_block(
                contract=contract,
                mode="speculative",
                output=speculative_output,
                risk_score=None,
            ),
        },
        "constraints_status": {
            "realistic": realistic_constraints,
        },
        "defensibility": {
            "p_success_ref": str(p_success_defensibility_path),
        },
    }

    signature_basis = {
        "contract_ref": payload["contract_ref"],
        "contract_snapshot": payload["contract_snapshot"],
        "engine": payload["engine"],
        "scores": payload["scores"],
        "constraints_status": payload["constraints_status"],
    }
    payload["determinism_signature"] = contracts.sha256_hex(contracts.canonical_json(signature_basis))

    abs_output = repo_root / output_path
    write_json(abs_output, payload)
    digest = contracts.sha256_hex(contracts.canonical_json(payload))

    return {
        "status": "PASS",
        "output": str(output_path),
        "sha256": digest,
        "realistic_p_success": payload["scores"]["realistic"]["p_success"],
        "speculative_p_success": payload["scores"]["speculative"]["p_success"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--risk-spec", default=str(DEFAULT_RISK_SPEC))
    parser.add_argument("--scenario", default=str(DEFAULT_SCENARIO))
    parser.add_argument("--p-success-defensibility", default=str(DEFAULT_P_SUCCESS_DEFENSIBILITY))
    parser.add_argument("--determinism-status", default=str(DEFAULT_DETERMINISM_STATUS))
    parser.add_argument("--parameter-registry", default=str(DEFAULT_PARAMETER_REGISTRY))
    parser.add_argument("--parameter-claims", default=str(DEFAULT_PARAMETER_CLAIMS))
    parser.add_argument("--evidence-sources", default=str(DEFAULT_EVIDENCE_SOURCES))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_artifact(
            repo_root=Path(args.repo_root).resolve(),
            contract_path=Path(args.contract),
            risk_spec_path=Path(args.risk_spec),
            scenario_path=Path(args.scenario),
            p_success_defensibility_path=Path(args.p_success_defensibility),
            determinism_status_path=Path(args.determinism_status),
            parameter_registry_path=Path(args.parameter_registry),
            parameter_claims_path=Path(args.parameter_claims),
            evidence_sources_path=Path(args.evidence_sources),
            output_path=Path(args.output),
        )
        if args.format == "json":
            print(render_json(result))
        else:
            print("PASS: objective score artifact")
            print(f"- output: {result['output']}")
            print(f"- sha256: {result['sha256']}")
            print(f"- realistic_p_success: {result['realistic_p_success']}")
            print(f"- speculative_p_success: {result['speculative_p_success']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
