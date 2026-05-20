# ROADMAP_CLOSURE_SPEC_v1

## 1. Intent

This spec defines `artifacts/roadmap_closure.v1.json`, the machine-readable closure contract for the full v2 roadmap.
The artifact covers the 15 long-running work items identified after Capsule Risk Budget v2 and records what is implemented inside this repository, what remains external evidence, and what must not be claimed.

This spec does not convert repository artifacts into hardware certification, mission readiness, procurement approval, launch authorization, or empirical reliability evidence.

## 2. Required Artifact

Expected generated artifact:

- `artifacts/roadmap_closure.v1.json`

Expected builder:

- `scripts/build_roadmap_closure_artifact.py`

Expected validator:

- `scripts/ci/roadmap_closure_validate.py`

The artifact must be generated from tracked repository inputs and committed only with the builder and validator.

## 3. Required Top-Level Fields

| field | requirement |
| --- | --- |
| `schema_version` | Must equal `roadmap_closure.v1`. |
| `generator` | Must equal `scripts/build_roadmap_closure_artifact.py`. |
| `public_scope` | Must equal `full_v2_roadmap_repo_native_closure`. |
| `non_certification_notice` | Must be `true`. |
| `source_artifacts` | Must list tracked source artifacts and SHA-256 digests. |
| `roadmap_item_count` | Must equal `15`. |
| `roadmap_items` | Must contain exactly the 15 roadmap records in stable id order. |
| `closure_metrics` | Must summarize implemented count, non-certification count, evidence-gap count, and trust-grade distribution. |
| `model_summaries` | Must expose deterministic summaries for physics, trajectory, dust, radiation/material, mission coupling, uncertainty, optimization, and cost feasibility. |
| `qualification_tracks` | Must expose capsule stack and archive-media qualification gaps. |
| `evidence_upgrade` | Must expose current trust distribution and upgrade priorities. |
| `dag_v2` | Must expose module-trace expectations. |
| `runtime_runs` | Must expose selected-run catalog status, local review-pack runner, and DAG manifest/hashchain fields. |
| `model_summaries.mission_coupling` | Must reference the tracked mission probability coupling artifact and keep full mission probability externally open. |
| `review_pack` | Must expose red-team review cases. |
| `public_narrative` | Must expose forbidden and required public claim language. |

## 4. Required Roadmap Item IDs

The artifact must contain these records in order:

1. `roadmap-01` Mission Physics v2 screening layer
2. `roadmap-02` Target trajectory and reachability engine
3. `roadmap-03` Capsule qualification evidence stack
4. `roadmap-04` Archive media and bit-level recoverability
5. `roadmap-05` Interstellar dust-tail model
6. `roadmap-06` Radiation and material transport hooks
7. `roadmap-07` Full mission-level probabilistic coupling
8. `roadmap-08` Uncertainty v2 interactions
9. `roadmap-09` Evidence upgrade campaign
10. `roadmap-10` Optimization v2
11. `roadmap-11` Mission DAG v2 physics module boundary
12. `roadmap-12` Runtime scenario generation and user-owned runs
13. `roadmap-13` Cost, procurement, and architecture feasibility
14. `roadmap-14` External validation and independent review pack
15. `roadmap-15` Public narrative hardening

Every item must include:

- `status = repo_native_closure_implemented_external_evidence_open`
- `implementation_mode`
- `summary`
- `artifacts`
- `validators`
- `model_summary_ref`
- `external_evidence_gaps`
- `acceptance_criteria`
- `false_claims_blocked`
- `non_certification_notice = true`
- `claim_boundary`

## 5. Closure Semantics

`repo_native_closure_implemented_external_evidence_open` means the repository now has an auditable deterministic contract, generated artifact, validation gate, and public summary for the item.
It does not mean the external physical, experimental, procurement, legal, or operational evidence has been obtained.

The artifact must keep these boundaries separate:

- repository implementation,
- deterministic screening model,
- review/qualification gap,
- external evidence still required.

## 6. Validation Rules

Validators must fail when:

- schema, generator, public scope, or non-certification fields drift,
- the item list is not exactly 15 records in stable order,
- any item lacks artifacts, validators, evidence gaps, or claim boundaries,
- any item drops its non-certification notice,
- closure metrics do not count all 15 items,
- mission-coupling probabilities are outside `[0, 1]`,
- public narrative does not forbid certification language,
- required model-summary sections are absent.

## 7. Browser Boundary

The browser may render a compact summary of this artifact.
The UI must not recompute the roadmap closure model, infer missing evidence, or soften the external-evidence gaps.

## 8. Non-Goals

This artifact does not provide:

- full GR/MHD simulation,
- hardware qualification,
- media aging proof,
- procurement-grade cost,
- launch approval,
- legal or regulatory clearance,
- third-party validation results,
- proof that selected targets can be reached.
