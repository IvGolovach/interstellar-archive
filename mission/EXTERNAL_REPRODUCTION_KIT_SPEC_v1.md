# External Reproduction Kit Spec v1

This spec defines the repository-native reviewer handoff pack for external reproduction.

The generated kit artifact and exported pack are not external validation records. They only define what an independent reviewer should run, which committed artifacts are in scope, which record schema must be used, and which claims remain blocked until an accepted external evidence record exists.

Required properties:
- deterministic artifact generation from committed repository state
- exportable reviewer pack with commands, source artifact copies, and an evidence-record template
- no claim promotion from pack export alone
- explicit rejection of repository-native self-attestation as external proof
