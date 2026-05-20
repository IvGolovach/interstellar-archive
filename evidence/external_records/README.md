# External Evidence Records

This directory is the intake location for future external evidence record JSON files.

Current state: no accepted external records are committed.

Rules:
- do not add repository-maintainer self-attestations as external evidence
- do not add internal CI logs as external evidence
- use `mission/EXTERNAL_EVIDENCE_RECORD_SCHEMA_v1.json`
- validate records with `scripts/ci/external_evidence_record_validate.py`
- claim promotion requires a follow-up repository review and validator update
