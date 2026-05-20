# Optimization Protocol v1

## Scope
Optimization Engine v1 is a deterministic, realistic-domain optimizer for mission baseline parameters that affect `core_probability`.

## Why realistic-only
- Policy-facing optimization must be insulated from speculative and non-physical controls.
- Search-space resolution rejects any parameter with `domain != realistic`.
- Domain enforcement is machine-checked through `parameter_domain_guard` and `optimization_guard`.

## Why D-grade excluded
- Trust grade `D` represents speculative-only assumptions.
- V1 optimizer rejects trust `D` parameters before sampling.
- This prevents high-scoring but low-credibility solutions from entering ranked outputs.

## Why deterministic
- Identical `(scenario, search space, constraints, seed)` must produce identical artifacts.
- Deterministic checks compare artifact-pack SHA under same seed and require seed-shift hash divergence.
- Determinism is required for auditability and CI regression detection.

## Pareto meaning in v1
Pareto frontier is computed over:
1. maximize `core_probability`
2. maximize `trust_weighted_score`
3. minimize `risk_metric`

A candidate is non-dominated if no other feasible candidate is better-or-equal on all three objectives and strictly better on at least one.

## What v1 does not claim
- It is not a global optimizer for all mission parameters.
- It does not model full GR trajectory dynamics.
- It does not certify mission feasibility.
- It does not treat trust scores as posterior probabilities.
- It does not include speculative-mode optimization.
