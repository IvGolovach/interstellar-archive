import { PUBLIC_DATASET_PATHS } from "../src/lib/artifact_public_contracts";
import {
  loadParameterDrilldownDataset,
  ParameterDrilldownDatasetError,
} from "../src/lib/parameter_drilldown_loader";

function main(): void {
  let dataset;
  try {
    dataset = loadParameterDrilldownDataset();
  } catch (error) {
    console.error("FAIL: browser dataset validation");
    if (error instanceof ParameterDrilldownDatasetError) {
      for (const validationError of error.validationErrors) {
        console.error(`- ${validationError}`);
      }
      process.exitCode = 1;
      return;
    }
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
    return;
  }

  const errors = [...dataset.errors];

  if (dataset.parameters.length === 0) {
    errors.push("dataset parameters must be non-empty");
  }
  if (dataset.parameters.some((parameter) => parameter.parameter_id.startsWith("code_literal."))) {
    errors.push("dataset parameters must exclude internal code_literal.* entries");
  }
  if (Object.keys(dataset.staticUsageGraph).some((parameterId) => parameterId.startsWith("code_literal."))) {
    errors.push("static usage graph must exclude internal code_literal.* entries");
  }
  if (Object.keys(dataset.evidenceIndex).some((parameterId) => parameterId.startsWith("code_literal."))) {
    errors.push("evidence index must exclude internal code_literal.* entries");
  }
  if (
    dataset.optimizationSearchSpace.parameters_considered.some((entry) =>
      entry.parameter_id.startsWith("code_literal."),
    )
  ) {
    errors.push("optimization search-space considered parameters must exclude internal code_literal.* entries");
  }
  if (
    dataset.optimizationSearchSpace.excluded_parameters.some((entry) =>
      entry.parameter_id.startsWith("code_literal."),
    )
  ) {
    errors.push("optimization search-space excluded parameters must exclude internal code_literal.* entries");
  }
  if (dataset.failureSurfaceBaseline.dominant_drivers.top3.length !== 3) {
    errors.push("failure surface dominant_drivers.top3 must contain exactly 3 entries");
  }
  if (dataset.objectiveScoreBaseline.contract_ref !== PUBLIC_DATASET_PATHS.objectiveContract) {
    errors.push("objective score contract_ref must match PUBLIC_DATASET_PATHS.objectiveContract");
  }
  if (dataset.optimizationFrontier.objective_contract_ref !== PUBLIC_DATASET_PATHS.objectiveContract) {
    errors.push("optimization frontier objective_contract_ref must match PUBLIC_DATASET_PATHS.objectiveContract");
  }
  if (dataset.optimizationV2.schema_version !== "optimization_v2_frontier.v1") {
    errors.push("optimization v2 schema_version must be optimization_v2_frontier.v1");
  }
  if (dataset.optimizationV2.candidate_count !== 20 || dataset.optimizationV2.candidates.length !== 20) {
    errors.push("optimization v2 must expose 20 source frontier candidates");
  }
  const optimizationV2Axes = ["p_success", "risk_envelope", "qualification_gap", "cost_proxy"] as const;
  if (
    dataset.optimizationV2.axis_contract.axes.map((axis) => axis.id).join(",") !==
    optimizationV2Axes.join(",")
  ) {
    errors.push("optimization v2 axis_contract must expose the four Pareto axes");
  }
  if (
    dataset.optimizationV2.rollup.axis_ids.join(",") !==
    optimizationV2Axes.join(",")
  ) {
    errors.push("optimization v2 must expose the four Pareto axes");
  }
  if (
    dataset.optimizationV2.rollup.global_optimum_claimed ||
    dataset.optimizationV2.rollup.calibrated_cost_model_available ||
    dataset.optimizationV2.rollup.qualification_complete
  ) {
    errors.push("optimization v2 must keep optimum, cost calibration, and qualification claims open");
  }
  if (!dataset.optimizationV2.blocked_claims.includes("procurement-grade cost estimate")) {
    errors.push("optimization v2 must block procurement-grade cost claims");
  }
  if (!dataset.optimizationV2.blocked_claims.includes("flight-ready design selected")) {
    errors.push("optimization v2 must block flight-ready design-selection claims");
  }
  const sourceCandidateIds = new Set(dataset.optimizationFrontier.points.map((point) => point.candidate_id));
  const v2CandidateIds = new Set<string>();
  const paretoMemberIds: string[] = [];
  for (const candidate of dataset.optimizationV2.candidates) {
    if (v2CandidateIds.has(candidate.candidate_id)) {
      errors.push(`optimization v2 duplicate candidate id: ${candidate.candidate_id}`);
    }
    v2CandidateIds.add(candidate.candidate_id);
    if (!sourceCandidateIds.has(candidate.source_candidate_id)) {
      errors.push(`optimization v2 candidate source_candidate_id missing: ${candidate.candidate_id}`);
    }
    for (const [axisIndex, axis] of optimizationV2Axes.entries()) {
      if (candidate.scores.objective_vector[axisIndex] !== candidate.scores[axis]) {
        errors.push(`optimization v2 objective_vector mismatch: ${candidate.candidate_id} ${axis}`);
      }
    }
    if (candidate.dominant_drivers.parameter_ids.some((parameterId) => parameterId.startsWith("code_literal."))) {
      errors.push(`optimization v2 candidate leaks internal dominant driver: ${candidate.candidate_id}`);
    }
    if (candidate.pareto_frontier_member) {
      paretoMemberIds.push(candidate.candidate_id);
    }
  }
  if (dataset.optimizationV2.pareto_frontier_candidate_ids.some((candidateId) => !v2CandidateIds.has(candidateId))) {
    errors.push("optimization v2 pareto ids must reference candidates");
  }
  if (paretoMemberIds.join(",") !== dataset.optimizationV2.pareto_frontier_candidate_ids.join(",")) {
    errors.push("optimization v2 pareto flags must match pareto ids");
  }
  if (dataset.capsuleSurvivabilityLab.schema_version !== "capsule_survivability_lab.v1") {
    errors.push("capsule survivability artifact schema_version must be capsule_survivability_lab.v1");
  }
  if (dataset.capsuleSurvivabilityLab.rows.length < 100) {
    errors.push("capsule survivability artifact must expose at least 100 rows");
  }
  if (dataset.capsuleRiskBudget.schema_version !== "capsule_risk_budget.v1") {
    errors.push("capsule risk budget artifact schema_version must be capsule_risk_budget.v1");
  }
  if (dataset.capsuleRiskBudget.source_artifact_ref !== PUBLIC_DATASET_PATHS.capsuleSurvivabilityLab) {
    errors.push("capsule risk budget source_artifact_ref must match capsule survivability artifact path");
  }
  if (dataset.capsuleRiskBudget.risk_budget_count < 100) {
    errors.push("capsule risk budget artifact summary must expose at least 100 risk budgets");
  }
  if (!dataset.capsuleRiskBudget.source_policy) {
    errors.push("capsule risk budget artifact summary must expose source_policy");
  }
  if ((dataset.capsuleRiskBudget.failure_modes ?? []).length < 8) {
    errors.push("capsule risk budget artifact summary must expose at least 8 failure modes");
  }
  if ((dataset.capsuleRiskBudget.qualification_roadmap ?? []).length < 5) {
    errors.push("capsule risk budget artifact summary must expose at least 5 qualification tracks");
  }
  if (dataset.missionFeasibilityScreen.schema_version !== "mission_feasibility_screen.v1") {
    errors.push("mission feasibility artifact schema_version must be mission_feasibility_screen.v1");
  }
  if (dataset.missionFeasibilityScreen.scenario_count !== 15) {
    errors.push("mission feasibility artifact summary must expose 15 scenario rows");
  }
  if (dataset.missionFeasibilityScreen.capsule_risk_budget_match_count !== 15) {
    errors.push("mission feasibility artifact summary must link all rows to capsule risk budget");
  }
  if (dataset.userMissionRunCatalog.schema_version !== "user_mission_run_catalog.v1") {
    errors.push("user mission run catalog schema_version must be user_mission_run_catalog.v1");
  }
  if (dataset.userMissionRunCatalog.run_count !== 15 || dataset.userMissionRunCatalog.run_rows.length !== 15) {
    errors.push("user mission run catalog must expose 15 run rows");
  }
  if (!dataset.userMissionRunCatalog.default_run_id.startsWith("umr-reference-black-hole-conditional-45-")) {
    errors.push("user mission run catalog default_run_id must reference the default feasibility row");
  }
  if (dataset.runtimeScenarioGeneration.schema_version !== "runtime_scenario_generation.v1") {
    errors.push("runtime scenario generation schema_version must be runtime_scenario_generation.v1");
  }
  if (
    dataset.runtimeScenarioGeneration.generation_row_count !== 15 ||
    dataset.runtimeScenarioGeneration.generation_rows.length !== 15
  ) {
    errors.push("runtime scenario generation must expose 15 recipe rows");
  }
  if (
    dataset.runtimeScenarioGeneration.run_pack_contract.writes_tracked_files ||
    dataset.runtimeScenarioGeneration.rollup.rows_writing_tracked_files !== 0
  ) {
    errors.push("runtime scenario generation must not write tracked files");
  }
  if (
    dataset.runtimeScenarioGeneration.rollup.remote_execution_claimed ||
    dataset.runtimeScenarioGeneration.rollup.persistent_reviewed_archive_claimed
  ) {
    errors.push("runtime scenario generation must keep remote execution and persistent archive claims open");
  }
  if (
    dataset.runtimeScenarioGeneration.generation_rows.some(
      (row) =>
        !row.command_preview.includes("scripts/run_user_mission_scenario.py") ||
        !row.command_preview.includes("--verify-deterministic") ||
        row.ownership_boundary.remote_execution ||
        row.ownership_boundary.persistent_reviewed_archive,
    )
  ) {
    errors.push("runtime scenario generation rows must render deterministic local-run recipes only");
  }
  if (!dataset.runtimeScenarioGeneration.blocked_claims.includes("persistent reviewed run archive")) {
    errors.push("runtime scenario generation must block persistent archive claims");
  }
  if (dataset.costProcurementArchitectureFeasibility.schema_version !== "cost_procurement_architecture_feasibility.v1") {
    errors.push("cost/procurement/architecture schema_version must be cost_procurement_architecture_feasibility.v1");
  }
  if (
    dataset.costProcurementArchitectureFeasibility.architecture_row_count !== 15 ||
    dataset.costProcurementArchitectureFeasibility.architecture_rows.length !== 15
  ) {
    errors.push("cost/procurement/architecture artifact must expose 15 rows");
  }
  if (
    dataset.costProcurementArchitectureFeasibility.rollup.procurement_grade_estimate_available ||
    dataset.costProcurementArchitectureFeasibility.rollup.vendor_quote_count !== 0 ||
    dataset.costProcurementArchitectureFeasibility.rollup.launch_vehicle_selected ||
    dataset.costProcurementArchitectureFeasibility.rollup.architecture_selected_for_flight ||
    dataset.costProcurementArchitectureFeasibility.rollup.calibrated_cost_model_available ||
    dataset.costProcurementArchitectureFeasibility.rollup.qualification_complete
  ) {
    errors.push("cost/procurement/architecture artifact must keep procurement and architecture claims open");
  }
  if (
    dataset.costProcurementArchitectureFeasibility.architecture_rows.some(
      (row) => row.procurement_status !== "external_required",
    )
  ) {
    errors.push("cost/procurement/architecture rows must keep procurement external");
  }
  if (!dataset.costProcurementArchitectureFeasibility.blocked_claims.includes("procurement-grade cost estimate")) {
    errors.push("cost/procurement/architecture artifact must block procurement-grade cost estimates");
  }
  if (dataset.externalValidationReviewPack.schema_version !== "external_validation_review_pack.v1") {
    errors.push("external validation review pack schema_version must be external_validation_review_pack.v1");
  }
  if (
    dataset.externalValidationReviewPack.review_case_count !== 7 ||
    dataset.externalValidationReviewPack.review_cases.length !== 7
  ) {
    errors.push("external validation review pack must expose 7 review cases");
  }
  if (
    dataset.externalValidationReviewPack.required_external_deliverables.length !== 6 ||
    dataset.externalValidationReviewPack.review_cases.some((row) => row.status !== "external_required")
  ) {
    errors.push("external validation review pack must keep all review deliverables external_required");
  }
  if (
    dataset.externalValidationReviewPack.rollup.third_party_review_completed ||
    dataset.externalValidationReviewPack.rollup.independent_reproduction_completed ||
    dataset.externalValidationReviewPack.rollup.independent_benchmark_completed ||
    dataset.externalValidationReviewPack.rollup.high_fidelity_state_trace_complete ||
    dataset.externalValidationReviewPack.rollup.external_red_team_completed ||
    dataset.externalValidationReviewPack.rollup.external_validation_claimed
  ) {
    errors.push("external validation review pack must keep external validation claims open");
  }
  if (!dataset.externalValidationReviewPack.blocked_claims.includes("third-party validated")) {
    errors.push("external validation review pack must block third-party validation claims");
  }
  if (dataset.publicNarrativeHardening.schema_version !== "public_narrative_hardening.v1") {
    errors.push("public narrative hardening schema_version must be public_narrative_hardening.v1");
  }
  if (
    dataset.publicNarrativeHardening.claim_rule_count !== 10 ||
    dataset.publicNarrativeHardening.claim_rules.length !== 10 ||
    dataset.publicNarrativeHardening.public_surface_count < 8
  ) {
    errors.push("public narrative hardening must expose 10 claim rules and at least 8 public surfaces");
  }
  if (
    dataset.publicNarrativeHardening.rollup.unsafe_public_overclaim_count !== 0 ||
    dataset.publicNarrativeHardening.rollup.external_wording_audit_completed ||
    dataset.publicNarrativeHardening.rollup.audience_testing_completed ||
    dataset.publicNarrativeHardening.rollup.legal_review_completed ||
    dataset.publicNarrativeHardening.rollup.public_claim_approval_completed
  ) {
    errors.push("public narrative hardening must keep public wording audit and approval open");
  }
  if (
    !dataset.publicNarrativeHardening.forbidden_public_claims.includes("certified") ||
    !dataset.publicNarrativeHardening.forbidden_public_claims.includes("external validation completed") ||
    !dataset.publicNarrativeHardening.forbidden_public_claims.includes("procurement-grade cost estimate")
  ) {
    errors.push("public narrative hardening must block certification, validation, and procurement overclaims");
  }
  if (
    !dataset.publicNarrativeHardening.required_public_concepts.includes("non-certifying") ||
    !dataset.publicNarrativeHardening.required_public_concepts.includes("deterministic artifact")
  ) {
    errors.push("public narrative hardening must require non-certifying deterministic artifact framing");
  }
  if (
    !dataset.publicNarrativeHardening.browser_boundary.artifact_only_rendering ||
    dataset.publicNarrativeHardening.browser_boundary.client_side_claim_recomputation_allowed ||
    dataset.publicNarrativeHardening.browser_boundary.blocked_claim_suppression_allowed ||
    dataset.publicNarrativeHardening.browser_boundary.external_gap_softening_allowed
  ) {
    errors.push("public narrative hardening browser boundary must render artifact fields only");
  }
  if (dataset.externalValidationExecutionLedger.schema_version !== "external_validation_execution_ledger.v1") {
    errors.push("external validation execution ledger schema_version must be external_validation_execution_ledger.v1");
  }
  if (
    dataset.externalValidationExecutionLedger.execution_record_count !== 0 ||
    dataset.externalValidationExecutionLedger.external_record_count !== 0 ||
    dataset.externalValidationExecutionLedger.rollup.external_validation_completed ||
    dataset.externalValidationExecutionLedger.rollup.third_party_records_uploaded
  ) {
    errors.push("external validation execution ledger must keep external records and validation completion open");
  }
  if (dataset.independentPhysicsBackendComparison.schema_version !== "independent_physics_backend_comparison.v1") {
    errors.push("independent physics backend comparison schema_version must be independent_physics_backend_comparison.v1");
  }
  if (
    dataset.independentPhysicsBackendComparison.analytic_check_count < 4 ||
    dataset.independentPhysicsBackendComparison.rollup.independent_external_backend_complete ||
    dataset.independentPhysicsBackendComparison.rollup.cross_backend_comparison_completed ||
    dataset.independentPhysicsBackendComparison.rollup.high_fidelity_state_trace_complete
  ) {
    errors.push("independent physics backend comparison must keep external backend validation open");
  }
  if (dataset.capsuleQualificationEvidencePack.schema_version !== "capsule_qualification_evidence_pack.v1") {
    errors.push("capsule qualification evidence pack schema_version must be capsule_qualification_evidence_pack.v1");
  }
  if (
    dataset.capsuleQualificationEvidencePack.mass_closure.configured_capsule_mass_kg !== 206 ||
    dataset.capsuleQualificationEvidencePack.lab_record_count !== 0 ||
    dataset.capsuleQualificationEvidencePack.rollup.qualification_complete ||
    dataset.capsuleQualificationEvidencePack.rollup.flight_ready_claimed
  ) {
    errors.push("capsule qualification evidence pack must keep lab qualification and flight readiness open");
  }
  if (dataset.evidenceUpgradeClosure.schema_version !== "evidence_upgrade_closure.v1") {
    errors.push("evidence upgrade closure schema_version must be evidence_upgrade_closure.v1");
  }
  if (
    dataset.evidenceUpgradeClosure.closure_cycle_count !== 15 ||
    dataset.evidenceUpgradeClosure.rollup.trust_grade_promotion_count !== 0 ||
    dataset.evidenceUpgradeClosure.rollup.source_correctness_claimed
  ) {
    errors.push("evidence upgrade closure must keep source correctness and trust promotions open");
  }
  if (dataset.externalReproductionKit.schema_version !== "external_reproduction_kit.v1") {
    errors.push("external reproduction kit schema_version must be external_reproduction_kit.v1");
  }
  if (
    dataset.externalReproductionKit.review_case_count !== 7 ||
    !dataset.externalReproductionKit.rollup.export_cli_available ||
    dataset.externalReproductionKit.rollup.external_execution_completed ||
    dataset.externalReproductionKit.rollup.first_real_external_record_present ||
    dataset.externalReproductionKit.rollup.fake_external_records_accepted
  ) {
    errors.push("external reproduction kit must be export-ready while execution and records remain open");
  }
  if (dataset.externalEvidenceIntake.schema_version !== "external_evidence_intake.v1") {
    errors.push("external evidence intake schema_version must be external_evidence_intake.v1");
  }
  if (
    dataset.externalEvidenceIntake.record_count !== 0 ||
    dataset.externalEvidenceIntake.accepted_record_count !== 0 ||
    dataset.externalEvidenceIntake.rejected_record_count !== 0 ||
    dataset.externalEvidenceIntake.rollup.first_real_external_record_present ||
    dataset.externalEvidenceIntake.rollup.external_validation_completed ||
    dataset.externalEvidenceIntake.rollup.independent_backend_validated ||
    dataset.externalEvidenceIntake.rollup.certification_go ||
    !dataset.externalEvidenceIntake.validation_policy.reject_repository_maintainer_as_external ||
    !dataset.externalEvidenceIntake.validation_policy.reject_self_signed_repo_native_records
  ) {
    errors.push("external evidence intake must keep first real external record open and reject fake records");
  }
  if (dataset.externalValidationCampaign.schema_version !== "external_validation_campaign.v1") {
    errors.push("external validation campaign schema_version must be external_validation_campaign.v1");
  }
  if (
    dataset.externalValidationCampaign.workstream_count !== 6 ||
    dataset.externalValidationCampaign.rollup.accepted_record_count !== 0 ||
    dataset.externalValidationCampaign.rollup.first_real_external_record_present ||
    dataset.externalValidationCampaign.rollup.external_validation_completed ||
    dataset.externalValidationCampaign.rollup.independent_backend_validated ||
    dataset.externalValidationCampaign.rollup.qualification_complete ||
    dataset.externalValidationCampaign.rollup.certification_go ||
    dataset.externalValidationCampaign.proof_promotion_review.automatic_claim_promotion_allowed ||
    !Array.isArray(dataset.externalValidationCampaign.proof_promotion_review.promoted_claims) ||
    dataset.externalValidationCampaign.proof_promotion_review.promoted_claims.length !== 0
  ) {
    errors.push("external validation campaign must keep six workstreams open without claim promotion");
  }
  if (
    dataset.externalValidationCampaign.public_evidence_dossier.marketing_claim_surface ||
    dataset.externalValidationCampaign.public_evidence_dossier.certification_language_allowed
  ) {
    errors.push("external validation campaign dossier must block marketing and certification language");
  }
  if (dataset.releaseCandidateReadiness.schema_version !== "release_candidate_readiness.v1") {
    errors.push("release candidate readiness schema_version must be release_candidate_readiness.v1");
  }
  if (
    !dataset.releaseCandidateReadiness.rollup.repo_publication_candidate_ready ||
    dataset.releaseCandidateReadiness.rollup.certification_go ||
    dataset.releaseCandidateReadiness.rollup.external_validation_completed ||
    dataset.releaseCandidateReadiness.rollup.qualification_complete ||
    dataset.releaseCandidateReadiness.rollup.independent_backend_validated
  ) {
    errors.push("release candidate readiness must be publication-ready but certification and external proof blocked");
  }
  if (dataset.missionProbabilityCoupling.schema_version !== "mission_probability_coupling.v1") {
    errors.push("mission probability coupling schema_version must be mission_probability_coupling.v1");
  }
  if (dataset.missionProbabilityCoupling.coupling_count !== 15 || dataset.missionProbabilityCoupling.coupling_rows.length !== 15) {
    errors.push("mission probability coupling must expose 15 coupling rows");
  }
  if (!dataset.missionProbabilityCoupling.default_coupling_id.startsWith("mpc-reference-black-hole-conditional-45-")) {
    errors.push("mission probability coupling default_coupling_id must reference the default run");
  }
  if (dataset.missionProbabilityCoupling.rollup.rows_with_full_mission_probability_closed !== 0) {
    errors.push("mission probability coupling must keep full mission probability open");
  }
  if (dataset.uncertaintyInteractions.schema_version !== "uncertainty_interactions.v1") {
    errors.push("uncertainty interactions schema_version must be uncertainty_interactions.v1");
  }
  if (
    dataset.uncertaintyInteractions.uncertainty_entry_count !== 4 ||
    dataset.uncertaintyInteractions.main_effects.length !== 4
  ) {
    errors.push("uncertainty interactions must expose 4 main effects");
  }
  if (
    dataset.uncertaintyInteractions.interaction_pair_count !== 6 ||
    dataset.uncertaintyInteractions.pair_interactions.length !== 6
  ) {
    errors.push("uncertainty interactions must expose 6 pair interactions");
  }
  if (dataset.uncertaintyInteractions.rollup.validated_correlation_count !== 0) {
    errors.push("uncertainty interactions must not claim validated correlations");
  }
  if (dataset.evidenceUpgradeCampaign.schema_version !== "evidence_upgrade_campaign.v1") {
    errors.push("evidence upgrade campaign schema_version must be evidence_upgrade_campaign.v1");
  }
  if (dataset.evidenceUpgradeCampaign.claim_count !== 66) {
    errors.push("evidence upgrade campaign must expose 66 all-claim rows in aggregate");
  }
  if (
    dataset.evidenceUpgradeCampaign.public_campaign_count !== 31 ||
    dataset.evidenceUpgradeCampaign.internal_audit_count !== 35
  ) {
    errors.push("evidence upgrade campaign must expose 31 public rows and 35 internal audit rows");
  }
  if (
    dataset.evidenceUpgradeCampaign.public_top_priorities.some((row) =>
      row.parameter_id.startsWith("code_literal."),
    )
  ) {
    errors.push("evidence upgrade campaign public_top_priorities must exclude internal code_literal.* entries");
  }
  if (!dataset.evidenceUpgradeCampaign.blocked_claims.includes("trust grades upgraded automatically")) {
    errors.push("evidence upgrade campaign must block automatic trust upgrades");
  }
  if (dataset.missionDagV2Boundary.schema_version !== "mission_dag_v2_boundary.v1") {
    errors.push("mission DAG v2 boundary schema_version must be mission_dag_v2_boundary.v1");
  }
  if (dataset.missionDagV2Boundary.module_count !== 6 || dataset.missionDagV2Boundary.module_boundaries.length !== 6) {
    errors.push("mission DAG v2 boundary must expose 6 module rows");
  }
  if (
    !dataset.missionDagV2Boundary.rollup.state_trace_contract_complete ||
    dataset.missionDagV2Boundary.rollup.independent_backend_complete ||
    dataset.missionDagV2Boundary.rollup.high_fidelity_state_traces_available ||
    dataset.missionDagV2Boundary.rollup.external_reproduction_completed
  ) {
    errors.push("mission DAG v2 boundary must keep trace contract explicit and backend evidence open");
  }
  if (
    dataset.missionDagV2Boundary.module_boundaries.some(
      (row) =>
        row.scenario_node_ids.length === 0 ||
        row.failure_taxonomy_ids.length === 0 ||
        !row.v2_boundary_requirements.includes("state trace hash"),
    )
  ) {
    errors.push("mission DAG v2 boundary module rows must map scenario, taxonomy, and trace requirements");
  }
  if (!dataset.missionDagV2Boundary.blocked_claims.includes("independent physics backend validated")) {
    errors.push("mission DAG v2 boundary must block independent backend validation");
  }
  if (dataset.roadmapClosure.schema_version !== "roadmap_closure.v1") {
    errors.push("roadmap closure artifact schema_version must be roadmap_closure.v1");
  }
  if (dataset.roadmapClosure.roadmap_item_count !== 15 || dataset.roadmapClosure.roadmap_items.length !== 15) {
    errors.push("roadmap closure artifact must expose exactly 15 roadmap items");
  }
  if (dataset.roadmapClosure.closure_metrics.repo_native_closure_count !== 15) {
    errors.push("roadmap closure metrics must count 15 repo-native closure items");
  }
  if (!dataset.determinismStatus.golden_checksum) {
    errors.push("determinism status must expose golden_checksum");
  }

  if (errors.length > 0) {
    console.error("FAIL: browser dataset validation");
    for (const error of errors) {
      console.error(`- ${error}`);
    }
    process.exitCode = 1;
    return;
  }

  console.log("PASS: browser dataset validation");
  console.log(`- parameter_count: ${dataset.parameters.length}`);
  console.log(`- source_manifest: ${PUBLIC_DATASET_PATHS.parameterDrilldownManifest}`);
  console.log(`- source_frontier: ${PUBLIC_DATASET_PATHS.optimizationFrontier}`);
  console.log(`- source_optimization_v2: ${PUBLIC_DATASET_PATHS.optimizationV2}`);
  console.log(`- source_capsule: ${PUBLIC_DATASET_PATHS.capsuleSurvivabilityLab}`);
  console.log(`- source_capsule_risk_budget: ${PUBLIC_DATASET_PATHS.capsuleRiskBudget}`);
  console.log(`- source_mission_feasibility: ${PUBLIC_DATASET_PATHS.missionFeasibilityScreen}`);
  console.log(`- source_user_mission_runs: ${PUBLIC_DATASET_PATHS.userMissionRunCatalog}`);
  console.log(`- source_runtime_scenario_generation: ${PUBLIC_DATASET_PATHS.runtimeScenarioGeneration}`);
  console.log(`- source_cost_procurement_architecture: ${PUBLIC_DATASET_PATHS.costProcurementArchitectureFeasibility}`);
  console.log(`- source_external_validation_review_pack: ${PUBLIC_DATASET_PATHS.externalValidationReviewPack}`);
  console.log(`- source_public_narrative_hardening: ${PUBLIC_DATASET_PATHS.publicNarrativeHardening}`);
  console.log(`- source_external_validation_execution_ledger: ${PUBLIC_DATASET_PATHS.externalValidationExecutionLedger}`);
  console.log(`- source_independent_physics_backend_comparison: ${PUBLIC_DATASET_PATHS.independentPhysicsBackendComparison}`);
  console.log(`- source_capsule_qualification_evidence_pack: ${PUBLIC_DATASET_PATHS.capsuleQualificationEvidencePack}`);
  console.log(`- source_evidence_upgrade_closure: ${PUBLIC_DATASET_PATHS.evidenceUpgradeClosure}`);
  console.log(`- source_external_reproduction_kit: ${PUBLIC_DATASET_PATHS.externalReproductionKit}`);
  console.log(`- source_external_evidence_intake: ${PUBLIC_DATASET_PATHS.externalEvidenceIntake}`);
  console.log(`- source_external_validation_campaign: ${PUBLIC_DATASET_PATHS.externalValidationCampaign}`);
  console.log(`- source_release_candidate_readiness: ${PUBLIC_DATASET_PATHS.releaseCandidateReadiness}`);
  console.log(`- source_mission_probability_coupling: ${PUBLIC_DATASET_PATHS.missionProbabilityCoupling}`);
  console.log(`- source_uncertainty_interactions: ${PUBLIC_DATASET_PATHS.uncertaintyInteractions}`);
  console.log(`- source_evidence_upgrade_campaign: ${PUBLIC_DATASET_PATHS.evidenceUpgradeCampaign}`);
  console.log(`- source_mission_dag_v2_boundary: ${PUBLIC_DATASET_PATHS.missionDagV2Boundary}`);
  console.log(`- source_roadmap_closure: ${PUBLIC_DATASET_PATHS.roadmapClosure}`);
}

main();
