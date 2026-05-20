# Assumption Ledger

This ledger records explicit assumptions used across the whitepaper and model notebooks.

| ID | Assumption | Rationale | Confidence | Impacted Artifacts |
| --- | --- | --- | --- | --- |
| A-001 | Encounter frequency follows a Poisson process over long horizons. | Simplifies arrival modeling; baseline for Monte Carlo. | Medium | `appendix/models/monte_carlo.ipynb` |
| A-002 | Relative velocity distribution can be approximated as log-normal. | Captures skew toward higher velocities in sparse data. | Low | `appendix/models/uncertainty_growth.ipynb` |
| A-003 | Detection horizon scales with inverse-square signal decay. | Standard proxy for sensitivity. | High | `appendix/models/encounter_geometry.ipynb` |
| A-004 | Observation windows are independent across survey campaigns. | Keeps uncertainty growth additive. | Medium | `appendix/models/uncertainty_growth.ipynb` |

## Quantitative Proof-Pack Assumptions

The machine-auditable registry for all quantitative assumptions lives in:

- `evidence/assumptions.json`

Additional IDs currently used by the proof pipeline:

| ID | Assumption (short form) | Confidence |
| --- | --- | --- |
| A-101 | Solar constant fixed at 1361 W/m^2 for envelope checks. | High |
| A-102 | Compact-object reference mass fixed at 10 M_sun. | High |
| A-103 | Two-body heliocentric energy closure for first-order Oberth checks. | Medium |
| A-104 | Perihelion burn modeled as impulsive prograde delta-v. | Medium |
| A-105 | Baseline near-parabolic inbound case uses v_infinity,in ~ 0. | Medium |
| A-106 | Conditional high-speed envelope uses inbound v_infinity,in in 10-30 km/s range. | Low |
| A-107 | Transverse leverage uses small-angle linearized geometry. | High |
| A-108 | Distance anchor fixed at 1560 ly for scale checks. | Medium |
| A-109 | RTG decay uses Pu-238 half-life 87.7 years (radioactive decay only). | High |
| A-110 | Cost classes are order-of-magnitude anchors pending full WBS closure. | Low |
| A-111 | Hypervelocity validation remains facility-limited; higher-speed cases are explicit extrapolation risk. | Medium |

## Notes
- Confidence levels: **Low / Medium / High** (subjective, update as evidence grows).
- Add new assumptions with a unique ID and link them to affected models.
- For quantitative claims, update `evidence/assumptions.json` and rerun `scripts/run_evidence_checks.sh`.
