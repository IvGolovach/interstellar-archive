# SENSITIVITY_PLAN_v1

## 1. Parameters most likely to move `P_success`

Highest expected leverage in v1:
1. `bh_parameters.periapsis_distance_m` (drives crossing margin and `P_hit`).
2. `trajectory_model.nav_position_sigma_m` and correction uncertainty terms (`guidance_sigma_rad`, `execution_sigma_fraction`).
3. `environment_model.radiative_flux_w_m2`, `plasma_density_proxy_m3`, `dust_flux_scale` (drive `P_survive`).
4. `capsule_model.data_media_survival_margin` and `material_degradation_mu_1_per_year` (drive `P_data_intact`).

## 2. Planned scan ranges

- `periapsis_distance_m`: `[0.9 r_s, 1.2 r_s]`
- `delta_v_budget_mps`: `[5, 120]`
- `guidance_sigma_rad`: `[1e-8, 1e-5]`
- `execution_sigma_fraction`: `[0.01, 0.25]`
- `radiative_flux_w_m2`: `[0.5, 1.5] * baseline`
- `dust_flux_scale`: `[0.6, 3.0]`
- `data_media_survival_margin`: `[0.4, 0.98]`

## 3. Planned experiments for ToR #2

1. Monte Carlo campaign (>=10000 samples) with uncertainty_model distributions.
2. Two-mode comparison (`realistic` vs `speculative`) with strict output labeling.
3. Correction-window policy sweep (duration, power, delta-v coupling) under fixed environment proxy.

## 4. Meaningful improvement criterion

A parameter set is considered meaningfully improved only if all are true:
- `delta(P_success) >= +0.05` absolute versus baseline.
- No degradation in environment acceptance (`environment_acceptable` remains true).
- Improvement remains >= `+0.03` under at least 80% of uncertainty samples in realistic mode.
