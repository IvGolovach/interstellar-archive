# Capsule Risk Budget Data Notes v1

Purpose: document which Capsule Risk Budget v2 inputs are source-backed, proxy-based, or assumption-bound before they are interpreted as Monte Carlo survival numbers.

This note does not add a new source model.
It maps the existing capsule environment and survivability evidence boundary into risk-budget review classes.
The primary local source brief remains `docs/research/CAPSULE_ENVIRONMENT_DATA_BRIEF_v1.md`.

## 1. Reading Rules

Risk-budget values should be read in this order:

1. Source-backed anchor: what is directly supported by a cited source or stable deterministic repo input?
2. Proxy mapping: where is that anchor being used outside its original context?
3. Assumption-bound prior: which coefficient or tail behavior is not directly sourced?
4. Survival number: what p05/p50/p95 band results from the current reduced-order model?

The survival number is the last item, not the first.

## 2. Evidence Classes Used By The Risk Budget

| class | meaning | reviewer action |
| --- | --- | --- |
| source-backed | A source directly supports the quantity or a close reference environment. | Check source applicability and units. |
| proxy | A source-backed or deterministic value is reused with declared limits. | Check whether the limit changes the conclusion. |
| assumption-bound | The value is a bounded prior, extrapolation, or reduced-order coefficient. | Treat as a sensitivity driver, not as qualification evidence. |
| mixed | Multiple evidence classes are combined in one mode or row. | Inspect the weakest material assumption before accepting the row. |

These classes are plain-language review labels.
They should remain compatible with the repository trust grades `A/B/C/D`.

## 3. Source-Backed Anchors

The following anchors are stable enough to reference in the risk-budget artifact, with the limits already stated in `docs/research/CAPSULE_ENVIRONMENT_DATA_BRIEF_v1.md`.

| topic | source-backed anchor | valid use in risk budget | invalid overclaim |
| --- | --- | --- | --- |
| local neutral hydrogen | Local heliosphere/VLISM neutral-H density from New Horizons/SWAP analysis. | Local cruise reference and order-of-magnitude gas context. | Whole-path average to arbitrary targets. |
| local plasma/electron density | Voyager plasma-wave order-of-magnitude interstellar plasma density near/just beyond heliopause. | Local plasma reference. | Black-hole or dense target-region plasma validation. |
| local interstellar dust | Ulysses/Galileo and Ulysses 16-year dust-density/flux context. | Local in-situ dust prior with factor-level uncertainty. | Universal Myr dust-tail distribution or mm/cm flux. |
| dust size regimes | MRN extinction-size reference plus Ulysses large-grain evidence. | Separate extinction-sized grains from impact-relevant large-grain tails. | Single universal dust distribution constant. |
| hypervelocity context | NASA HVIT lower-speed lab capability and ESA spacecraft-impact context. | Ground-test validation ceiling and impact-energy intuition. | Direct validation of all tens-of-km/s interstellar shield claims. |
| GCR/radiation references | NASA GCR model/standard references, RAD context, and stopping-power tools. | Model/source hooks for radiation-environment reasoning. | Direct Myr media-survival scalar. |
| target distance and time of flight | Scenario-owned target distances plus source-backed astronomical anchors where available. | Deterministic horizon calculation and scenario labeling. | Target reachability, navigation authority, or operational feasibility. |

## 4. Proxy Mappings

Proxy mappings are allowed only when the artifact keeps the mapping visible.

| proxy | why it is useful | required caveat |
| --- | --- | --- |
| local ISM gas and dust as cruise references | Gives a source-backed lower/contextual environment anchor. | Not a whole-path average and not a target-region model. |
| NASA/ESA impact context for shield reasoning | Gives tested speed/material context and impact-energy scaling. | Does not qualify the capsule stack at the modeled velocity, angle, projectile, or duration. |
| Genesis-class or heritage capsule values | Provides public heritage scale for mass/frontal area reasoning. | Heritage geometry or mass is not qualification evidence for this capsule. |
| `flight_years` from distance and velocity | Makes exposure horizon explicit and reproducible. | Does not prove arrival, targetability, or active control for that duration. |
| reduced-order attack-mode contribution | Helps reviewers see which stressor dominates the model. | Contribution share is model accounting, not physical root-cause proof. |

## 5. Assumption-Bound Inputs

These inputs should remain explicit assumptions until stronger evidence exists:

| input family | why it remains assumption-bound | evidence that would upgrade it |
| --- | --- | --- |
| mm/cm interstellar dust-tail frequency | Existing sources support local dust and large grains, not a mission-specific deep-time catastrophic tail. | Calibrated tail model using in-situ, astronomical, and uncertainty-tail evidence. |
| shield effectiveness at tens of km/s | Public lab validation context does not cover the exact stack over all relevant regimes. | Stack-level ballistic-limit tests plus hydrocode validation across material, angle, and velocity. |
| material degradation over Myr horizons | Current compact degradation priors are reduced-order placeholders. | Material-specific aging, thermal, radiation, erosion, and micrometeoroid evidence. |
| archive-media persistence | Current media margin is a physical-media proxy. | Direct media-stack persistence, radiation, thermal, and recovery testing. |
| attack-mode independence/correlation | Reduced-order sampling may simplify coupling between hazards. | Model-form validation and sensitivity studies that vary correlations. |
| target-region environment envelope | Current black-hole/proxy environment values are scenario-owned. | Target-state model tied to distance, accretion state, direction, and uncertainty propagation. |

## 6. Attack Mode Evidence Map

| attack mode | source-backed components | proxy components | assumption-bound components |
| --- | --- | --- | --- |
| `nominal` | Existing Capsule Lab source anchors. | Baseline v1 reduced-order row propagation. | Material/media priors remain assumption-bound. |
| `skeptical` | Same source anchors as nominal. | Conservative multiplier bundle for review. | Coupled pessimistic priors are not empirical failure rates. |
| `severe_dust` | Ulysses/Galileo dust context; NASA/ESA impact context. | Local dust as cruise prior; lab impact context as validation ceiling. | Catastrophic large-particle tail, shield response at modeled speed. |
| `media_decay` | Radiation/material source hooks where available. | Archive-media margin as data-integrity proxy. | Direct Myr media survival and full stack coupling. |
| `radiation_stress` | NASA GCR references, RAD context, stopping-power tools. | Reference-model data used as capsule context. | Direct media response over selected horizon. |

## 7. Monte Carlo Notes

The risk-budget Monte Carlo should be deterministic and reproducible.
At minimum, the artifact should declare:

- sample count,
- sampling seed,
- sampling method,
- source artifact reference and digest,
- uncertainty dimensions and bounds,
- per-row sample count if it differs from the top-level count,
- any mode-correlation or independence assumption.

Monte Carlo output should not be described as evidence by itself.
It is a propagation of current evidence and assumptions.
If weak assumptions dominate the sampled result, the row remains weak even when the median is high.

## 8. Failure Modes Outside Current Evidence

The following failure modes are not closed by the current evidence notes:

- complete multiphysics coupling between dust, plasma, radiation, thermal, and material response,
- coupled shock/fragment/radiation behavior of the exact shield and vault stack,
- bit-level archive decoding after physical media damage,
- long-term chemical, mechanical, and radiation aging of the exact media stack,
- target-region environmental bursts or state changes outside scenario envelopes,
- active guidance, correction, telemetry, recovery, or repair behavior,
- post-arrival verification that a capsule survived and data remained readable.

If a row appears strong while these limits dominate its assumptions, reviewers should treat the row as a prioritization signal only.

## 9. Upgrade Criteria

An input can move from assumption-bound toward proxy or source-backed only when the upgrade evidence is specific enough to bind the quantity being modeled.

Examples:

- A general radiation standard can support a radiation reference, but not direct archive-media persistence.
- A hypervelocity test facility range can support validation boundaries, but not exact shield effectiveness at every modeled impact speed.
- A target-distance source can support time-of-flight calculation, but not target reachability.
- A heritage mass value can support scale comparison, but not capsule qualification.

The v2 artifact should preserve these distinctions even when a UI or reviewer summary wants a compact survival number.
