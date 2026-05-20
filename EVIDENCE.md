# Evidence Layer v1

## Purpose
`mission/EVIDENCE_REGISTRY_v1.json` is the machine-checkable contract that binds mission/physics parameters to explicit evidence sources and trust grades.

This layer answers three questions for each parameter:
1. Where does this value or distribution come from?
2. Is it realistic or speculative?
3. What trust grade is assigned, and why?

## Data model

Core files:
- `mission/EVIDENCE_SCHEMA_v1.json`
- `mission/EVIDENCE_REGISTRY_v1.json`
- `mission/UNCERTAINTY_MODEL_v1.json`
- `mission/MISSION_SCHEMA_v1.json`

Entity types:
- `EvidenceSource`: source metadata (`paper|report|dataset|assumption`).
- `ParameterClaim`: parameter binding (`parameter_id`, `value_mode`, `units`, `mode`, `evidence_source_ids`, `trust_grade`, `justification`, `last_reviewed_commit`).

## Enforcement rules

Enforced by `scripts/ci/evidence_validate.py --strict`:
- Every `parameter_id` declared in mission schema must exist in evidence registry.
- `evidence_source_ids` must be non-empty and resolve to existing sources.
- `mode=realistic` cannot use `trust_grade=D`.
- `trust_grade=D` is allowed only for `mode=speculative`.
- Claims with `value_mode=distribution` must have uncertainty entries with numeric `bounds.min < bounds.max`.

Negative drift guard:
- If `ParameterClaim`/`trust_grade`/`evidence_source_ids` changes, CI requires `engineering/CHANGELOG.md` update in the same diff.

## Local commands

```bash
python3 scripts/ci/evidence_validate.py --strict
python3 scripts/ci/evidence_coverage.py --min 95
python3 scripts/build_evidence_status.py
```

## Status artifact

`scripts/build_evidence_status.py` generates:
- `artifacts/evidence_status_v1.json`

Fields:
- `total_parameters`
- `realistic_parameters`
- `speculative_parameters`
- `trust_distribution`
- `missing_evidence_count`
- `evidence_completeness_ratio`
