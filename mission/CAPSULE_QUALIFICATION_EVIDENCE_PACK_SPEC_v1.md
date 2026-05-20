# Capsule Qualification Evidence Pack Spec v1

## Scope

`artifacts/capsule_qualification_evidence_pack.v1.json` packages the capsule material stack, mass closure, survivability inputs, failure modes, and qualification test matrix.

## Required Semantics

- `non_certification_notice` must be `true`.
- The material and layer data must come from `mission/capsule/capsule_design.v1.json`.
- The qualification test matrix must come from the capsule risk budget qualification roadmap and remain `external_required`.
- `lab_record_count` must remain `0` unless real lab, reviewer, or test-facility records are attached through a separate reviewed change.
- `qualification_complete`, `flight_ready_claimed`, and `certified_hardware_survivability` must remain `false`.

## Evidence Boundary

Mass closure is arithmetic. It does not prove hardware survivability, archive recoverability, or flight readiness. Stack-level ballistic, radiation, plasma, aging, ECC, and reviewer records remain external evidence.
