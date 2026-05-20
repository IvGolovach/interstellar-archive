# External Evidence Intake Spec v1

This spec defines how externally supplied reproduction, backend-comparison, qualification, red-team, or wording-audit records enter the repository.

The v1 intake contract is deliberately conservative:
- accepted records are evidence intake only
- accepted records do not automatically unlock certification, qualification, or mission-readiness claims
- records from repository maintainers, internal CI, or self-signed repository-native runs are rejected as external evidence
- every record must cite a reviewed commit, command set, raw outputs or report URI, reviewer identity, conflict statement, and external attestation/report URI

The current committed intake artifact may contain zero records. That state is valid and means the project is ready to receive external evidence, not that external validation has happened.
