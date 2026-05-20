#!/usr/bin/env python3
"""Build Optimization v2 four-axis decision-surface artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Mapping

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_json, write_json
except ImportError:
    from script_io import load_json, render_json, write_json

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.optimization import v2


DEFAULT_OBJECTIVE_CONTRACT = Path("mission/objectives/objective_contract.v1.json")
DEFAULT_RISK_SPEC = Path("mission/objectives/risk_envelope.v1.json")
DEFAULT_PARAMETER_CLAIMS = Path("parameters/registry/parameter_claims.v1.json")
DEFAULT_SEARCH_SPACE = Path("artifacts/optimization_search_space.v1.json")
DEFAULT_FRONTIER = Path("artifacts/optimization_frontier_realistic.v1.json")
DEFAULT_MISSION_FEASIBILITY = Path("artifacts/mission_feasibility_screen.v1.json")
DEFAULT_CAPSULE_RISK_BUDGET = Path("artifacts/capsule_risk_budget.v1.json")
DEFAULT_EVIDENCE_CAMPAIGN = Path("artifacts/evidence_upgrade_campaign.v1.json")
DEFAULT_OUTPUT = Path("artifacts/optimization_v2_frontier.v1.json")


def _score_from_source(point: Mapping[str, Any], field: str) -> float:
    scores = point.get("scores", {})
    if not isinstance(scores, Mapping):
        return 0.0
    value = scores.get(field)
    return v2._round(float(value)) if v2._is_number(value) else 0.0


def _public_dominant_drivers(point: Mapping[str, Any]) -> Dict[str, Any]:
    raw = point.get("dominant_drivers", {})
    if not isinstance(raw, Mapping):
        return {"method": "unknown", "parameter_ids": [], "excluded_internal_parameter_count": 0}
    raw_ids = raw.get("parameter_ids", [])
    if not isinstance(raw_ids, list):
        raw_ids = []
    public_ids = [
        str(parameter_id)
        for parameter_id in raw_ids
        if isinstance(parameter_id, str) and not parameter_id.startswith("code_literal.")
    ]
    return {
        "method": str(raw.get("method", "unknown")),
        "parameter_ids": public_ids,
        "excluded_internal_parameter_count": len(raw_ids) - len(public_ids),
    }


def build_payload(
    *,
    repo_root: Path,
    objective_contract_path: Path = DEFAULT_OBJECTIVE_CONTRACT,
    risk_spec_path: Path = DEFAULT_RISK_SPEC,
    parameter_claims_path: Path = DEFAULT_PARAMETER_CLAIMS,
    search_space_path: Path = DEFAULT_SEARCH_SPACE,
    frontier_path: Path = DEFAULT_FRONTIER,
    mission_feasibility_path: Path = DEFAULT_MISSION_FEASIBILITY,
    capsule_risk_budget_path: Path = DEFAULT_CAPSULE_RISK_BUDGET,
    evidence_campaign_path: Path = DEFAULT_EVIDENCE_CAMPAIGN,
) -> Dict[str, Any]:
    source_paths = [
        str(objective_contract_path),
        str(risk_spec_path),
        str(parameter_claims_path),
        str(search_space_path),
        str(frontier_path),
        str(mission_feasibility_path),
        str(capsule_risk_budget_path),
        str(evidence_campaign_path),
    ]
    for path in source_paths:
        if not (repo_root / path).exists():
            raise FileNotFoundError(path)

    search_space = load_json(repo_root / search_space_path)
    source_frontier = load_json(repo_root / frontier_path)
    parameter_claims = load_json(repo_root / parameter_claims_path)

    if source_frontier.get("schema_version") != "optimization_frontier.v1":
        raise ValueError("source frontier schema_version must be optimization_frontier.v1")
    if source_frontier.get("mode") != v2.MODE:
        raise ValueError("source frontier mode must be realistic")
    if search_space.get("schema_version") != "optimization_search_space.v1":
        raise ValueError("search space schema_version must be optimization_search_space.v1")

    source_pareto = {
        int(index)
        for index in source_frontier.get("pareto_frontier_indices", [])
        if isinstance(index, int)
    }
    candidates = []
    for index, point in enumerate(source_frontier.get("points", [])):
        if not isinstance(point, Mapping):
            continue
        parameters = point.get("parameters", {})
        if not isinstance(parameters, Mapping):
            parameters = {}

        qualification = v2.qualification_gap(
            candidate_parameters=parameters,
            search_space=search_space,
            parameter_claims=parameter_claims,
        )
        cost = v2.cost_proxy(
            candidate_parameters=parameters,
            search_space=search_space,
        )
        p_success = _score_from_source(point, "p_success")
        risk_envelope = _score_from_source(point, "risk_envelope")
        candidate_id = f"optv2-{point.get('candidate_id', f'pt-{index:03d}')}"
        candidate = {
            "candidate_id": candidate_id,
            "source_candidate_id": str(point.get("candidate_id", f"pt-{index:03d}")),
            "scores": {
                "p_success": p_success,
                "risk_envelope": risk_envelope,
                "qualification_gap": qualification["score"],
                "cost_proxy": cost["score"],
                "objective_vector": [
                    p_success,
                    risk_envelope,
                    qualification["score"],
                    cost["score"],
                ],
                "rank_key": "pareto",
            },
            "axis_explainability": {
                "qualification_gap": qualification,
                "cost_proxy": cost,
            },
            "source_constraint_status": point.get("constraint_status", {}),
            "dominant_drivers": _public_dominant_drivers(point),
            "source_v1_pareto_member": index in source_pareto,
        }
        candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            -float(item["scores"]["p_success"]),
            float(item["scores"]["risk_envelope"]),
            float(item["scores"]["qualification_gap"]),
            float(item["scores"]["cost_proxy"]),
            str(item["candidate_id"]),
        )
    )
    pareto_ids = v2.pareto_candidate_ids(candidates)
    pareto_set = set(pareto_ids)
    for candidate in candidates:
        candidate["pareto_frontier_member"] = candidate["candidate_id"] in pareto_set

    payload: Dict[str, Any] = {
        "schema_version": v2.SCHEMA_VERSION,
        "generator": v2.GENERATOR,
        "mode": v2.MODE,
        "non_certification_notice": True,
        "public_scope": "optimization_v2_four_axis_decision_surface",
        "source_artifacts": v2.source_artifacts(repo_root, source_paths),
        "axis_contract": v2.axis_contract(),
        "candidate_count": len(candidates),
        "frontier_candidate_count": len(pareto_ids),
        "candidates": candidates,
        "pareto_frontier_candidate_ids": pareto_ids,
        "rollup": {
            "dimension_count": len(v2.AXIS_IDS),
            "axis_ids": list(v2.AXIS_IDS),
            "aggregation_policy": "pareto_first_no_hidden_weighted_sum",
            "source_frontier_candidate_count": int(source_frontier.get("evaluation_count", len(candidates))),
            "source_frontier_pareto_count": len(source_pareto),
            "global_optimum_claimed": False,
            "hidden_weighted_sum_used": False,
            "calibrated_cost_model_available": False,
            "qualification_complete": False,
            "top_candidate_id": pareto_ids[0] if pareto_ids else None,
        },
        "external_evidence_gaps": list(v2.EXTERNAL_EVIDENCE_GAPS),
        "blocked_claims": list(v2.BLOCKED_CLAIMS),
        "interpretation_limits": list(v2.INTERPRETATION_LIMITS),
    }
    signature_basis = {
        "mode": payload["mode"],
        "axis_contract": payload["axis_contract"],
        "candidate_count": payload["candidate_count"],
        "frontier_candidate_count": payload["frontier_candidate_count"],
        "candidates": payload["candidates"],
        "pareto_frontier_candidate_ids": payload["pareto_frontier_candidate_ids"],
        "rollup": payload["rollup"],
        "external_evidence_gaps": payload["external_evidence_gaps"],
        "blocked_claims": payload["blocked_claims"],
    }
    payload["determinism_signature"] = v2.sha256_payload(signature_basis)
    return payload


def build_and_write(
    *,
    repo_root: Path,
    output_path: Path,
    objective_contract_path: Path = DEFAULT_OBJECTIVE_CONTRACT,
    risk_spec_path: Path = DEFAULT_RISK_SPEC,
    parameter_claims_path: Path = DEFAULT_PARAMETER_CLAIMS,
    search_space_path: Path = DEFAULT_SEARCH_SPACE,
    frontier_path: Path = DEFAULT_FRONTIER,
    mission_feasibility_path: Path = DEFAULT_MISSION_FEASIBILITY,
    capsule_risk_budget_path: Path = DEFAULT_CAPSULE_RISK_BUDGET,
    evidence_campaign_path: Path = DEFAULT_EVIDENCE_CAMPAIGN,
) -> Dict[str, Any]:
    payload = build_payload(
        repo_root=repo_root,
        objective_contract_path=objective_contract_path,
        risk_spec_path=risk_spec_path,
        parameter_claims_path=parameter_claims_path,
        search_space_path=search_space_path,
        frontier_path=frontier_path,
        mission_feasibility_path=mission_feasibility_path,
        capsule_risk_budget_path=capsule_risk_budget_path,
        evidence_campaign_path=evidence_campaign_path,
    )
    write_json(repo_root / output_path, payload)
    return {
        "status": "PASS",
        "output": str(output_path),
        "candidate_count": payload["candidate_count"],
        "frontier_candidate_count": payload["frontier_candidate_count"],
        "axis_ids": payload["rollup"]["axis_ids"],
        "sha256": v2.sha256_payload(payload),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--objective-contract", default=str(DEFAULT_OBJECTIVE_CONTRACT))
    parser.add_argument("--risk-spec", default=str(DEFAULT_RISK_SPEC))
    parser.add_argument("--parameter-claims", default=str(DEFAULT_PARAMETER_CLAIMS))
    parser.add_argument("--search-space", default=str(DEFAULT_SEARCH_SPACE))
    parser.add_argument("--frontier", default=str(DEFAULT_FRONTIER))
    parser.add_argument("--mission-feasibility", default=str(DEFAULT_MISSION_FEASIBILITY))
    parser.add_argument("--capsule-risk-budget", default=str(DEFAULT_CAPSULE_RISK_BUDGET))
    parser.add_argument("--evidence-campaign", default=str(DEFAULT_EVIDENCE_CAMPAIGN))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_and_write(
            repo_root=Path(args.repo_root).resolve(),
            output_path=Path(args.output),
            objective_contract_path=Path(args.objective_contract),
            risk_spec_path=Path(args.risk_spec),
            parameter_claims_path=Path(args.parameter_claims),
            search_space_path=Path(args.search_space),
            frontier_path=Path(args.frontier),
            mission_feasibility_path=Path(args.mission_feasibility),
            capsule_risk_budget_path=Path(args.capsule_risk_budget),
            evidence_campaign_path=Path(args.evidence_campaign),
        )
        if args.format == "json":
            print(render_json(result))
        else:
            print("PASS: optimization v2 artifact")
            print(f"- output: {result['output']}")
            print(f"- candidate_count: {result['candidate_count']}")
            print(f"- frontier_candidate_count: {result['frontier_candidate_count']}")
            print(f"- axes: {','.join(result['axis_ids'])}")
            print(f"- sha256: {result['sha256']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
