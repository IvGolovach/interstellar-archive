# Objective Function Contract v1

## Purpose
This contract defines how mission runs are scored for comparison without running search or optimization. It gives a deterministic, auditable objective function surface so every future frontier/selection report can explain why one point is better than another.

## Modes
Scoring is mode-separated and never blended:
- `realistic`: policy-facing score domain.
- `speculative`: exploratory score domain.

The two modes are reported independently. No blended scalar score is published in v1.

## Primary Objective
Primary objective in both modes is:
- maximize `p_success`

`p_success` source is fixed to `/artifacts/p_success_defensibility.json`.

## Secondary Objectives and Aggregation
### Realistic
Secondary objective:
- `risk_envelope`

Formal definition in v1:
- `risk_envelope = 1 - Q_0.05(p_success_distribution)`
- distribution source: mission uncertainty model (`mission/BASELINE_SCENARIO_v1.json.uncertainty_model`)
- method contract: `mission/objectives/risk_envelope.v1.json`
- deterministic seed: fixed by risk contract (`deterministic_seed`)

Aggregation in realistic mode is strict Pareto over:
- maximize `p_success`
- minimize `risk_envelope`

No weighted sum is allowed in v1 realistic mode.

### Speculative
No secondary objectives in v1. Ranking key is lexicographic over `p_success` only.

## Constraints
### Hard constraints
- `no_D_grade_influence`: realistic scoring must not allow speculative/D-grade influence.
- `evidence_completeness_1.0`: realistic score is valid only when parameter evidence completeness is 1.0.

### Soft penalties
Not part of v1 contract score. Future versions can add penalties only via explicit contract bump.

## Trust-Weighting Policy
Trust-weighted score is not used as a ranking objective in v1. This avoids hidden weighting assumptions in public score ordering before dedicated calibration.

Forbidden in realistic v1 objective contract:
- direct optimization objective on trust `D` parameters,
- any blended score that can increase with speculative-only inputs.

## Non-goals
This score contract does not claim:
- global optimality,
- hardware feasibility certification,
- full economic optimization,
- high-fidelity risk quantification (v1 risk is quantile-based proxy).

It only defines deterministic scoring primitives for baseline comparison and future optimization protocols.
