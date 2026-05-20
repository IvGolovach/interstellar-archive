"""Artifact-oriented runner for optimization engine v1."""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

from mission.optimization import pareto
from mission.optimization.engine_v1 import OptimizationConfig, run_optimization
from mission.optimization.search_space import ResolveResult, resolve_search_space
from mission.guards.optimization import validate_plan as validate_optimization_plan
from mission.guards.parameter_domain import run_guard as run_parameter_domain_guard


REQUIRED_ARTIFACT_FILES = (
    "OPTIMIZATION_CONFIG.json",
    "SEARCH_SPACE_RESOLVED.json",
    "SAMPLE_RESULTS.json",
    "PARETO_FRONTIER.json",
    "TOP_K_SOLUTIONS.json",
    "CONSTRAINT_VIOLATIONS.json",
    "DETERMINISM_CHECK.json",
    "meta.json",
    "FINAL_REPORT.md",
)


@dataclass(frozen=True)
class RunContext:
    repo_root: Path
    scenario_path: Path
    plan_path: Path
    parameter_registry_path: Path
    parameter_claims_path: Path


@dataclass(frozen=True)
class OptimizationRunResult:
    payload: Dict[str, Any]
    pack_hash: str
    domain_verified: bool
    speculative_used: bool


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _compute_pack_hash(payload: Mapping[str, Any]) -> str:
    content = _canonical_json(payload)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _resolve_search_space(
    *,
    scenario: Mapping[str, Any],
    plan: Mapping[str, Any],
    parameter_registry: Mapping[str, Any],
    parameter_claims: Mapping[str, Any],
    mode: str,
) -> ResolveResult:
    tuned_parameters = plan.get("tuned_parameters", [])
    if not isinstance(tuned_parameters, list) or not tuned_parameters:
        raise ValueError("optimization plan tuned_parameters must be non-empty")

    return resolve_search_space(
        scenario=scenario,
        parameter_registry=parameter_registry,
        parameter_claims=parameter_claims,
        mode=mode,
        candidate_ids=[str(item) for item in tuned_parameters],
    )


def _domain_verdict(repo_root: Path) -> Tuple[bool, Dict[str, Any]]:
    domain_result = run_parameter_domain_guard(
        repo_root=repo_root,
        parameter_registry_path=Path("parameters/registry/parameter_registry.v1.json"),
        parameter_claims_path=Path("parameters/registry/parameter_claims.v1.json"),
        scenario_path=Path("mission/BASELINE_SCENARIO_v1.json"),
        mission_script_path=Path("scripts/mission_baseline_check.py"),
        divergence_threshold=20.0,
    )
    return domain_result.get("status") == "PASS", domain_result


def _evaluate_once(context: RunContext, config: OptimizationConfig) -> OptimizationRunResult:
    if config.mode != "realistic":
        raise ValueError("Optimization Engine v1 supports only mode=realistic")

    scenario = _load_json(context.scenario_path)
    plan = _load_json(context.plan_path)
    parameter_registry = _load_json(context.parameter_registry_path)
    parameter_claims = _load_json(context.parameter_claims_path)

    plan_result = validate_optimization_plan(plan, parameter_registry, parameter_claims)
    if plan_result["status"] != "PASS":
        raise ValueError("optimization_guard failed: " + "; ".join(plan_result.get("errors", [])))

    search_space = _resolve_search_space(
        scenario=scenario,
        plan=plan,
        parameter_registry=parameter_registry,
        parameter_claims=parameter_claims,
        mode=config.mode,
    )

    optimization_result = run_optimization(
        repo_root=context.repo_root,
        baseline_scenario=scenario,
        search_space=search_space,
        config=config,
    )

    sample_results = optimization_result["sample_results"]
    pareto_frontier = pareto.pareto_frontier(sample_results)
    top_k = optimization_result["top_k"]

    best = top_k[0] if top_k else {}
    speculative_used = any(bool(item.get("speculative_parameters_used")) for item in sample_results)

    stable_payload = {
        "config": optimization_result["config"],
        "search_space": optimization_result["search_space"],
        "sample_results": sample_results,
        "pareto_frontier": pareto_frontier,
        "top_k": top_k,
        "constraint_violations": optimization_result["constraint_violations"],
        "best": {
            "core_probability": float(best.get("core_probability", 0.0)),
            "trust_weighted_score": float(best.get("trust_weighted_score", 0.0)),
            "risk_metric": float(best.get("risk_metric", 1.0)),
        },
    }

    domain_verified, domain_result = _domain_verdict(context.repo_root)

    payload = {
        **stable_payload,
        "domain_guard": domain_result,
        "speculative_used": speculative_used,
    }
    pack_hash = _compute_pack_hash(stable_payload)

    return OptimizationRunResult(
        payload=payload,
        pack_hash=pack_hash,
        domain_verified=domain_verified,
        speculative_used=speculative_used,
    )


def _negative_proof(
    *,
    context: RunContext,
    config: OptimizationConfig,
    base_hash: str,
) -> Dict[str, Any]:
    scenario = _load_json(context.scenario_path)
    plan = _load_json(context.plan_path)
    registry = _load_json(context.parameter_registry_path)
    claims = _load_json(context.parameter_claims_path)

    # 1) speculative parameter in optimization plan must fail
    speculative_plan = dict(plan)
    tuned = [str(item) for item in plan.get("tuned_parameters", [])]
    tuned.append("trajectory_model.non_physical_capture_bias")
    speculative_plan["tuned_parameters"] = tuned
    speculative_result = validate_optimization_plan(speculative_plan, registry, claims)
    speculative_rejected = speculative_result["status"] == "FAIL"

    # 2) D-grade realistic parameter must fail
    d_plan = dict(plan)
    d_registry = dict(registry)
    d_registry["parameters"] = [dict(item) for item in registry.get("parameters", [])]
    d_claims = dict(claims)
    d_claims["claims"] = [dict(item) for item in claims.get("claims", [])]

    tuned_realistic = str(plan.get("tuned_parameters", [""])[0])
    for claim in d_claims["claims"]:
        if claim.get("parameter_id") == tuned_realistic:
            claim["trust_grade"] = "D"
            claim["mode"] = "realistic"
            break
    d_result = validate_optimization_plan(d_plan, d_registry, d_claims)
    d_rejected = d_result["status"] == "FAIL"

    # 3/4) deterministic behavior from hash
    run_same = _evaluate_once(context, config)
    same_seed_match = run_same.pack_hash == base_hash

    different_seed_cfg = OptimizationConfig(
        mode=config.mode,
        samples=config.samples,
        seed=config.seed + 1,
        refine_top_k=config.refine_top_k,
        refine_steps=config.refine_steps,
    )
    run_diff = _evaluate_once(context, different_seed_cfg)
    different_seed_differs = run_diff.pack_hash != base_hash

    return {
        "speculative_parameter_rejected": speculative_rejected,
        "d_grade_parameter_rejected": d_rejected,
        "same_seed_identical_hash": same_seed_match,
        "different_seed_changes_hash": different_seed_differs,
        "base_hash": base_hash,
        "same_seed_hash": run_same.pack_hash,
        "different_seed_hash": run_diff.pack_hash,
        "verdict": "PASS"
        if speculative_rejected and d_rejected and same_seed_match and different_seed_differs
        else "FAIL",
    }


def _render_final_report(
    *,
    run_id: str,
    pack_hash: str,
    result: OptimizationRunResult,
    determinism: Mapping[str, Any],
    negative: Mapping[str, Any],
) -> str:
    best = result.payload.get("best", {})
    pareto_size = len(result.payload.get("pareto_frontier", []))
    return "\n".join(
        [
            "# Optimization Engine v1 Report",
            "",
            f"- run_id: `{run_id}`",
            f"- mode: `{result.payload['config']['mode']}`",
            f"- pack_hash: `{pack_hash}`",
            f"- best_core_probability: `{best.get('core_probability', 0.0):.12f}`",
            f"- best_trust_weighted_score: `{best.get('trust_weighted_score', 0.0):.12f}`",
            f"- pareto_size: `{pareto_size}`",
            f"- domain_verified: `{result.domain_verified}`",
            f"- speculative_used: `{result.speculative_used}`",
            f"- determinism_pass: `{determinism.get('verdict') == 'PASS'}`",
            f"- negative_proof_pass: `{negative.get('verdict') == 'PASS'}`",
        ]
    ) + "\n"


def execute_and_write(
    *,
    context: RunContext,
    config: OptimizationConfig,
    output_dir: Path,
    run_id: str,
    verify_deterministic: bool,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    run_result = _evaluate_once(context, config)

    stable_payload = {
        "config": run_result.payload["config"],
        "search_space": run_result.payload["search_space"],
        "sample_results": run_result.payload["sample_results"],
        "pareto_frontier": run_result.payload["pareto_frontier"],
        "top_k": run_result.payload["top_k"],
        "constraint_violations": run_result.payload["constraint_violations"],
        "best": run_result.payload["best"],
    }

    pack_hash = _compute_pack_hash(stable_payload)
    determinism = {
        "requested": verify_deterministic,
        "pack_hash": pack_hash,
        "same_seed_hash": None,
        "same_seed_match": None,
        "different_seed_hash": None,
        "different_seed_differs": None,
        "verdict": "SKIPPED",
    }

    if verify_deterministic:
        with tempfile.TemporaryDirectory() as _tmp:
            second = _evaluate_once(context, config)
            alt = _evaluate_once(
                context,
                OptimizationConfig(
                    mode=config.mode,
                    samples=config.samples,
                    seed=config.seed + 1,
                    refine_top_k=config.refine_top_k,
                    refine_steps=config.refine_steps,
                ),
            )

        determinism.update(
            {
                "same_seed_hash": second.pack_hash,
                "same_seed_match": second.pack_hash == pack_hash,
                "different_seed_hash": alt.pack_hash,
                "different_seed_differs": alt.pack_hash != pack_hash,
            }
        )
        determinism["verdict"] = (
            "PASS" if determinism["same_seed_match"] and determinism["different_seed_differs"] else "FAIL"
        )

    negative = _negative_proof(context=context, config=config, base_hash=pack_hash)

    best = run_result.payload.get("best", {})
    pareto_size = len(run_result.payload.get("pareto_frontier", []))

    meta = {
        "engine_version": "optimization-engine-v1",
        "mode": config.mode,
        "seed": config.seed,
        "samples": config.samples,
        "best_core_probability": float(best.get("core_probability", 0.0)),
        "trust_weighted_score": float(best.get("trust_weighted_score", 0.0)),
        "pareto_size": pareto_size,
        "domain_verified": run_result.domain_verified,
        "speculative_used": run_result.speculative_used,
        "pack_hash": pack_hash,
        "verdict": "PASS"
        if run_result.domain_verified
        and not run_result.speculative_used
        and determinism.get("verdict") in {"PASS", "SKIPPED"}
        and negative.get("verdict") == "PASS"
        else "FAIL",
    }

    _write_json(output_dir / "OPTIMIZATION_CONFIG.json", run_result.payload["config"])
    _write_json(output_dir / "SEARCH_SPACE_RESOLVED.json", run_result.payload["search_space"])
    _write_json(output_dir / "SAMPLE_RESULTS.json", {"items": run_result.payload["sample_results"]})
    _write_json(output_dir / "PARETO_FRONTIER.json", {"items": run_result.payload["pareto_frontier"]})
    _write_json(output_dir / "TOP_K_SOLUTIONS.json", {"items": run_result.payload["top_k"]})
    _write_json(output_dir / "CONSTRAINT_VIOLATIONS.json", run_result.payload["constraint_violations"])
    _write_json(output_dir / "DETERMINISM_CHECK.json", determinism)
    _write_json(output_dir / "meta.json", meta)

    (output_dir / "NEGATIVE_PROOF.md").write_text(
        "\n".join(
            [
                "# Negative Proof",
                "",
                f"- speculative parameter rejected: `{negative['speculative_parameter_rejected']}`",
                f"- D-grade parameter rejected: `{negative['d_grade_parameter_rejected']}`",
                f"- same seed identical hash: `{negative['same_seed_identical_hash']}`",
                f"- different seed changes hash: `{negative['different_seed_changes_hash']}`",
                f"- verdict: `{negative['verdict']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (output_dir / "FINAL_REPORT.md").write_text(
        _render_final_report(
            run_id=run_id,
            pack_hash=pack_hash,
            result=run_result,
            determinism=determinism,
            negative=negative,
        ),
        encoding="utf-8",
    )

    return {
        "run_id": run_id,
        "output_dir": str(output_dir),
        "best_core_probability": float(best.get("core_probability", 0.0)),
        "trust_weighted_score": float(best.get("trust_weighted_score", 0.0)),
        "pareto_size": pareto_size,
        "pack_hash": pack_hash,
        "determinism": determinism,
        "negative_proof": negative,
        "meta": meta,
        "required_files": list(REQUIRED_ARTIFACT_FILES),
    }
