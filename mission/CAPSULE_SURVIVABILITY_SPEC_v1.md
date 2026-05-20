# CAPSULE_SURVIVABILITY_SPEC_v1

## 1. Intent

This v1 spec defines the mission-facing contract for capsule design and deep-time survivability reasoning.
It extends the existing mission layer with explicit target and flight-horizon selection semantics and a deterministic generated artifact consumed by the web workspace.

The spec is intentionally conservative:

- no certification claim,
- no hardware qualification claim,
- no mission-readiness claim,
- no hidden target or flight-year defaults.

## 2. Contract Status

Status: authored contract plus generated artifact contract.

The current implementation registers this spec as a required mission contract document and validates `artifacts/capsule_survivability_lab.v1.json` through `scripts/ci/capsule_survivability_validate.py`.
The generated artifact remains reduced-order and non-certifying.

## 3. Required Inputs

A machine-readable capsule survivability run must declare the following top-level inputs.

| field | type | required | notes |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must be versioned, for example `capsule_survivability.v1`. |
| `mission_mode` | string | yes | Must preserve the existing `realistic` / `speculative` separation. |
| `selected_target` | object | yes | User-selected target descriptor. |
| `flight_years` | number | yes | User-selected design horizon in years. |
| `capsule_design` | object | yes | Capsule design profile and priors. |
| `environment_profile` | object | yes | Exposure envelope or reference to an existing mission environment profile. |
| `assumption_manifest` | array | yes | Human-readable and machine-readable assumption list. |
| `evidence_links` | array | yes | Source, claim, and trust references for surfaced inputs. |

`flight_years` must be greater than zero.
For the v1 generated artifact, `flight_years` is either computed from selected target distance and velocity or selected from a fixed horizon option.
It remains a declared design horizon rather than a validated operational envelope.

## 4. Selected Target Contract

`selected_target` must include:

| field | required | meaning |
| --- | --- | --- |
| `target_id` | yes | Stable symbolic id for the selected target or scenario. |
| `target_label` | yes | Human-readable label. |
| `target_class` | yes | Example classes: `schwarzschild_black_hole`, `stellar_remnant_proxy`, `scenario_proxy`. |
| `distance_from_earth_ly` | yes | Distance assumption used by mission reasoning. |
| `environment_profile_ref` | yes | Reference to the environmental assumptions used for survivability. |
| `source_policy` | yes | How target facts and assumptions are sourced. |

The selected target is not a proof of reachable targeting.
It identifies the scenario being evaluated.

## 5. Capsule Design Contract

`capsule_design` must expose the survivability-facing fields derived from `mission/capsule/capsule_design.v1.json`:

| field | required | evidence expectation |
| --- | --- | --- |
| `mass_kg` | yes | Source-backed heritage proxy or stronger. |
| `frontal_area_m2` | yes | Source-backed heritage proxy or stronger. |
| `shield_areal_density_kg_m2` | yes | Explicit prior until stack-level evidence exists. |
| `data_media_survival_margin` | yes | Explicit media-survivability prior. |
| `material_degradation_mu_1_per_year` | yes | Explicit deep-time degradation prior. |
| `geometry_model` | yes | Named modeling simplification. |
| `material_family` | yes | Qualitative material family, not a qualified bill of materials. |

The current v1 evidence split from `mission/CAPSULE_NUMERIC_AUDIT_v1.md` remains authoritative.
Mass and frontal area are Genesis-class heritage proxies.
Shield, media, and degradation values remain assumption-bound unless upgraded by a later evidence update.

## 6. Deep-Time Survivability Outputs

The generated report exposes, at minimum:

| field | meaning |
| --- | --- |
| `flight_years` | User-selected design horizon used for the result. |
| `selected_target` | Target descriptor used for the result. |
| `structureProbability` | Reduced-order shell/structure survival proxy over the selected horizon. |
| `dataIntegrityProbability` | Reduced-order physical-media integrity proxy over the selected horizon. |
| `survivalProbability` | Capsule-only aggregate p50 from deterministic uncertainty samples. |
| `survivalP05` / `survivalP95` | Uncertainty band around capsule-only aggregate. |
| `trust_summary` | Count and list of `A/B/C/D` input classes. |
| `dominant_assumptions` | Assumptions most responsible for result interpretation. |
| `limit_flags` | Machine-readable flags for missing evidence, proxy-only values, or speculative influence. |
| `non_certification_notice` | Required true/visible notice that this is not certification evidence. |

`survivalProbability` must not silently replace the existing mission success equation:

`P_success = P_hit * P_survive * P_data_intact`

The capsule layer may feed or explain `P_survive` and `P_data_intact`; it must not hide `P_hit`, targetability limits, or the fact that source-backed environment anchors and assumption-bound model coefficients are different evidence classes.

## 7. Evidence and Trust Rules

The layer uses the repository trust grades:

| grade | meaning in this layer |
| --- | --- |
| `A` | Direct evidence for the same quantity and context. |
| `B` | Strong heritage proxy with explicit applicability limits. |
| `C` | Bounded assumption, estimate, or reduced-order prior. |
| `D` | Speculative or non-physical control. |

Rules:

1. Realistic outputs must not depend on `D` inputs.
2. `B` heritage proxies must not be described as qualification evidence.
3. `C` assumptions must be visible in `dominant_assumptions` or `assumption_manifest` when they materially affect outputs.
4. Any missing evidence link must produce a `limit_flags` entry.
5. Public UI must render from generated artifact fields, not recompute capsule truth in the browser.

## 8. Required Assumption Manifest

The assumption manifest must include:

- target selection source and target class,
- user-selected `flight_years`,
- environment proxy boundaries,
- material degradation prior,
- data-media persistence prior,
- shield and geometry simplifications,
- whether any speculative mode inputs are present,
- statement that no repair, maintenance, telemetry recovery, or post-crossing verification is modeled.

## 9. Validation Expectations

Validators should fail when:

- `selected_target` is missing,
- `flight_years` is missing or non-positive,
- any surfaced input lacks an evidence or assumption link,
- realistic outputs depend on `D` inputs,
- `non_certification_notice` is missing,
- a generated artifact changes without its builder and validation flow,
- UI-side code computes capsule survivability values instead of rendering artifact data.

The v1 validator also requires at least 100 deterministic rows, a visible non-certification notice, valid control references, valid probabilities, a source index, and a default `reference-black-hole` arrival row near 10 Myr.

## 10. One-PR Integration Rule

The capsule survivability layer must be reviewed as one PR covering:

- architecture documentation,
- mission-facing spec,
- source-backed environment brief,
- capsule design data,
- survivability engine,
- generated artifact builder and validator,
- web Capsule Lab route,
- required-path registration,
- governance decision,
- final SHA-aligned changelog entry.

This keeps the public contract, validation manifest, and governance history synchronized.

## 11. Explicit Non-Goals

This spec does not provide:

- certified hardware survivability,
- complete materials qualification,
- full radiation or plasma transport,
- thermal soak and transient shock modeling,
- bit-level data recovery modeling,
- launch, navigation, regulatory, or operational approval,
- proof that a selected target can be reached within `flight_years`.
