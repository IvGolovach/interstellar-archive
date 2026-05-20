# CAPSULE_RISK_BUDGET_SPEC_v1

## 1. Intent

This spec defines the mission-facing contract for `artifacts/capsule_risk_budget.v1.json`.
The artifact converts capsule survivability rows into a deterministic Monte Carlo risk budget that exposes attack modes, uncertainty dimensions, dominant assumptions, and reviewer-readable survival bands.

The spec is intentionally conservative:

- no certification claim,
- no hardware qualification claim,
- no launch-readiness claim,
- no hidden target, flight-horizon, or capsule-profile defaults,
- no replacement of the mission-level `P_success` decomposition.

## 2. Contract Status

Status: authored contract for a generated artifact.

The expected generated artifact is `artifacts/capsule_risk_budget.v1.json`.
The expected builder is `scripts/build_capsule_risk_budget_artifact.py`.
The expected validator is `scripts/ci/capsule_risk_budget_validate.py`.

The artifact remains reduced-order and non-certifying.
It should be read as a deterministic review surface over the capsule survivability layer, not as empirical reliability evidence.

## 3. Required Top-Level Fields

| field | type | required | notes |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `capsule_risk_budget.v1`. |
| `generator` | string | yes | Expected builder path or stable builder id. |
| `source_artifact_ref` | string | yes | Must equal `artifacts/capsule_survivability_lab.v1.json`. |
| `source_artifact_sha256` | string | yes | Digest of the source survivability artifact used to build this artifact. |
| `sample_count` | integer | yes | Minimum `1000`; larger campaigns should keep deterministic seed metadata. |
| `seed` | integer | yes | Required for reproducibility. |
| `sampling_method` | string | yes | Example: deterministic Monte Carlo or deterministic latin-hypercube-style sampling. |
| `attack_modes` | object | yes | Contains `default_row_id` and a `modes` array with at least four physical/model stressor modes. |
| `uncertainty_dimensions` | array | yes | Sampled dimensions and their evidence class. |
| `risk_budgets` | array | yes | Per-row risk budget results; at least 100 rows for the v1 browser boundary. |
| `risk_budget_count` | integer | yes | Must equal the number of entries in `risk_budgets`. |
| `source_policy` | object | yes | How source-backed, proxy, and assumption-bound values are labeled. |
| `failure_modes` | array | yes | Explicit modeled and unmodeled failure modes. |
| `qualification_roadmap` | array | yes | Evidence needed to upgrade current priors. |
| `non_certification_notice` | boolean | yes | Must be `true`. |

## 4. Attack Mode Contract

Each `attack_modes.modes[]` entry must include:

| field | required | meaning |
| --- | --- | --- |
| `id` / `attack_mode_id` | yes | Stable id. |
| `label` | yes | Human-readable name. |
| `description` | yes | Physical or model stressor represented by the mode. |
| `multipliers` | yes | Deterministic stress multipliers used by the review mode. |
| `total_capsule_survival` | yes | Default-row median survival under that attack mode for quick review. |

Recommended mode ids:

- `nominal`
- `skeptical`
- `severe_dust`
- `media_decay`
- `radiation_stress`

Implementations may add more modes.
They must not remove the distinction between source-backed anchors, proxy extrapolations, and assumption-bound priors.

## 5. Uncertainty Dimension Contract

Each `uncertainty_dimensions[]` entry must include:

| field | required | meaning |
| --- | --- | --- |
| `id` | yes | Stable id used by rows and samples. |
| `label` | yes | Human-readable name. |
| `targets` | yes | Model paths affected by this dimension. |
| `provenance` | yes | `validated_source`, `proxy`, or `assumption`. |
| `distribution` | yes | Distribution family or deterministic sampling rule. |
| `source_ids` | yes | Source ids, docs, or assumption ids supporting the dimension. |

Required dimension families:

- target and flight-horizon selection,
- dust environment and large-particle tail,
- plasma/radiation environment,
- shield and geometry attenuation,
- material degradation over time,
- data-media integrity,
- model-form and mode-correlation uncertainty.

## 6. Risk Budget Row Contract

Each `risk_budgets[]` entry should be traceable to one capsule survivability row.
The v1 implementation publishes one nominal row for each Capsule Lab row and the full attack-mode set for the default 10 Myr reference claim row.

Required fields:

| field | required | meaning |
| --- | --- | --- |
| `row_id` | yes | Stable source capsule survivability row id. |
| `attack_mode_id` | yes | Attack mode used for the row. |
| `target_id` | yes | Target descriptor or stable target id. |
| `flight_years` | yes | Flight horizon used for the row. |
| `velocity_id` | yes | Velocity profile used by the source row. |
| `capsule_id` | yes | Capsule profile used by the source row. |
| `quantiles` | yes | `p01`, `p05`, `p50`, `p95`, `p99` capsule-only survival values. |
| `monte_carlo` | yes | UI-ready p05/p50/p95 interval summary. |
| `risk_budget` | yes | Status, median survival, loss probability, and p50 budget margin. |
| `survival_loss_by_driver` | yes | Driver shares that explain sampled loss pressure. |
| `top_uncertainty_drivers` | yes | Dominant sampled drivers for reviewer triage. |
| `failure_mode_contributions` | yes | Structure/media/coupled contribution shares. |
| `required_improvement` | yes | Required hazard-reduction estimate for p50 targets. |
| `qualification_roadmap` | yes | Driver-specific evidence upgrades needed for the row. |
| `evidence_needed` | yes | Driver-specific external evidence needed before stronger claims are allowed. |
| `evidence_gap_ids` | yes | Stable ids linking row gaps to the top-level qualification roadmap. |
| `acceptance_criteria` | yes | Review criteria that must be met or explicitly external-required. |
| `blocking_claims` | yes | Claims the row is not allowed to support. |

All probability-like fields must be finite numbers in `[0, 1]`.
Rows must not hide target, horizon, velocity, or capsule profile context.

## 7. Evidence and Source Policy

The artifact must maintain these evidence classes:

| class | artifact meaning |
| --- | --- |
| `source_backed` | Direct source or close reference environment supports the value. |
| `proxy` | A source-backed or heritage value is used with declared applicability limits. |
| `assumption_bound` | A bounded prior or reduced-order coefficient is used because direct evidence is absent. |
| `mixed` | The row or mode combines more than one class and must expose the mix. |

Rules:

1. Realistic rows must not depend on speculative or trust-`D` inputs.
2. Source-backed values must retain their source refs and applicability limits.
3. Proxy values must not be renamed as measured values.
4. Assumption-bound values must be visible in `dominant_assumptions`, `evidence_mix`, or `limit_flags` when material.
5. Any row with missing evidence or source refs must fail validation or carry a blocking limit flag.

## 8. Survival Number Semantics

`survival_p50` is the median output of the reduced-order sampled model.
It is not an observed success rate, warranty, qualification result, or empirical reliability estimate.

`survival_p05` and `survival_p95` describe uncertainty encoded by the artifact.
They do not prove that unknown unknowns, omitted correlations, or model-form error have been fully bounded.

The risk budget may explain capsule-side terms in:

```text
P_success = P_hit * P_survive * P_data_intact
```

It must not replace `P_hit`, target acquisition, correction-window modeling, launch feasibility, regulatory review, or operational readiness.

## 9. Validation Expectations

Validators should fail when:

- `schema_version` is not `capsule_risk_budget.v1`,
- `non_certification_notice` is not `true`,
- `source_artifact_ref` does not equal `artifacts/capsule_survivability_lab.v1.json`,
- `sample_count` is below `1000`,
- `attack_modes` has fewer than four entries,
- `risk_budgets` has fewer than 100 entries,
- `risk_budget_count` does not equal `len(risk_budgets)`,
- probability fields are outside `[0, 1]`,
- realistic rows depend on speculative or trust-`D` inputs,
- source-backed/proxy/assumption-bound labels are missing,
- dominant assumption or limit-flag fields are absent,
- row-level evidence gaps, acceptance criteria, or blocking claims are absent,
- builder output differs from the committed artifact,
- browser-facing data carries a different artifact path than `artifacts/capsule_risk_budget.v1.json`.

## 10. Failure Modes

The artifact should expose both modeled and unmodeled failure modes.

Modeled or partially modeled:

- dust and large-particle impact pressure,
- plasma/radiation exposure pressure,
- material degradation over selected horizon,
- data-media integrity loss,
- target/horizon/environment mismatch.

Unmodeled or not yet qualified:

- full multiphysics radiation and plasma transport,
- stack-level ballistic-limit validation at all relevant speeds and angles,
- bit-level archive decoding and ECC recovery,
- active repair, maintenance, telemetry recovery, or post-arrival verification,
- complete targetability, launch, legal, regulatory, or operational readiness.

## 11. One-PR Integration Rule

The risk-budget layer should be reviewed as one coherent update covering:

- architecture/governance doc,
- mission-facing spec,
- data/source notes,
- generated artifact builder,
- generated artifact,
- strict validator,
- browser dataset embedding if applicable,
- required-path registration,
- governance decision,
- final SHA-aligned changelog entry after commits exist.

Landing only docs without the artifact path, or landing the artifact without the non-certification docs, creates review drift.

## 12. Explicit Non-Goals

This spec does not provide:

- certified hardware survivability,
- complete materials qualification,
- full environment or radiation transport,
- validated archive-media recovery over Myr horizons,
- launch, navigation, regulatory, or operational approval,
- proof that a selected target can be reached within `flight_years`,
- proof that a single survival number should be interpreted without its evidence mix and uncertainty band.
