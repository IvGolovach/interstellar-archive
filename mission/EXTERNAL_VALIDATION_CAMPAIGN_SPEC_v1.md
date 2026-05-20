# External Validation Campaign Spec v1

Purpose: define the repository-native campaign surface for the six external
validation workstreams without claiming that external validation, lab
qualification, or public wording approval has already happened.

## Scope

The campaign coordinates:

- first real external evidence record intake;
- independent physics backend execution;
- capsule qualification program;
- line-of-sight environment model;
- proof-promotion review;
- public evidence dossier.

## Required boundaries

- `artifacts/external_validation_campaign.v1.json` is a campaign index, not an
  external evidence record.
- Accepted records in `artifacts/external_evidence_intake.v1.json` must remain
  separate from claim promotion.
- No v1 path may automatically set certification, flight readiness, external
  validation, independent-backend validation, or qualification complete.
- The line-of-sight environment section may encode source-backed anchors, but
  exact mm/cm dust flux, target-region plasma, and whole-path ISM averages stay
  assumption-bound until a direction-specific model exists.
- The public evidence dossier may show blocked claims and evidence gaps, but it
  cannot approve marketing, legal, certification, or public claim language.

## Artifact contract

`external_validation_campaign.v1` must expose:

- a six-row `workstreams` array in stable order;
- `campaign_policy` flags that records do not directly unlock claims and proof
  promotion requires follow-up review;
- nested boundary sections for backend execution, line-of-sight environment,
  capsule qualification, proof promotion, and public dossier status;
- `rollup` booleans that keep external validation, independent backend
  validation, line-of-sight completion, qualification completion, proof
  promotion, and certification false by default;
- blocked claims and external evidence gaps suitable for public review.

The validator is intentionally conservative: repo-native readiness can be true,
but proof claims must remain false until an external reviewer/lab/auditor
provides accepted evidence and a separate promotion review updates the claim
surface.
