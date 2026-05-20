# Capsule Design and Deep-Time Survivability Layer

This document defines the authored architecture boundary for a Capsule Design and Deep-Time Survivability Layer.
It is a contract layer over the existing mission, parameter, evidence, and artifact governance stack.
It does not certify a capsule, qualify hardware, or claim that a mission design is ready to fly.

## 1. Purpose

The layer exists to make capsule-design assumptions explicit before they influence public mission interpretation.
Its job is to bind a user-selected target and a user-selected flight horizon to:

- a declared capsule design profile,
- a declared environmental exposure envelope,
- a declared set of evidence and assumptions,
- deterministic outputs that remain labeled as reduced-order research artifacts.

The layer is useful only if readers can see where the numbers came from, which assumptions dominate the result, and where the current evidence is weak.

## 2. Scope

In scope for v1:

- capsule geometry, mass, shield, material-family, and data-media survivability assumptions,
- user-selected target metadata and generated `flight_years` rows,
- deep-time degradation and media-integrity proxy semantics,
- evidence/trust labeling for every surfaced design and survivability input,
- deterministic generated capsule survivability reports consumed by the web workspace.

Out of scope for v1:

- hardware qualification,
- mission certification,
- launch readiness,
- regulatory review,
- full multiphysics radiation, thermal, plasma, dust, and materials coupling,
- bit-level ECC and storage-format recovery modeling,
- claims that a selected target or flight horizon is operationally reachable.

## 3. User-Selected Target and Flight Horizon

The layer must treat target and time horizon as explicit user selections, not hidden defaults.
At minimum, a run or artifact that uses this layer must declare:

- `selected_target.target_id`
- `selected_target.target_label`
- `selected_target.target_class`
- `selected_target.distance_from_earth_ly`
- `selected_target.environment_profile_ref`
- `flight_years`

`flight_years` is a design horizon used for degradation and persistence assumptions.
It is not proof of arrival, not proof of navigation authority for that duration, and not proof that the selected target remains observationally or operationally stable over that duration.

## 4. Architecture

The layer is divided into four contracts.

### 4.1 Selection contract

The selection contract records the user-selected target and flight horizon.
It must be visible in any generated capsule survivability artifact and in any UI that renders the result.
Changing target or `flight_years` changes the interpretation of the output, even if capsule design inputs stay fixed.

### 4.2 Capsule design contract

The capsule design contract describes the physical design proxy used by the reduced-order model.
The v1 fields align with the existing mission capsule model:

- `capsule_model.mass_kg`
- `capsule_model.frontal_area_m2`
- `capsule_model.shield_areal_density_kg_m2`
- `capsule_model.data_media_survival_margin`
- `capsule_model.material_degradation_mu_1_per_year`
- `capsule_model.geometry_model`
- `capsule_model.material_family`

The current evidence boundary from `mission/CAPSULE_NUMERIC_AUDIT_v1.md` remains binding:
Genesis-class mass and frontal area are heritage proxies, while shield, media, and degradation values remain bounded priors unless stronger public evidence is added.

### 4.3 Survivability contract

The survivability contract describes how the design profile is interpreted over the selected horizon.
For v1, survivability remains a reduced-order proxy over:

- environment acceptance,
- material degradation,
- shield and geometry assumptions,
- physical media integrity,
- mission-mode separation.

The layer must not turn these proxies into a certification claim.
Outputs may support comparison, sensitivity inspection, and assumption audit.
They must not be described as hardware-qualified survival probabilities.

### 4.4 Evidence and trust contract

Every public design or survivability input must resolve to a trust class:

- `A`: direct, high-quality measurement or qualified dataset for the same quantity and context,
- `B`: strong heritage proxy or externally sourced parameter with clear applicability limits,
- `C`: bounded assumption, estimate, or reduced-order prior,
- `D`: speculative or non-physical control.

Realistic public outputs must not depend on `D` inputs.
`B` heritage values are still not qualification evidence for the new capsule design.
`C` values must remain visible as assumptions, not be normalized into quiet defaults.

## 5. Required Assumptions

A v1 capsule survivability artifact must expose the following assumptions:

- target selection is provided by the user or by an explicitly named scenario,
- `flight_years` is selected by the user and is used as a model horizon,
- environmental exposure is represented by bounded proxies rather than full field simulation,
- long-duration material degradation is reduced to a compact rate or prior,
- data integrity is a physical-media survivability proxy, not bit-level ECC recovery,
- no mid-flight repair, maintenance, telemetry recovery, or post-crossing observation is assumed,
- target and trajectory uncertainties are governed by the mission layer, not solved by the capsule layer.

If any assumption is missing, the artifact should be considered incomplete.

## 6. Artifact Integration

This layer is implemented as both an authored contract and a tracked generated artifact:

- `docs/CAPSULE_SURVIVABILITY_LAYER.md`
- `mission/CAPSULE_SURVIVABILITY_SPEC_v1.md`
- `docs/research/CAPSULE_ENVIRONMENT_DATA_BRIEF_v1.md`
- `mission/capsule/capsule_design.v1.json`
- `mission/survivability/engine.py`
- `scripts/build_capsule_survivability_artifact.py`
- `scripts/ci/capsule_survivability_validate.py`
- `artifacts/capsule_survivability_lab.v1.json`
- `web/src/pages/CapsuleLabRoute.tsx`
- `web/src/ui/capsule/*`
- required-path registration in `docs/required_paths.v1.json`
- governance decision record in `engineering/DECISIONS.md`

The generated artifact follows the repository artifact policy:

- generated only by a tracked script,
- validated by a strict CI gate,
- diff-gated against committed output,
- rendered by UI from artifact data only,
- never used as physical truth beyond its declared assumptions.

The v1 artifact contains 120 deterministic scenario rows: 3 targets, 5 velocity profiles, 4 time horizons, and 2 capsule profiles.
The default black-hole narrative row is `reference-black-hole` + `conditional-45` + `ballistic-arrival` + `baseline-stack`, which produces a flight horizon near 10.32 Myr.
Its probability output is capsule-only and reduced-order; it must be read with the row's p05/p50/p95 uncertainty band, source index, and non-certification notice.

## 7. Review Boundary

The capsule survivability layer should land as one PR.
The architecture doc, mission spec, source brief, capsule design data, generated artifact, web route, validators, required-path manifest, governance decision, and final changelog SHA alignment must be reviewed together.
Landing only one part of the contract would create drift between public documentation, required repository paths, and governance history.

## 8. Non-Certification Statement

This layer is not a certification system.
It does not prove that a capsule can be built, launched, guided, survive the selected flight horizon, preserve retrievable data, or operate near a selected target.
It only makes the assumptions and evidence chain explicit enough for deterministic review.
