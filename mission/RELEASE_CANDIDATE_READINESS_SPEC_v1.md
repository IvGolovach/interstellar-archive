# Release Candidate Readiness Spec v1

## Scope

`artifacts/release_candidate_readiness.v1.json` is a repository-publication readiness index over the proof-phase artifacts and existing public-claim boundaries.

## Required Semantics

- `release_candidate_status` must be `repo_publication_candidate_external_evidence_open`.
- `repo_publication_candidate_ready` may be true only for repository-publication readiness, not certification or flight approval.
- `certification_go`, `flight_readiness_go`, `external_validation_completed`, `qualification_complete`, `independent_backend_validated`, and `trust_grade_promotions_completed` must remain `false`.
- At least the external validation, capsule qualification, and independent backend gates must remain `external_required`.

## Evidence Boundary

The artifact can make a PR/release easier to review. It must not claim a validated mission, qualified capsule, independent physics backend, source correctness, legal approval, launch approval, or operational readiness.
