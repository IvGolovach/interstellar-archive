# Versioning Contract v1

This document defines SemVer release invariants for the repository.

## Source Of Truth
- `VERSION` (root file) is the canonical SemVer value (`MAJOR.MINOR.PATCH`).
- A SemVer release tag MUST be `v{VERSION}`.
- Only tags matching `vMAJOR.MINOR.PATCH` are SemVer release tags.
- Narrative milestones are allowed only outside the SemVer namespace.

## Invariants
At any commit on `main`:
- `VERSION == CITATION.cff.version`
- `artifacts/research_signals.json.version == "v{VERSION}"`
- If `HEAD` has a SemVer tag, it MUST be `v{VERSION}`.

## Tag Semantics
- Valid SemVer tags use `vMAJOR.MINOR.PATCH`.
- Leading zeros are not allowed (`v01.2.3` invalid).
- Tags like `v1` or `v1.2` are invalid in the version namespace.
- Narrative markers must not use SemVer-compatible names.

## Release Discipline
1. Bump `VERSION` and sync dependent metadata.
2. Run strict CI checks and ensure green status.
3. Create tag `v{VERSION}` on the validated commit.
4. Push tag and publish release notes.

## Guardrails
- `scripts/ci/version_contract_validate.py --strict` is the enforcement gate.
- CI must run this gate in `evidence.yml` before evidence-chain checks.
- Any mismatch is a hard failure (exit code `2`).
