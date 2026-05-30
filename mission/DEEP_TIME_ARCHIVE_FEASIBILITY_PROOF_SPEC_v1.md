# Deep-Time Archive Feasibility Proof Spec v1

## Scope

`artifacts/deep_time_archive_feasibility.v1.json` is the integrated review artifact for the passive archive thesis.
It combines the reference target corridor, encounter geometry, capsule architecture, dust and particle hazards, data-medium readability, architecture modes, Sun-Oberth gate, and probability decomposition.

## Required Semantics

- `non_certification_notice` must be `true`.
- The artifact must use Gaia BH1 only as a reference 1560 ly catalog corridor unless a future dynamic worldline model is attached.
- `Archive-only` and `Flagship-Full` modes must remain separate.
- Baseline `23-34 km/s` Sun-Oberth rows must use zero inbound excess speed.
- Conditional `35-45 km/s` rows must declare the positive inbound-energy assumption.
- Case A horizon or capture rows must be marked not operationally controllable.
- The dust model must keep MRN small grains, Ulysses local in-situ dust, and mm/cm catastrophic-tail sensitivity separate.
- HVIT direct test velocity must remain separated from 23-60 km/s extrapolated impact rows.
- Data-medium survival, readability, and decode must be separate terms.
- Full `P_archive_recoverable` must remain `null` until target delivery, whole-path environment, stack qualification, material aging, media readability, and recovery/readout factors are externally closed.

## Evidence Boundary

This artifact is a proof boundary, not a completed proof.
It can show where present-day material classes and deterministic physics make the passive archive concept plausible.
It cannot by itself prove 10 Myr recovery, mission readiness, black-hole capture targeting, or flight hardware qualification.

## Promotion Gates

Stronger public language requires all of the following:

- dynamic target worldline corridor for the selected arrival epoch;
- whole-path dust, gas, plasma, and radiation model;
- full-stack hypervelocity impact evidence or reviewed hydrocode closure;
- material aging and radiation transport evidence;
- end-to-end medium damage-to-decode evidence;
- TPS/SRM hot-vacuum qualification for the Sun-Oberth mode;
- independent review and proof-promotion record.
