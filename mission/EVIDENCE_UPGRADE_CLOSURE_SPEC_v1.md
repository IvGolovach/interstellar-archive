# Evidence Upgrade Closure Spec v1

## Scope

`artifacts/evidence_upgrade_closure.v1.json` records the first closure cycle over the evidence-upgrade campaign without changing trust grades or claiming source correctness.

## Required Semantics

- `closure_cycle_count` must match the recorded top-priority rows.
- Speculative rows must be quarantined instead of promoted into realistic proof surfaces.
- Rows that need source replacement, public URLs, narrowed uncertainty bounds, or primary datasets must remain `external_required`.
- `external_source_upgrade_count`, `trust_grade_promotion_count`, and `realistic_D_grade_public_rows_closed` must remain `0` until supporting evidence is added.
- `source_correctness_claimed` and `trust_grades_upgraded_automatically` must remain `false`.

## Evidence Boundary

This artifact can document decisions and next actions. It cannot upgrade trust grades without source-registry changes, derivation notes, and strict validators.
