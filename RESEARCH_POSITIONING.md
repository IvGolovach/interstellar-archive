# Research Positioning

## Why deterministic simulation matters
Deterministic simulation is required for credible comparison across revisions. If identical inputs do not produce identical outputs, observed differences cannot be confidently attributed to model changes. Determinism is therefore a prerequisite for auditability, regression detection, and scientific communication.

## Why evidence packs matter
Evidence packs convert claims into inspectable artifacts. They provide a stable bundle of inputs, outputs, checksums, and metadata that third parties can reproduce without relying on author memory. This reduces ambiguity in public discussion and enables independent verification.

## Why governance matters
Governance defines how and when changes are allowed. In this repository, decisions and changelog rationale provide traceability, while CI guardrails prevent undocumented behavior drift. Governance is used here as a lightweight integrity mechanism, not as process overhead.

## Known limitations
- The simulation is intentionally simplified and does not model all coupled physical processes.
- Parameter ranges are schema-bounded and may exclude plausible real-world edge regimes.
- Operational environments, manufacturing constraints, and hardware aging effects are only partially represented.
- Browser demo UX is an interpretation layer and not an authoritative scientific interface by itself.
- Some proofs are stored as CI artifacts and external references, not as full in-repo logs.

## Failure modes
- Incorrect assumptions can produce internally consistent but externally invalid conclusions.
- Versioning mistakes can cause checksum drift that appears as model evolution without justified rationale.
- Incomplete documentation updates can break claim traceability even when code checks pass.
- Governance bypass at repository settings level would undermine local enforcement guarantees.
