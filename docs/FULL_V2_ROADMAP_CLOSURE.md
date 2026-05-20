# Full V2 Roadmap Closure

This document defines how the repository closes the 15 long-running roadmap items after Capsule Risk Budget v2.
The closure is repository-native: contracts, generated artifacts, deterministic summaries, validators, UI summaries, and governance.
It is not a claim that external hardware, launch, regulatory, procurement, or physical qualification has been completed.

## What Changed

The new closure layer makes each roadmap item reviewable as a row in `artifacts/roadmap_closure.v1.json`.
Roadmap item 7 is now backed by `artifacts/mission_probability_coupling.v1.json`, which factors selected mission probability into open external factors plus a capsule/data review proxy.
Roadmap item 8 is now backed by `artifacts/uncertainty_interactions.v1.json`, which exposes pairwise uncertainty residuals while keeping covariance and correlation evidence open.
Roadmap item 9 is now backed by `artifacts/evidence_upgrade_campaign.v1.json`, which ranks source-review work while keeping trust promotion and source correctness unclaimed.
Roadmap item 10 is now backed by `artifacts/optimization_v2_frontier.v1.json`, which adds four-axis Pareto screening while keeping optimum, procurement, and qualification claims blocked.
Roadmap item 11 is now backed by `artifacts/mission_dag_v2_boundary.v1.json`, which maps every DAG module to v1 wrapper support, v2 trace requirements, failure taxonomy coverage, and open independent-backend evidence gaps.
Roadmap item 12 is now backed by `artifacts/runtime_scenario_generation.v1.json`, which exposes local run recipes, compiled-scenario deltas, expected pack files, strict pack validation, and user-owned-run boundaries without claiming remote execution or a persistent reviewed archive.
Roadmap item 13 is now backed by `artifacts/cost_procurement_architecture_feasibility.v1.json`, which exposes proxy cost pressure, procurement gates, architecture rows, and blocked budget/launch/flight-readiness claims without claiming vendor quotes or procurement-grade estimates.
Roadmap item 14 is now backed by `artifacts/external_validation_review_pack.v1.json`, which exposes independent-review cases, required external deliverables, and blocked third-party-validation/reproduction claims without claiming external validation has been completed.
Roadmap item 15 is now backed by `artifacts/public_narrative_hardening.v1.json`, which exposes blocked public claims, required qualifiers, replacement guidance, and browser-rendering boundaries without claiming external wording audit, audience testing, legal review, or public claim approval has been completed.
Each row records:

- the implemented repository surface,
- the validation commands that enforce it,
- the deterministic model or contract summary,
- remaining external evidence gaps,
- the non-certification boundary.

This prevents the roadmap from becoming a narrative promise without machine-checkable follow-through.

## The 15 Closure Items

1. Mission Physics v2 screening layer
2. Target trajectory and reachability engine
3. Capsule qualification evidence stack
4. Archive media and bit-level recoverability
5. Interstellar dust-tail model
6. Radiation and material transport hooks
7. Full mission-level probabilistic coupling
8. Uncertainty v2 interactions
9. Evidence upgrade campaign
10. Optimization v2
11. Mission DAG v2 physics module boundary
12. Runtime scenario generation and user-owned runs
13. Cost, procurement, and architecture feasibility
14. External validation and independent review pack
15. Public narrative hardening

## Reading Rule

An item marked `repo_native_closure_implemented_external_evidence_open` means the repository now carries a deterministic contract, generated artifact, validator, and review boundary.
It does not mean the external evidence gap is closed.
For example, the capsule qualification item is implemented as a qualification-gap ledger and review gate, not as a completed ballistic-test campaign.

## Why This Is Useful

The project already has strong determinism and governance, but its hardest unresolved work is about replacing proxy confidence with better physics and better evidence.
The closure artifact keeps both facts visible:

- the repository has a concrete implementation surface for every roadmap item,
- the serious external evidence still required is not hidden.

## Validation

Canonical checks:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_roadmap_closure_artifact.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_external_validation_review_pack_artifact.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/ci/external_validation_review_pack_validate.py --strict
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_public_narrative_hardening_artifact.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/ci/public_narrative_hardening_validate.py --strict
PYTHONDONTWRITEBYTECODE=1 python3 scripts/ci/roadmap_closure_validate.py --strict
GIT_CONFIG_GLOBAL=/dev/null PYTHONDONTWRITEBYTECODE=1 python3 scripts/ci/check_suite.py
```

The browser renders the committed artifact summary only.
It must not recompute roadmap closure status in React.

## Non-Certification Boundary

The closure layer must not be described as certified, qualified, proven flight-ready, procurement-grade, or operationally approved.
Acceptable language:

- deterministic repository artifact,
- reduced-order screening model,
- qualification-gap ledger,
- non-certifying review contract,
- external evidence still required.
