# Evidence Graph

This directory defines the machine-readable proof graph for quantitative statements in the whitepaper.

## Files

- `claims.json`: Canonical list of quantitative claims with numeric acceptance ranges.
- `assumptions.json`: Explicit assumptions linked to claims and artifacts.
- `sources.json`: Source registry (local documents, constants, bibliography keys).

## Chain Contract

Every claim must resolve this chain:

`claim -> assumption -> model -> artifact -> source`

The contract is enforced by:

- `scripts/build_evidence_artifacts.py`
- `scripts/audit_claim_chain.py`
- `tests/test_traceability_chain.py`

## Validation

Run the full pipeline:

```bash
scripts/run_evidence_checks.sh
```

