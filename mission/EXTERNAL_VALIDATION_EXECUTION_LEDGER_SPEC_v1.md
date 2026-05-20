# External Validation Execution Ledger Spec v1

## Scope

`artifacts/external_validation_execution_ledger.v1.json` is a deterministic queue and record schema for independent review execution. It is not a completed external review and must not unlock validation, certification, qualification, or flight-readiness claims.

## Required Semantics

- `non_certification_notice` must be `true`.
- `execution_ledger_status` must remain `repo_native_execution_ledger_ready_external_records_not_uploaded` until real external records are attached through a separate reviewed change.
- Every review case imported from `artifacts/external_validation_review_pack.v1.json` must keep `execution_status: external_required`.
- `execution_record_count` and `external_record_count` must remain `0` when no third-party records are present.
- The rollup must keep `external_validation_completed`, `third_party_records_uploaded`, and `independent_reproduction_completed` false.

## Evidence Boundary

The artifact may describe required reviewer fields, raw-output expectations, and blocked claims. It must not fabricate reviewer identities, commands, raw outputs, signatures, or attestations.
