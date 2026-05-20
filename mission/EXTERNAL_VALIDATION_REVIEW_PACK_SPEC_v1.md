# External Validation Review Pack Spec v1

This spec turns roadmap item 14 into a deterministic repository-native review-pack artifact.

The artifact prepares external review cases and acceptance records.
It does not claim that third-party validation, independent reproduction, independent physics benchmarking, external red-team review, or flight qualification has happened.

## Source Inputs

- `docs/research/VALIDATION_AND_QUALIFICATION_GAPS_v1.md`
- `docs/FULL_V2_ROADMAP_CLOSURE.md`
- `docs/ARTIFACT_POLICY.md`
- generated mission, risk, probability, uncertainty, evidence, DAG, cost, and runtime artifacts
- this spec, builder, validator, and implementation module

## Required Artifact

The builder writes `artifacts/external_validation_review_pack.v1.json`.

The artifact must expose:

- review cases for optimistic priors, dust tails, media decay, targetability separation, independent backend comparison, procurement boundaries, and public wording risk,
- external review gates with `external_required` status,
- source artifacts and required reviewer evidence for every case,
- acceptance record fields future reviewers must provide,
- rollup booleans that keep third-party review, independent reproduction, independent benchmark, high-fidelity state trace, external red-team, and external validation claims false,
- blocked claims and interpretation limits.

## Browser Boundary

The browser may render committed review-pack fields.
It must not claim independent validation or execute external review workflows.
