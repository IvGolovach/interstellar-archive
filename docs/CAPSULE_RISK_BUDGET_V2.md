# Capsule Risk Budget v2

This document defines the governance and reviewer interpretation boundary for the Capsule Risk Budget v2 step.
It extends the capsule survivability layer with a deterministic Monte Carlo risk-budget artifact.
It does not certify capsule hardware, qualify materials, validate launch readiness, or prove that any selected target can be reached.

## 1. Purpose

Capsule survivability v1 exposes deterministic rows for target, flight horizon, velocity profile, and capsule profile.
Risk Budget v2 explains how those survival rows should be stress-read:

- which physical stressor modes dominate the survival number,
- which uncertainty dimensions were sampled,
- which inputs are source-backed, proxy-based, or assumption-bound,
- which failure modes remain outside the reduced-order model,
- how reviewers should interpret p05/p50/p95 survival outputs without overclaiming.

The risk budget is a review aid.
It is not a high-fidelity probabilistic risk assessment and it is not an empirical survival-rate measurement.

## 2. Artifact Boundary

The v2 contract is expected to be represented by:

- authored architecture/governance doc: `docs/CAPSULE_RISK_BUDGET_V2.md`,
- mission-facing spec: `mission/CAPSULE_RISK_BUDGET_SPEC_v1.md`,
- source and proxy notes: `docs/research/CAPSULE_RISK_BUDGET_DATA_NOTES_v1.md`,
- generated artifact: `artifacts/capsule_risk_budget.v1.json`,
- builder: `scripts/build_capsule_risk_budget_artifact.py`,
- validator: `scripts/ci/capsule_risk_budget_validate.py`,
- required-path registration in `docs/required_paths.v1.json`,
- governance decision in `engineering/DECISIONS.md`.

The generated artifact should be built from tracked inputs.
The browser-facing dataset may embed it, but UI code must render committed artifact fields rather than recomputing risk budgets in the browser.

Known minimum integration constraints from the browser-dataset boundary:

- `schema_version` is `capsule_risk_budget.v1`,
- `non_certification_notice` is `true`,
- `source_artifact_ref` points to `artifacts/capsule_survivability_lab.v1.json`,
- `sample_count` is at least `1000`,
- `attack_modes` contains at least four modes,
- `risk_budgets` contains at least 100 rows,
- `source_policy`, `failure_modes`, and top-level `qualification_roadmap` are present,
- each row keeps external `evidence_needed`, `evidence_gap_ids`, `acceptance_criteria`, and `blocking_claims` visible.

The v2 browser artifact keeps the payload compact by publishing a nominal risk budget for every Capsule Lab row and the full attack-mode set for the default 10 Myr black-hole claim row.
Future versions can expand full attack-mode coverage to every row if reviewers need that interaction more than they need a small browser bundle.

## 3. What "Attack Mode" Means Here

In this context, "attack mode" means a physical or model stressor that attacks the survival margin.
It is not a cybersecurity attacker model.

The v2 artifact should expose at least these mode families:

| attack mode | interpretation | current evidence status |
| --- | --- | --- |
| `nominal` | Baseline propagation of the committed Capsule Lab row. | Mixed: source-backed anchors plus proxy and assumption-bound priors. |
| `skeptical` | Broad conservative stress across material, media, dust, radiation, and exposure terms. | Mostly proxy/assumption-bound; useful for attacking optimistic priors. |
| `severe_dust` | Dust-tail, velocity-coupling, and shield extrapolation stress case. | Mixed: local dust anchors plus assumption-bound catastrophic tail and shield response. |
| `media_decay` | Archive-media persistence and material degradation stress case. | Mostly assumption-bound until media-stack aging evidence exists. |
| `radiation_stress` | Radiation and plasma-coupled data integrity stress case. | Mixed: radiation/plasma references plus assumption-bound media response. |

Implementations may split these modes further, but must preserve the source/proxy/assumption distinction.

## 4. Uncertainty Dimensions

Monte Carlo sampling is useful only if readers can see what was sampled and what was not.
The artifact should declare the uncertainty dimensions used for each risk budget row.

Expected dimensions:

| dimension | examples | interpretation boundary |
| --- | --- | --- |
| target and horizon | `target_id`, distance, velocity profile, `flight_years` | Derived from selected scenario inputs. Does not prove reachability or navigation authority. |
| dust environment | dust flux scale, large-grain tail, relative impact speed | Source-backed local anchors plus assumption-bound tail extrapolation. |
| plasma/radiation environment | plasma proxy, charged-particle exposure, GCR model reference | Local source anchors are not universal path averages or target-region validation. |
| shield and geometry | areal density, stand-off geometry, impact attenuation prior | Reduced-order design proxies, not stack-qualified ballistic-limit evidence. |
| material aging | degradation rate or hazard coefficient over flight horizon | Assumption-bound until material-specific long-duration evidence exists. |
| data-media integrity | media survival margin, redundancy interpretation, radiation/thermal exposure coupling | Physical-media persistence proxy, not bit-level ECC recovery or post-arrival readability proof. |
| model-form uncertainty | mode coupling, independence assumptions, sampling seed, row aggregation rule | Governance metadata, not physical evidence. |

The model should not treat all dimensions as equally evidenced.
A narrow p05/p95 band from narrow priors can still be weak if the priors are assumption-bound.

## 5. How To Read Survival Numbers

Reviewers should read each survival number as an artifact-scoped model output, not as a capsule survival certificate.

Required reading order:

1. Identify the row: selected target, velocity profile, flight horizon, capsule profile, mission mode, and source artifact reference.
2. Check the evidence mix: which values are source-backed, which are heritage proxies, and which are assumption-bound.
3. Read p05, p50, and p95 together. The p50 value is the median of the sampled reduced-order model, not an observed success rate.
4. Inspect attack-mode contributions and dominant assumptions before comparing two rows.
5. Treat wide bands, low p05 values, or assumption-dominated modes as qualification gaps, even if p50 is high.
6. Do not compare rows across different `flight_years`, targets, or velocity profiles without calling out that the exposure horizon changed.
7. Do not replace mission success with capsule survival. The mission decomposition still requires:

```text
P_success = P_hit * P_survive * P_data_intact
```

The capsule risk budget can explain `P_survive` and `P_data_intact`.
It does not solve `P_hit`, target acquisition, launch feasibility, regulatory approval, or operational safety.

## 6. Source-Backed, Proxy, and Assumption-Bound Inputs

The v2 review boundary uses three plain-language classes in addition to the repository's A/B/C/D trust grades:

| class | meaning | examples in this layer |
| --- | --- | --- |
| source-backed | A cited source directly supports the quantity or a close reference environment. | Local ISM hydrogen/plasma anchors, Ulysses dust-density anchor, NASA/ESA hypervelocity context, target-distance anchors. |
| proxy | A sourced or deterministic value is used outside its exact original context with explicit limits. | Genesis-class heritage mass/frontal area, local ISM anchors used as cruise references, NASA HVIT velocity range used as validation ceiling context. |
| assumption-bound | A value is a bounded prior or reduced-order coefficient because direct evidence for the mission context is absent. | Deep-time material degradation rate, archive-media Myr persistence, shield effectiveness at tens of km/s, mm/cm dust-tail frequency. |

Public text should not collapse these classes into a single "measured" or "validated" label.
Assumption-bound values may be useful for ranking and sensitivity, but they remain weak evidence for qualification.

## 7. Failure Modes To Keep Visible

The v2 artifact and docs should keep these failure modes explicit:

- physical penetration or spall from dust/large-particle impacts,
- cumulative erosion or material property drift over the selected horizon,
- radiation, displacement damage, or single-event effects that degrade archive media,
- thermal load or thermal-cycling damage outside the reduced-order envelope,
- target-region plasma or dust conditions exceeding the assumed environment profile,
- data media remains physically intact but is not readable, indexed, or recoverable,
- selected target or trajectory does not remain valid for the modeled horizon,
- missing evidence links, trust-grade drift, or speculative input leakage,
- UI or downstream consumers recompute values outside the artifact contract,
- Monte Carlo priors are too narrow, correlated incorrectly, or missing important unknowns.

The risk budget is useful when these failure modes are visible.
It becomes misleading if it hides them behind a single polished survival score.

## 8. Qualification Roadmap

The v2 step is documentation and deterministic artifact governance.
It is not qualification.

Evidence that would reduce uncertainty:

1. Publish the deterministic builder and validator with a fixed seed/sample manifest and stable schema.
2. Add source-to-parameter coverage for every sampled uncertainty dimension.
3. Replace target-region environment proxies with direction, distance, and target-state models where public evidence supports them.
4. Add ballistic-limit or hydrocode validation for the shield stack across angle, material, projectile, and velocity regimes.
5. Add material-specific radiation, thermal, and aging models with source-backed coefficients.
6. Add archive-media persistence tests or credible accelerated-aging evidence tied to the proposed media stack.
7. Couple capsule survival with the mission-level targeting and correction model without hiding `P_hit`.
8. Run independent review cases that try to break optimistic priors, not only confirm baseline rows.

Even after these steps, certification would require a separate hardware, safety, regulatory, and operational qualification process outside this repository.

## 9. Reviewer Checklist

Before accepting a risk-budget update, reviewers should confirm:

- the artifact is generated by `scripts/build_capsule_risk_budget_artifact.py`,
- `scripts/ci/capsule_risk_budget_validate.py` rejects missing notices, invalid probabilities, and missing evidence/proxy labels,
- every public row has visible source/proxy/assumption labels,
- realistic rows do not depend on speculative or trust-`D` inputs,
- survival numbers remain tied to their target, horizon, and capsule profile,
- the browser dataset embeds the committed artifact rather than recomputing risk values,
- docs and required paths land with the artifact, builder, validator, and governance decision,
- public language does not describe the result as certified, qualified, proven, or flight-ready.

## 10. Non-Certification Statement

Capsule Risk Budget v2 is a deterministic research artifact and review contract.
It does not prove that a capsule can be built, launched, guided, protected, recovered, decoded, certified, or operated for a selected target or flight horizon.
It only makes the current survival-number interpretation more auditable by exposing the sampled uncertainties, attack modes, and evidence boundaries.
