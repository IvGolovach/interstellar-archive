# Mission Layer Summary

## 1. Executive Summary

1. Mission-definition v1 is formalized as a deterministic contract under `mission/MISSION_SCHEMA_v1.json`.
2. Horizon crossing is explicit: the crossing condition is `r <= r_s`, with Schwarzschild radius derived from black-hole mass.
3. Success is probability-based, not fixed-rate: `P_success = P_hit * P_survive * P_data_intact`.
4. Mission policy threshold is configurable through `success_threshold` in `[0, 1]`.
5. Realistic and speculative execution are separated through `mission_mode` and `speculative_overrides`.
6. The correction window is finite and bounded by duration, delta-v, power, and execution uncertainty.
7. Black-hole environment admissibility is implemented as a checkable filter (`strict|proxy`).
8. Uncertainties are distribution-defined with numeric parameters.
9. CI validates mission schema/scenario integrity and deterministic baseline behavior.
10. Capsule design and deep-time survivability are now a separate artifact-backed layer, not hidden inside the baseline `P_survive` proxy.
11. The mission layer does not require `sim/**` or web golden checksum changes.

## 2. Mission Definition

- Intent and constraints: `mission/MISSION_SPEC_v1.md`
- Machine contract: `mission/MISSION_SCHEMA_v1.json`
- Baseline scenario: `mission/BASELINE_SCENARIO_v1.json`

Core fields:

- `schema_version`
- `mission_mode`
- `success_threshold`
- `bh_model`
- `environment_acceptance_mode`
- `bh_parameters`
- `trajectory_model`
- `correction_window`
- `capsule_model`
- `environment_model`

## 3. Success Metric

Defined in `mission/SUCCESS_METRIC_v1.md`:

`P_success = P_hit * P_survive * P_data_intact`

Where:

- `P_hit`: crossing geometry plus uncertainty (`d_miss`, `sigma_eff`)
- `P_survive`: environment hazard and degradation proxy
- `P_data_intact`: physical media integrity proxy, not bit-level ECC

Decision rule:

- `success = (P_success >= success_threshold)`

## 4. Realistic and Speculative Separation

Guaranteed by schema and validator:

- `mission_mode` is one of `realistic` or `speculative`
- `speculative_overrides` is explicit and mode-gated
- realistic mode forbids speculative overrides
- parameter tags encode `mode` and `category` (`safe|advanced|non_physical`)

See:

- `mission/MISSION_SCHEMA_v1.json`
- `mission/PARAMETER_CATALOG_v1.md`

## 5. Correction Window Model

Defined in `mission/CORRECTION_WINDOW_MODEL_v1.md`:

- bounded interval `[start_year, end_year]`
- bounded `delta_v_budget_mps`
- finite `power_available_w`
- actuation and execution uncertainty (`guidance_sigma_rad`, `execution_sigma_fraction`)
- policy cap `max_duration_years <= 2000`

## 6. Black-Hole Environment Filter

Defined in `mission/BLACK_HOLE_ENV_FILTER_v1.md`.

Proxy predicate:

- `is_bh_environment_acceptable(params) -> bool`

Uses bounded ratios for radiative flux, plasma density proxy, and dust scale.

Known limitation in v1:

- scalar proxy thresholds, not full MHD or radiative-transfer coupling

## 7. Most Assumption-Heavy Parameters

Detailed public parameter catalog: `mission/PARAMETER_CATALOG_v1.md`
Capsule-specific numeric audit: `mission/CAPSULE_NUMERIC_AUDIT_v1.md`

Explicitly weaker or placeholder-heavy areas:

- `capsule_model.shield_areal_density_kg_m2`
- `capsule_model.data_media_survival_margin`
- `capsule_model.material_degradation_mu_1_per_year`
- `max_plasma_density_proxy_m3`
- `material_family`
- `non_physical_capture_bias`
- `non_physical_safety_multiplier`

## 8. Uncertainties and Distributions

Defined in `mission/UNCERTAINTY_MODEL_v1.md` and embedded in `mission/BASELINE_SCENARIO_v1.json`:

- navigation state: normal
- correction execution: lognormal
- dust variability: triangular
- degradation rate: uniform

## 8.1 Capsule Survivability Layer

Defined in:

- `docs/CAPSULE_SURVIVABILITY_LAYER.md`
- `mission/CAPSULE_SURVIVABILITY_SPEC_v1.md`
- `mission/capsule/capsule_design.v1.json`
- `artifacts/capsule_survivability_lab.v1.json`

The capsule layer exposes:

- capsule material stack and mass closure,
- target, velocity, and time-horizon controls,
- source-backed environment anchors,
- assumption-bound model coefficients,
- p05/p50/p95 capsule-only survival rows,
- a required non-certification notice.

The browser Capsule Lab renders committed artifact rows only; it does not recompute survivability in UI code.

## 9. Defined vs Placeholder Components

Defined in v1:

- crossing condition
- success equation
- environment acceptance predicate
- mission mode separation constraints
- deterministic baseline-check output structure

Placeholder or proxy components:

- plasma density proxy threshold physics
- compact survivability surrogate coefficients
- high-level material family descriptor
- capsule shield effectiveness, media persistence, and deep-time material hazard coefficients

## 10. Next Technical Work

1. Add a Monte Carlo engine that produces confidence intervals for `P_success` and its decomposition terms.
2. Replace the proxy environment filter with a radial profile plus thermal-dose integral model.
3. Add a correction-window optimization study over `P_success`, power, delta-v, and mass.
