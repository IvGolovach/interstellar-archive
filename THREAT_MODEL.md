# Threat Model

## Scope
This threat model covers repository-level research integrity controls: deterministic outputs, golden checksum governance, evidence traceability, and model-version contract stability. It does not cover operational security of developer machines or external hosting providers.

## Assets (what we protect)
- Determinism contract for simulation outputs and golden checksum stability.
- Evidence integrity chain (`claim -> assumption -> model -> artifact -> source`).
- Model evolution protocol and versioned governance records.
- Branch protection and CI enforcement configuration for `main`.

## Adversary model
Two categories are considered.
- Benign mistakes: accidental edits, stale branches, missing documentation updates, unchecked checksum changes.
- Malicious tampering: intentional modification of model/evidence outputs, selective proof deletion, or policy bypass attempts through branch or CI misconfiguration.

## Threats
- Silent model drift without explicit version/governance update.
- Golden checksum replacement that is not tied to model evolution policy.
- Evidence registry edits without rationale, causing trust-grade drift.
- Policy bypass by direct push or disabled required checks.
- Incomplete public proof collection that hides CI or branch-protection state.

## Mitigations
- Golden integrity checks enforce checksum/version coupling and block unauthorized drift (`web-sim.yml`, `scripts/benchmark_drift_guard.py`).
- Evidence contract validators enforce parameter/source linkage and trust constraints (`scripts/ci/evidence_validate.py`).
- Governance rule engine enforces changelog/decision traceability (`scripts/ci/governance_check.py`).
- Remote proof fallback validators enforce web-captured CI and branch-protection contracts (`scripts/ci/remote_proof_aggregate.py` and related validators).
- Branch policy states no force-push and no history rewrite on `main` (`engineering/GOVERNANCE.md`).

## Residual risk / non-goals
- Web-fallback proofs depend on accurate manual capture when API access is unavailable.
- This model does not assert physical correctness of mission assumptions; it only protects process integrity.
- This model does not replace independent external audit of source citations or scientific validity.
