# PARAMETER_CATALOG_v1

Mission-level parameters are partitioned into strict domains (`realistic` / `speculative`).
`realistic` outputs must remain independent from `speculative` parameters.
This catalog is the public mission/design/environment parameter surface. Internal `code_literal.*` audit entries remain in the canonical registries but are intentionally excluded from this table and from browser-facing drilldown artifacts.

| name | unit | default | bounds | category | mode | domain | trust_grade | affects_core_probability | source type | evidence available? | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `bh_parameters.distance_from_earth_ly` | ly | `26000.0` | `[0.001, 1000000.0]` | safe | realistic | realistic | B | true | paper/report | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `bh_parameters.mass_kg` | kg | `8.55e+36` | `[1e+30, 1e+41]` | safe | realistic | realistic | B | true | paper/report | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `bh_parameters.max_dust_flux_scale` | scale | `3.0` | `[0.01, 100.0]` | safe | realistic | realistic | B | true | paper/report | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `bh_parameters.max_plasma_density_proxy_m3` | 1/m^3 | `80000000000.0` | `[1.0, 1e+20]` | safe | realistic | realistic | B | true | paper/report | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `bh_parameters.max_radiative_flux_w_m2` | W/m^2 | `20000000.0` | `[100.0, 1000000000.0]` | safe | realistic | realistic | B | true | paper/report | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `bh_parameters.periapsis_distance_m` | m | `12300000000.0` | `[1.0, 1000000000000000.0]` | safe | realistic | realistic | B | true | paper/report | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `capsule_model.data_media_survival_margin` | fraction | `0.82` | `[0.4, 0.98]` | advanced | realistic | realistic | C | true | assumption | yes | Assumption-bound media survivability prior; realistic tuning range matches the declared v1 sensitivity envelope. |
| `capsule_model.frontal_area_m2` | m^2 | `1.81` | `[0.01, 20.0]` | advanced | realistic | realistic | B | false | paper/assumption | yes | Genesis-class frontal reference area proxy derived from the published 1.52 m heritage diameter. |
| `capsule_model.mass_kg` | kg | `206.0` | `[50.0, 1000.0]` | safe | realistic | realistic | B | false | paper/assumption | yes | Genesis-class entry-mass proxy anchored to the published Genesis SRC overview. |
| `capsule_model.material_degradation_mu_1_per_year` | 1/year | `0.00022` | `[0.0001, 0.0004]` | advanced | realistic | realistic | C | true | paper/assumption | yes | Bounded degradation prior informed by returned-capsule durability precedent, but still treated as an assumption-constrained rate. |
| `capsule_model.shield_areal_density_kg_m2` | kg/m^2 | `32.0` | `[0.1, 500.0]` | advanced | realistic | realistic | C | false | assumption | yes | Assumption-bound shield sizing prior; not yet tied to a public stack-level mass closure or ballistic-limit calibration set. |
| `correction_window.actuator_efficiency` | fraction | `0.68` | `[0.01, 1.0]` | advanced | realistic | realistic | C | true | assumption | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `correction_window.delta_v_budget_mps` | m/s | `36.0` | `[0.0, 20000.0]` | advanced | realistic | realistic | C | true | assumption | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `correction_window.end_year` | year | `180.0` | `[0.0, 100000.0]` | advanced | realistic | realistic | C | true | assumption | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `correction_window.execution_sigma_fraction` | fraction | `0.08` | `[0.0, 1.0]` | advanced | realistic | realistic | C | true | assumption | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `correction_window.guidance_sigma_rad` | rad | `2.5e-07` | `[0.0, 0.1]` | advanced | realistic | realistic | C | true | assumption | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `correction_window.max_duration_years` | year | `180.0` | `[1.0, 2000.0]` | advanced | realistic | realistic | C | true | assumption | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `correction_window.power_available_w` | W | `180.0` | `[1.0, 1000000.0]` | advanced | realistic | realistic | C | true | assumption | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `correction_window.specific_impulse_s` | s | `3200.0` | `[1.0, 20000.0]` | advanced | realistic | realistic | C | true | assumption | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `correction_window.start_year` | year | `0.0` | `[0.0, 100000.0]` | safe | realistic | realistic | C | true | assumption | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `environment_model.accretion_luminosity_fraction` | fraction | `0.0025` | `[0.0, 1.0]` | advanced | realistic | realistic | C | true | estimate | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `environment_model.dust_flux_scale` | scale | `1.4` | `[0.0, 1000.0]` | advanced | realistic | realistic | C | true | estimate | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `environment_model.non_physical_safety_multiplier` | scale | `1.0` | `[0.1, 10.0]` | non_physical | speculative | speculative | D | true | design_choice | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `environment_model.plasma_density_proxy_m3` | 1/m^3 | `50000000000.0` | `[0.0, 1e+24]` | advanced | realistic | realistic | C | true | estimate | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `environment_model.radiative_flux_w_m2` | W/m^2 | `12000000.0` | `[0.0, 1000000000000.0]` | advanced | realistic | realistic | C | true | estimate | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `success_threshold` | fraction | `0.62` | `[0.0, 1.0]` | advanced | realistic | realistic | C | true | design_choice | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `trajectory_model.initial_state_sigma_m` | m | `1800000.0` | `[0.0, 1000000000.0]` | advanced | realistic | realistic | C | true | estimate | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `trajectory_model.integration_step_s` | s | `86400.0` | `[1.0, 31536000.0]` | advanced | realistic | realistic | C | true | estimate | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `trajectory_model.nav_position_sigma_m` | m | `1200000.0` | `[0.0, 1000000000.0]` | advanced | realistic | realistic | C | true | estimate | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `trajectory_model.nav_velocity_sigma_mps` | m/s | `0.08` | `[0.0, 100000.0]` | advanced | realistic | realistic | C | true | estimate | yes | Mission parameter tracked by schema+scenario literal inventory. |
| `trajectory_model.non_physical_capture_bias` | fraction | `0.0` | `[0.0, 1.0]` | non_physical | speculative | speculative | D | true | design_choice | yes | Mission parameter tracked by schema+scenario literal inventory. |

Domain policy:
- `trust_grade=D` parameters are always `domain=speculative`.
- `non_physical_*` parameters are always `domain=speculative`.
- `realistic` optimization is restricted to `domain=realistic` and non-`D` parameters.
- Notes that mention schema/scenario literal inventory refer to the source contracts that back these public parameters, not to internal code-literal audit entries.
