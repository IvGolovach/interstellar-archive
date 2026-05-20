# Failure Taxonomy v1

Failure taxonomy is stored in `mission/dag/registry/failure_taxonomy.v1.json`.

## Stage semantics

- `S0`: environment gating / pre-encounter disqualification
- `S1`: navigation and control authority collapse
- `S2`: survival hardware failure under environment stress
- `S3`: data persistence/integrity failure

## Required behavior

- Every module output with `status=FAIL|WARN` must reference a valid taxonomy ID.
- Unknown taxonomy IDs are hard failures.
- Taxonomy coverage report is generated per DAG run.

## v1 caveat

Taxonomy identifies observable failure surfaces and evidence gaps. It does not claim root-cause completeness of all astrophysical or material mechanisms.
