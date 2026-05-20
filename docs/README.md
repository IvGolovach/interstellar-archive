# Documentation Map

This repository has grown into several layers: public framing, deterministic contracts, engineering governance, and generated evidence.
This index is the stable starting point for humans and tools.

## Start Here

- `README.md`: public framing, thesis, and top-level trust model.
- `REPRODUCIBILITY.md`: canonical commands for local and CI-equivalent verification.
- `PROJECT_TIMELINE.md`: reader-facing development chronology for the clean mirror.
- `PUBLICATION_POLICY.md`: publication boundary and wording policy for future public release.
- `docs/ARTIFACT_POLICY.md`: source-of-truth boundaries between authored files, tracked generated baselines, and ephemeral outputs.

## Public Contract Docs

- `ARCHITECTURE.md`: system-level architecture and invariants for the public research artifact.
- `EVIDENCE.md`: evidence chain and how claims map onto assumptions, models, and sources.
- `INVARIANTS.md`: non-negotiable repository invariants and trust boundaries.
- `LIMITATIONS.md`: explicit non-goals and modeling limits.
- `CITATION.cff`: citation metadata for the published artifact.
- `PUBLICATION_POLICY.md`: claim boundary and release-readiness policy.
- `PROJECT_TIMELINE.md`: private-provenance timeline summarized for public readers.

## Mission and Model Contracts

- `mission/`: deterministic mission specification, uncertainty model, optimization contract, and mission-DAG interfaces.
- `mission/capsule/`: deterministic capsule stack, material allocations, mass closure, and survivability-facing inputs.
- `mission/survivability/`: reduced-order deep-time capsule survivability engine with provenance-tagged inputs and model coefficients.
- `mission/CAPSULE_RISK_BUDGET_SPEC_v1.md`: mission-facing contract for the non-certifying Capsule Risk Budget v2 Monte Carlo artifact.
- `mission/MISSION_FEASIBILITY_SCREEN_SPEC_v1.md`: mission-facing contract for target, velocity, flight-time, dust/gas, risk-link, and cost-proxy feasibility screens.
- `mission/USER_MISSION_RUN_CATALOG_SPEC_v1.md`: mission-facing contract for selected mission run ids, runtime-generation recipes, local review-pack validation, and DAG manifest linkage.
- `mission/MISSION_PROBABILITY_COUPLING_SPEC_v1.md`: mission-facing contract for factorized mission probability coupling with open external factors and compact DAG snapshots.
- `mission/UNCERTAINTY_INTERACTIONS_SPEC_v1.md`: mission-facing contract for pairwise uncertainty residual screens with open covariance and correlation evidence gates.
- `mission/EVIDENCE_UPGRADE_CAMPAIGN_SPEC_v1.md`: mission-facing contract for the evidence-review campaign that ranks trust/source upgrades without automatic promotion.
- `mission/OPTIMIZATION_V2_SPEC_v1.md`: mission-facing contract for the four-axis optimization decision surface with explicit cost and qualification proxy boundaries.
- `mission/EXTERNAL_VALIDATION_REVIEW_PACK_SPEC_v1.md`: mission-facing contract for external validation review cases, reviewer deliverables, and non-certifying acceptance records.
- `mission/PUBLIC_NARRATIVE_HARDENING_SPEC_v1.md`: mission-facing contract for blocked public claims, required qualifiers, and browser-rendering claim boundaries.
- `mission/EXTERNAL_VALIDATION_EXECUTION_LEDGER_SPEC_v1.md`: mission-facing contract for review execution records without claiming external validation completion.
- `mission/INDEPENDENT_PHYSICS_BACKEND_COMPARISON_SPEC_v1.md`: mission-facing contract for repo analytic cross-checks while independent backend evidence remains open.
- `mission/CAPSULE_QUALIFICATION_EVIDENCE_PACK_SPEC_v1.md`: mission-facing contract for capsule material stack, mass closure, and external qualification test matrix.
- `mission/EVIDENCE_UPGRADE_CLOSURE_SPEC_v1.md`: mission-facing contract for the first evidence closure cycle without trust-grade promotion.
- `mission/EXTERNAL_REPRODUCTION_KIT_SPEC_v1.md`: mission-facing contract for exportable reviewer reproduction packs without claiming external execution.
- `mission/EXTERNAL_EVIDENCE_INTAKE_SPEC_v1.md`: mission-facing contract for validating future external evidence records while rejecting self-signed repository-native records.
- `mission/EXTERNAL_EVIDENCE_RECORD_SCHEMA_v1.json`: schema for future externally supplied reproduction, backend, qualification, red-team, and wording-audit records.
- `mission/EXTERNAL_VALIDATION_CAMPAIGN_SPEC_v1.md`: mission-facing contract for the six-workstream external validation campaign and proof-promotion boundary.
- `mission/RELEASE_CANDIDATE_READINESS_SPEC_v1.md`: mission-facing contract for publication-readiness indexing without certification or flight-readiness claims.
- `mission/ROADMAP_CLOSURE_SPEC_v1.md`: mission-facing contract for the full v2 roadmap closure artifact and its external-evidence-open semantics.
- `mission/baseline/`: public mission-baseline library used by the CLI wrapper and downstream mission tooling.
- `mission/guards/`: public guard-layer API for realistic/speculative domain enforcement and optimization safety.
- `mission/evidence_validation.py`: canonical evidence-validation library used by strict CI wrappers.
- `parameters/`: canonical numeric registry, source policy, and trust grading for both public mission parameters and internal audit-only literals.
- `parameters/registry/parameter_literal_scope.v1.json`: manifest declaring audited numeric-literal paths, watched DAG/optimization roots, and explicit exclusion rationales.
- `sim/`: deterministic simulation core used by the browser demo and checksum contract.
- `sim/public/`: stable browser-facing simulation boundary; `web/` should consume this surface instead of `sim/core`, `sim/schema`, or `sim/scenarios` directly.
- `models/`: Python evidence and physics helpers backing the research artifact.

## Web Workspace

- `web/src/app/`: hash-route parsing, workspace navigation, and page-level composition.
- `web/src/pages/`: lazy route entrypoints for Mission, Parameters, Failure Surface, and Optimization.
- `web/src/pages/CapsuleLabRoute.tsx`: artifact-backed capsule target/time/velocity/profile interaction.
- `web/src/pages/UserMissionRunRoute.tsx`: artifact-backed selected-run recipe, compiled-scenario preview, and local pack boundary route.
- `web/src/pages/MissionProbabilityCouplingRoute.tsx`: artifact-backed mission probability coupling route.
- `web/src/pages/UncertaintyInteractionsRoute.tsx`: artifact-backed pairwise uncertainty interaction route.
- `web/src/pages/EvidenceCampaignRoute.tsx`: artifact-backed evidence-upgrade campaign route.
- `web/src/pages/OptimizationLabRoute.tsx`: artifact-backed optimization v1/v2 decision surface route.
- `web/src/pages/MissionDagBoundaryRoute.tsx`: artifact-backed Mission DAG v2 module-boundary route.
- `web/src/pages/ExternalReviewRoute.tsx`: artifact-backed external validation review-pack route.
- `web/src/pages/ExternalProofRoute.tsx`: artifact-backed proof-phase route covering review execution, analytic cross-checks, capsule qualification, evidence closure, validation campaign status, and release readiness.
- `web/src/pages/PublicNarrativeRoute.tsx`: artifact-backed public narrative hardening route.
- `web/src/ui/`: render-layer components built on top of the public sim/artifact boundaries.

## Evidence and Generated Baselines

- `artifacts/`: tracked, deterministic baseline outputs consumed by docs, badges, and the UI.
- `artifacts/public/`: stable browser-facing artifact contract; `browser_dataset.v1.json` is the single UI-facing dataset assembled from tracked generated baselines and intentionally exposes only registry-visible public mission/design/environment parameters.
- `artifacts/capsule_survivability_lab.v1.json`: generated capsule design and deep-time survivability rows, including source data, model coefficients, and non-certification notice.
- `artifacts/capsule_risk_budget.v1.json`: generated Capsule Risk Budget v2 rows that explain survival-number uncertainty, attack modes, and source/proxy/assumption boundaries.
- `artifacts/mission_feasibility_screen.v1.json`: generated target/velocity/time feasibility screen linking Capsule Lab rows to dust/gas screens, black-hole horizon checks, risk-budget rows, and cost-energy proxies.
- `artifacts/user_mission_run_catalog.v1.json`: generated selected-run catalog linking target/velocity choices to stable run ids, local review-pack templates, source hashes, and blocked claims.
- `artifacts/runtime_scenario_generation.v1.json`: generated runtime-generation recipe surface with command previews, compiled-scenario deltas, expected pack files, local ownership boundaries, and blocked runtime claims.
- `artifacts/mission_probability_coupling.v1.json`: generated factorized mission probability coupling rows with capsule/data review proxies, open external factors, compact DAG snapshots, evidence gaps, and blocked claims.
- `artifacts/uncertainty_interactions.v1.json`: generated pairwise uncertainty interaction rows with endpoint residuals, open correlation status, covariance evidence gaps, and blocked claims.
- `artifacts/evidence_upgrade_campaign.v1.json`: generated evidence-upgrade campaign rows, public/internal rollups, source-quality gaps, recommended actions, and blocked trust-promotion claims.
- `artifacts/optimization_v2_frontier.v1.json`: generated four-axis optimization decision surface over success, risk, qualification-gap, and cost-proxy screening axes.
- `artifacts/mission_dag_v2_boundary.v1.json`: generated Mission DAG v2 boundary rows covering module schemas, scenario nodes, failure taxonomy mappings, trace requirements, and independent-backend evidence gaps.
- `artifacts/external_validation_review_pack.v1.json`: generated independent-review pack covering review cases, required external deliverables, acceptance-record fields, and blocked validation claims.
- `artifacts/public_narrative_hardening.v1.json`: generated public narrative hardening artifact covering blocked public claims, required qualifiers, replacement guidance, and browser-rendering boundaries.
- `artifacts/external_validation_execution_ledger.v1.json`: generated review-execution ledger with zero uploaded external records and explicit acceptance-record schema.
- `artifacts/independent_physics_backend_comparison.v1.json`: generated repo analytic cross-check surface that keeps independent backend validation open.
- `artifacts/capsule_qualification_evidence_pack.v1.json`: generated material-stack and qualification-test matrix with no lab completion claim.
- `artifacts/evidence_upgrade_closure.v1.json`: generated first evidence closure cycle that quarantines speculative rows and performs no automatic trust promotion.
- `artifacts/external_reproduction_kit.v1.json`: generated reviewer reproduction-kit contract with export commands and no external-execution claim.
- `artifacts/external_evidence_intake.v1.json`: generated external-evidence intake contract with zero accepted records and strict anti-self-attestation policy.
- `artifacts/external_validation_campaign.v1.json`: generated six-workstream campaign index covering first external record, independent backend, capsule qualification, line-of-sight environment, proof promotion, and public dossier boundaries.
- `artifacts/release_candidate_readiness.v1.json`: generated publication-candidate readiness index that keeps certification, qualification, and independent validation blocked.
- `artifacts/roadmap_closure.v1.json`: generated full-v2 roadmap closure summary for all 15 major work items, including validators, model summaries, false-claim blocks, and external evidence gaps.
- `evidence/`: authored claim, assumption, and source registries.
- `ops/reports/`: ignored run outputs produced during local or CI execution; useful for debugging, not a source of truth.

## Engineering and Change Governance

- `engineering/GOVERNANCE.md`: governance rules and repository change discipline.
- `engineering/DECISIONS.md`: design and policy decisions.
- `engineering/CHANGELOG.md`: append-only engineering changelog.
- `engineering/ARCHITECTURE.md`: engineering-oriented architecture contract.

## Supplemental Notes

- `mission/MISSION_LAYER_SUMMARY.md`: compact summary of the mission-definition layer and next technical work.

## Validation Entry Points

- `make check`: canonical full repository check from the repo root.
- `python3 scripts/ci/check_suite.py`: same validation flow with explicit SHA overrides when needed.
- `python3 scripts/ci/required_paths_validate.py --strict`: validates the required file contract declared in `docs/required_paths.v1.json`.

## Required File Contract

The required documentation and registry surface is versioned in `docs/required_paths.v1.json`.
CI and local full checks both validate that manifest instead of hardcoding long file lists in multiple places.
