# MISSION_FEASIBILITY_SCREEN_SPEC_v1

## 1. Intent

This spec defines the contract for `artifacts/mission_feasibility_screen.v1.json`.

The artifact turns target choice and flight duration into a deterministic review surface:

- target id and distance,
- velocity band and ballistic time of flight,
- black-hole horizon screen where applicable,
- source-backed local dust/gas sweep estimates,
- radiation/material hook status,
- Capsule Risk Budget linkage,
- cost/energy proxy and external evidence blockers.

It is not a launch architecture, procurement estimate, flight dynamics engine, hardware qualification result, or mission certification.

## 2. Required Top-Level Fields

| field | required | notes |
| --- | --- | --- |
| `schema_version` | yes | Must equal `mission_feasibility_screen.v1`. |
| `generator` | yes | Must equal `scripts/build_mission_feasibility_screen_artifact.py`. |
| `public_scope` | yes | Must equal `target_velocity_time_feasibility_screen`. |
| `non_certification_notice` | yes | Must be `true`. |
| `source_artifacts` | yes | SHA-256 refs for baseline, Capsule Lab, Capsule Risk Budget, and environment brief. |
| `constants` | yes | Physical constants and local dust/gas anchors used by the screen. |
| `target_count` | yes | Must be `3` for v1 Capsule Lab targets. |
| `velocity_count` | yes | Must be `5` for v1 Capsule Lab velocity bands. |
| `scenario_count` | yes | Must be `15`. |
| `scenario_rows` | yes | Exactly 15 target/velocity feasibility rows. |

## 3. Row Contract

Each `scenario_rows[]` entry must include:

- `target_id`, `distance_ly`, `velocity_id`, `velocity_km_s`, `flight_years`,
- `black_hole_screen`,
- `dust_screen`,
- `gas_screen`,
- `radiation_material_hooks`,
- `capsule_risk_budget_link`,
- `cost_energy_proxy`,
- `feasibility`,
- `external_evidence_gaps`,
- `blocked_claims`.

Rows must not hide target, velocity, or time horizon context.

## 4. Validation Rules

Validators must fail when:

- top-level schema, generator, scope, or non-certification fields drift,
- source artifact hashes are absent,
- scenario rows are not exactly `3 x 5`,
- the default `reference-black-hole` + `conditional-45` row is absent or not near `10 Myr`,
- any row lacks a nominal Capsule Risk Budget match,
- dust/gas/energy fields are not finite,
- black-hole rows do not expose horizon screening,
- evidence gaps or blocked public claims are absent.

## 5. Explicit Non-Goals

The v1 screen does not provide:

- numerical trajectory optimization,
- full GR or Kerr integration,
- MHD/accretion modeling,
- whole-path ISM mapping,
- validated mm/cm dust-tail flux,
- material-specific radiation transport,
- launch-provider feasibility,
- procurement pricing,
- flight readiness or certification.
