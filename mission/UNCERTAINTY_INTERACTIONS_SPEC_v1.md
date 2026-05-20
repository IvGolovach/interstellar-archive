# Uncertainty Interactions v1

`uncertainty_interactions.v1` is a deterministic review surface for roadmap item 8. It evaluates pairwise endpoint residuals across tracked mission uncertainty dimensions while keeping covariance and correlation evidence explicitly open.

This artifact is not a mission certification, a Sobol decomposition, or a validated probability interval. It answers a narrower question: under the current baseline model and declared uncertainty bounds, which parameter pairs produce non-additive `p_success` movement that reviewers should inspect first?

## Contract

- Source truth: `mission/UNCERTAINTY_MODEL_v1.json`, `mission/BASELINE_SCENARIO_v1.json`, `parameters/registry/parameter_claims.v1.json`, `mission/objectives/risk_envelope.v1.json`, `artifacts/parameter_sensitivity_summary.json`, and `artifacts/p_success_defensibility.json`.
- Mode: realistic only.
- Metric: `p_success`.
- Interaction definition: `interaction_residual = joint_endpoint_delta - sum(individual_endpoint_deltas)`.
- Stress policy: low/high endpoints come from declared uncertainty bounds.
- Correlation policy: correlation coefficients remain `null` with `external_correlation_evidence_required` until independent evidence exists.

## Non-Goals

- It does not close mission-level probability.
- It does not claim validated parameter independence.
- It does not replace external covariance, path-conditioned environment, or model-form validation work.
