# Capsule Numeric Audit v1

This note is the capsule-specific numeric audit for the realistic mission layer.
It separates three things that were previously blurred together:

- source-backed heritage proxy numbers
- assumption-bound survivability priors
- permissive schema bounds used only for validation

## 1. Verified numeric corrections

### `capsule_model.mass_kg`
- Baseline value: `206 kg`
- Previous value removed: `200 kg`
- Status: source-backed heritage proxy (`trust_grade = B`)
- Basis: Genesis Sample Return Capsule overview reports `Entry Mass = 206 kg`
- Source: [Genesis Sample Return Capsule Overview](https://ntrs.nasa.gov/citations/20070014646)

### `capsule_model.frontal_area_m2`
- Baseline value: `1.81 m^2`
- Previous value removed: `0.95 m^2`
- Status: source-backed heritage proxy (`trust_grade = B`)
- Basis: Genesis overview reports `Diameter = 1.52 m`; v1 uses circular frontal reference area `pi * (1.52 / 2)^2 ≈ 1.81 m^2`
- Source: [Genesis Sample Return Capsule Overview](https://ntrs.nasa.gov/citations/20070014646)

The old pair `200 kg` + `0.95 m^2` mixed incompatible capsule heritage classes. For comparison, Stardust used a much smaller `0.8128 m` diameter with frontal reference area `0.51887 m^2`, not `0.95 m^2`.
- Cross-check source: [Aerodynamics of Stardust Sample Return Capsule](https://ntrs.nasa.gov/citations/20040105538)

## 2. Retained numbers with explicit uncertainty limits

### `capsule_model.shield_areal_density_kg_m2`
- Baseline value: `32 kg/m^2`
- Status: assumption-bound design prior (`trust_grade = C`)
- Why retained: used as a v1 shield sizing placeholder in DAG failure-surface logic
- Why not upgraded: no public stack-level mass closure or ballistic-limit calibration set was found for this exact number

### `capsule_model.data_media_survival_margin`
- Baseline value: `0.82`
- Realistic tuning envelope: `[0.4, 0.98]`
- Status: assumption-bound survivability prior (`trust_grade = C`)
- Why retained: it is a reduced-order media-integrity prior, not a directly measured persistence fraction

### `capsule_model.material_degradation_mu_1_per_year`
- Baseline value: `0.00022 1/year`
- Realistic tuning envelope: `[0.0001, 0.0004]`
- Status: bounded assumption with qualitative material-durability precedent (`trust_grade = C`)
- Why retained: Stardust post-flight material analysis supports qualitative durability precedent, but not a direct deep-time degradation rate measurement
- Source: [Optical Property Measurements on the Stardust Sample Return Capsule](https://ntrs.nasa.gov/citations/20070031961)

## 3. Removed overstated causal claims

These parameters are no longer tagged as direct `p_survival` / `p_data_intact` / `p_success` drivers in the realistic mission registry:

- `capsule_model.mass_kg`
- `capsule_model.frontal_area_m2`
- `capsule_model.shield_areal_density_kg_m2`

Reason:
- `mass_kg` and `frontal_area_m2` do not participate in the current reduced-order baseline formulas or DAG failure drivers.
- `shield_areal_density_kg_m2` is used in DAG shield-failure proxy logic, but not in the current baseline `p_success` formula.

## 4. Scope note on bounds

The schema bounds for `mass_kg`, `frontal_area_m2`, and `shield_areal_density_kg_m2` remain permissive validation bounds.
They should not be read as evidence-backed feasible design envelopes.

## 5. Still unresolved

The following capsule-adjacent numbers remain intentionally unresolved or only partially anchored:

- a public stack-level derivation for `32 kg/m^2`
- a direct public persistence experiment that maps to `data_media_survival_margin = 0.82`
- a material-specific long-horizon measurement that maps directly to `0.00022 1/year`

The previous exact `12-15 km/s` narrative anchor for shield validation was removed from the structured evidence layer because this audit did not find a clean primary-source basis for presenting that range as a validated capsule-specific numeric fact.

Until those are sourced, the repo should treat them as bounded v1 priors rather than validated hardware facts.
