# Evidence Upgrade Campaign v1

`evidence_upgrade_campaign.v1` is a deterministic triage artifact for roadmap item 9. It ranks parameter claims by current trust grade, source type, public exposure, core-probability relevance, and existing sensitivity impact.

The artifact does not upgrade any trust grade by itself. It defines the review work required before a parameter can move from assumption-bound or moderately sourced evidence to a stronger evidence class.

## Contract

- Source truth: parameter claims, parameter registry, evidence sources, public evidence index, sensitivity summary, and p-success defensibility artifact.
- Output: all campaign rows, top 15 priorities, trust distribution, source/gap labels, recommended actions, acceptance criteria, and blocked claims.
- Upgrade policy: `C -> B`, `B -> A`, and `D` remains speculative unless replaced by source-backed physics.
- Browser policy: public campaign rows may be rendered in detail; internal audit rows are summarized only as aggregate counts.
- Non-certification: the campaign is a work ledger, not an external validation result.

## Non-Goals

- It does not change `parameters/registry/parameter_claims.v1.json`.
- It does not certify external sources or hardware readiness.
- It does not close scientific correctness; it makes the next evidence work visible.
