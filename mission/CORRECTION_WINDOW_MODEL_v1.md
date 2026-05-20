# CORRECTION_WINDOW_MODEL_v1

## 1. Policy envelope

v1 allows mid-course correction only within finite interval:

- `start_year = 0`
- `end_year = 180`
- `max_duration_years = 180`

Hard policy cap in schema: `max_duration_years <= 2000`.

## 2. Actuation and delta-v budget

Baseline correction authority:
- `delta_v_budget_mps = 36 m/s`
- `actuation_model = deterministic_impulse`
- `specific_impulse_s = 3200 s`
- `actuator_efficiency = 0.68`

Effective correction capability is bounded and non-infinite by construction.

## 3. Power model

Baseline sustained correction power:
- `power_available_w = 180 W`

v1 does not model dynamic power subsystem degradation in time-series form, but power is finite and bounded in schema to avoid unphysical correction claims.

## 4. Guidance and execution uncertainty

- `guidance_sigma_rad = 2.5e-7 rad`
- `execution_sigma_fraction = 0.08`

Mapped to effective miss uncertainty contribution:

\[
\sigma_{corr} = \sqrt{(r\,\sigma_{guidance})^2 + (r\,\epsilon_{exec}\,10^{-3})^2}
\]

## 5. Distribution contract

Correction-related uncertainties represented as distributions:
- `correction_execution_sigma ~ lognormal(mu=-2.6, sigma=0.35)`
- `guidance_pointing_error ~ normal(mean=0, sigma=2.5e-7)`

## 6. Why this is physically bounded

The model prevents implicit infinite control by requiring simultaneous finite values for window duration, delta-v, actuation efficiency, and power. Any scenario outside these bounds must fail schema validation.
