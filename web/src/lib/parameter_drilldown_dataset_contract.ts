export type EvidenceStatusCode = "OK" | "FAIL";

export interface ParameterBounds {
  minimum: number | null;
  maximum: number | null;
  is_fixed: boolean;
  has_bounds: boolean;
}

export interface ParameterManifestEntry {
  parameter_id: string;
  default_value: unknown;
  bounds: ParameterBounds;
  units: string;
  domain: string;
  mode: string;
  category: string;
  classification: string;
  value_mode: string;
  trust_grade: string;
  affects_core_probability: boolean;
  modules_touched_count: number;
  modules: string[];
  paths_to_metrics: string[];
  evidence_source_ids: string[];
  evidence_status: {
    status: EvidenceStatusCode;
    reason: string | null;
  };
  has_uncertainty: boolean;
  has_source: boolean;
  defensibility_status: "PASS" | "FAIL";
  has_dynamic_trace: boolean;
  static_usage_ref: string;
  evidence_ref: string;
  sensitivity_summary?: string;
  failure_taxonomy_refs?: string[];
}

export interface ParameterDrilldownManifest {
  schema_version: string;
  generator: string;
  public_scope: "public_mission_parameters_only";
  ui_scope: "mission_design_environment_only";
  dynamic_trace_semantics: "module_level_attribution";
  parameter_count: number;
  excluded_internal_parameter_count: number;
  internal_parameter_prefixes_excluded: string[];
  global_evidence_completeness_ratio: number;
  parameters: ParameterManifestEntry[];
  inputs: Array<{ path: string; sha256: string }>;
  artifacts: Array<{ path: string; sha256: string }>;
}

export interface ParameterStaticUsageEntry {
  affects_core_probability: boolean;
  modules: string[];
  paths_to_metrics: string[];
}

export interface ParameterEvidenceSource {
  source_id: string;
  type: string;
  citation: string;
  url: string | null;
  claim_scope: string;
  notes: string;
}

export interface ParameterEvidenceEntry {
  affects_core_probability: boolean;
  category: string;
  classification: string;
  domain: string;
  evidence_source_ids: string[];
  source_ids: string[];
  evidence_sources: ParameterEvidenceSource[];
  justification: string;
  last_reviewed_commit: string;
  mode: string;
  trust_grade: string;
  units: string;
  value_mode: string;
  value_origin_type: "measured" | "assumed" | "derived" | "computed";
  uncertainty_type: "distribution" | "interval" | "fixed" | "model-derived";
  uncertainty_spec: Record<string, unknown>;
  has_uncertainty: boolean;
  derivation_chain: Array<{ type: string; ref: string }>;
  influence_path: string[];
  failure_surface: Array<{
    failure_mode: string;
    dominant_driver_method: string;
    confidence: number;
  }>;
  defensibility_status: "PASS" | "FAIL";
  defensibility_errors: string[];
}

export interface PSuccessInputOrigin {
  origin_type: string;
  driver_parameter_ids: string[];
  source_ids: string[];
  value_origin_types: string[];
  derivation_chain_refs: string[];
}

export interface PSuccessDefensibility {
  schema_version: "p_success_defensibility.v1";
  formula: string;
  inputs: ["p_hit", "p_survival", "p_data_intact"];
  input_origins: Record<string, PSuccessInputOrigin>;
  uncertainty_propagation: "MonteCarlo" | "analytical" | "hybrid";
  mode_constraints: {
    realistic: {
      allow_speculative_parameters: boolean;
      allow_trust_grade_D: boolean;
    };
    speculative: {
      allow_speculative_parameters: boolean;
      allow_trust_grade_D: boolean;
    };
  };
}

export interface FailureSurfaceTimelineEntry {
  stage: "S0" | "S1" | "S2" | "S3";
  summary: string;
  status: "PASS" | "FAIL" | "N/A";
}

export interface FailureSurfaceBaseline {
  schema_version: "failure_surface.v1";
  engine: {
    commit_sha: string;
    determinism_signature: string;
    mode: "realistic" | "speculative" | "dual";
    seed: number;
    scenario_ref: string;
  };
  outcome: {
    outcome_class: "SUCCESS" | "FAIL" | "UNHEALTHY" | "INVALID";
    p_success: number;
    failure_mode: string;
    failure_stage: "S0" | "S1" | "S2" | "S3" | "NONE";
  };
  timeline: FailureSurfaceTimelineEntry[];
  dominant_drivers: {
    method: "OAT" | "delta_p_success" | "taxonomy_attribution";
    confidence: number;
    top3: Array<{
      parameter_id: string;
      reason: string;
      evidence_ref: string;
    }>;
  };
  what_changed_vs_baseline: {
    reference: string;
    p_success_delta: number;
    failure_mode_changed: boolean;
    failure_stage_changed: boolean;
    drivers_added: string[];
    drivers_removed: string[];
  };
}

export interface ObjectiveContract {
  schema_version: "objective_contract.v1";
  engine_commit: string;
  modes: Array<"realistic" | "speculative">;
  objective_sets: {
    realistic: ObjectiveModeSet;
    speculative: ObjectiveModeSet;
  };
  definitions: Record<string, Record<string, unknown>>;
}

interface ObjectivePrimary {
  metric: string;
  maximize: boolean;
}

interface ObjectiveConstraint {
  id: string;
  type: string;
  enforced_by?: string;
}

interface ObjectiveSecondary {
  metric: string;
  maximize: boolean;
  aggregation?: string;
  status?: string;
}

interface ObjectiveAggregation {
  type: string;
  order?: string[];
  dimensions?: string[];
}

interface ObjectiveModeSet {
  primary: ObjectivePrimary;
  constraints?: ObjectiveConstraint[];
  secondary: ObjectiveSecondary[];
  aggregation: ObjectiveAggregation;
}

interface ObjectiveConstraintStatus {
  id: string;
  status: "PASS" | "FAIL";
  details?: Record<string, unknown>;
}

interface ObjectiveModeScore {
  p_success: number;
  objective_vector: number[];
  rank_key: string;
  risk_envelope?: number;
  risk_meta?: {
    method: string;
    quantile: number;
    distribution_size: number;
    q_value: number;
  };
}

export interface ObjectiveScoreBaseline {
  schema_version: "objective_score.v1";
  contract_ref: string;
  contract_snapshot: ObjectiveContract;
  engine: {
    commit_sha: string;
    seed: string | number;
    mode: "dual";
    scenario_ref: string;
  };
  scores: {
    realistic: ObjectiveModeScore;
    speculative: ObjectiveModeScore;
  };
  constraints_status: {
    realistic: ObjectiveConstraintStatus[];
  };
  defensibility: {
    p_success_ref: string;
  };
  determinism_signature: string;
}

export interface OptimizationSearchSpaceEntry {
  parameter_id: string;
  bounds: [number, number];
  baseline_value: number;
  trust_grade: "A" | "B" | "C";
  domain: "realistic";
  affects_core_probability: boolean;
}

export interface OptimizationSearchSpaceArtifact {
  schema_version: "optimization_search_space.v1";
  objective_contract_ref: string;
  mode: "realistic";
  seed: number;
  trust_filter: string;
  excluded_internal_parameter_count: number;
  internal_parameter_prefixes_excluded: string[];
  parameters_considered: OptimizationSearchSpaceEntry[];
  excluded_parameters: Array<{
    parameter_id: string;
    exclusion_reason: string[];
    trust_grade: string;
    domain: string;
  }>;
}

export interface OptimizationFrontierPoint {
  candidate_id: string;
  parameters: Record<string, number>;
  scores: {
    p_success: number;
    objective_vector: number[];
    rank_key: string;
    risk_envelope?: { status: string } | number;
  };
  dominant_drivers: {
    method: string;
    parameter_ids: string[];
  };
  constraint_status: Record<string, string>;
}

export interface OptimizationFrontierArtifact {
  schema_version: "optimization_frontier.v1";
  objective_contract_ref: string;
  risk_envelope_spec_ref?: string;
  engine_commit: string;
  mode: "realistic";
  seed: number;
  method: string;
  dimensions?: string[];
  evaluation_count: number;
  points: OptimizationFrontierPoint[];
  pareto_frontier_indices: number[];
  determinism_signature: string;
}

export interface OptimizationV2Axis {
  id: "p_success" | "risk_envelope" | "qualification_gap" | "cost_proxy";
  direction: "maximize" | "minimize";
  status: "computed" | "screening_proxy";
  source_ref: string;
  method?: string;
}

export interface OptimizationV2Candidate {
  candidate_id: string;
  source_candidate_id: string;
  scores: {
    p_success: number;
    risk_envelope: number;
    qualification_gap: number;
    cost_proxy: number;
    objective_vector: [number, number, number, number];
    rank_key: "pareto";
  };
  axis_explainability: {
    qualification_gap: Record<string, unknown>;
    cost_proxy: Record<string, unknown>;
  };
  source_constraint_status: Record<string, string>;
  dominant_drivers: {
    method: string;
    parameter_ids: string[];
    excluded_internal_parameter_count: number;
  };
  source_v1_pareto_member: boolean;
  pareto_frontier_member: boolean;
}

export interface OptimizationV2Artifact {
  schema_version: "optimization_v2_frontier.v1";
  generator: string;
  mode: "realistic";
  public_scope: "optimization_v2_four_axis_decision_surface";
  non_certification_notice: boolean;
  axis_contract: {
    aggregation_policy: "pareto_first_no_hidden_weighted_sum";
    axes: OptimizationV2Axis[];
    blocked_claims: string[];
  };
  candidate_count: number;
  frontier_candidate_count: number;
  candidates: OptimizationV2Candidate[];
  pareto_frontier_candidate_ids: string[];
  rollup: {
    dimension_count: number;
    axis_ids: ["p_success", "risk_envelope", "qualification_gap", "cost_proxy"];
    aggregation_policy: "pareto_first_no_hidden_weighted_sum";
    source_frontier_candidate_count: number;
    source_frontier_pareto_count: number;
    global_optimum_claimed: boolean;
    hidden_weighted_sum_used: boolean;
    calibrated_cost_model_available: boolean;
    qualification_complete: boolean;
    top_candidate_id: string | null;
  };
  external_evidence_gaps: string[];
  blocked_claims: string[];
  interpretation_limits: string[];
  determinism_signature: string;
}

export interface DeterminismStatusSnapshot {
  last_verified_commit_sha?: string;
  engine_version?: string;
  schema_version?: string;
  golden_checksum?: string;
}

export interface BrowserSourceArtifact {
  path: string;
  sha256: string;
}

export interface PublicDatasetPaths {
  capsuleRiskBudget: string;
  capsuleSurvivabilityLab: string;
  determinismStatus: string;
  failureSurfaceBaseline: string;
  parameterDrilldownManifest: string;
  parameterEvidenceIndex: string;
  objectiveContract: string;
  objectiveScoreBaseline: string;
  optimizationFrontier: string;
  optimizationV2: string;
  optimizationSearchSpace: string;
  pSuccessDefensibility: string;
  parameterStaticUsageGraph: string;
  missionFeasibilityScreen: string;
  userMissionRunCatalog: string;
  runtimeScenarioGeneration: string;
  costProcurementArchitectureFeasibility: string;
  externalValidationReviewPack: string;
  publicNarrativeHardening: string;
  externalValidationExecutionLedger: string;
  independentPhysicsBackendComparison: string;
  capsuleQualificationEvidencePack: string;
  evidenceUpgradeClosure: string;
  externalReproductionKit: string;
  externalEvidenceIntake: string;
  externalValidationCampaign: string;
  releaseCandidateReadiness: string;
  missionProbabilityCoupling: string;
  uncertaintyInteractions: string;
  evidenceUpgradeCampaign: string;
  missionDagV2Boundary: string;
  roadmapClosure: string;
}

export interface ExternalReviewDeliverable {
  id: string;
  status: string;
  acceptance_fields: string[];
  blocked_claim: string;
}

export interface ExternalReviewCase {
  id: string;
  title: string;
  status: string;
  source_inputs: string[];
  review_questions: string[];
  expected_failure_modes: string[];
  external_deliverable_ids: string[];
  independent_result_available: boolean;
  acceptance_record_required: Record<string, boolean>;
  blocked_claims: string[];
}

export interface ExternalValidationReviewPackArtifact {
  schema_version: "external_validation_review_pack.v1";
  generator: string;
  public_scope: "external_validation_independent_review_pack";
  non_certification_notice: boolean;
  review_pack_status: string;
  roadmap_item: {
    id: string;
    title: string;
    status?: string;
    implementation_mode?: string;
    summary?: string;
    external_evidence_gaps?: string[];
    claim_boundary?: string;
  };
  required_external_deliverables: ExternalReviewDeliverable[];
  review_case_count: number;
  review_cases: ExternalReviewCase[];
  dag_review_surface: Record<string, unknown>;
  evidence_review_surface: Record<string, unknown>;
  runtime_review_surface: Record<string, unknown>;
  cost_procurement_review_surface: Record<string, unknown>;
  rollup: {
    review_case_count: number;
    external_deliverable_count: number;
    third_party_review_completed: boolean;
    independent_reproduction_completed: boolean;
    independent_benchmark_completed: boolean;
    high_fidelity_state_trace_complete: boolean;
    external_red_team_completed: boolean;
    external_validation_claimed: boolean;
    all_cases_require_external_review: boolean;
  };
  blocked_claims: string[];
  external_evidence_gaps: string[];
  interpretation_limits: string[];
  determinism_signature?: string;
}

export interface PublicNarrativeSurface {
  surface_id: string;
  source_ref: string;
  covered_rule_ids: string[];
  unsafe_public_overclaim_count: number;
  artifact_only_rendering_required: boolean;
}

export interface PublicNarrativeClaimRule {
  id: string;
  surface: string;
  claim_domain: string;
  rule_type: "forbid" | "require_qualifier" | "allow_with_boundary";
  forbidden_terms: string[];
  required_qualifiers: string[];
  allowed_replacements: string[];
  source_artifact_refs: string[];
  evidence_gap_refs: string[];
  severity: "blocking";
  validator_action: "fail_public_release";
  rationale: string;
}

export interface PublicNarrativeReplacementGuidance {
  forbidden_claim: string;
  replacement: string;
  requires_external_evidence_note: boolean;
  rule_id: string;
}

export interface PublicNarrativeSourceClaim {
  source_ref: string;
  required_qualifiers_present: boolean;
  guarded_forbidden_claim_mentions: string[];
  unsafe_public_overclaim_count: number;
  manual_review_required: boolean;
}

export interface PublicNarrativeHardeningArtifact {
  schema_version: "public_narrative_hardening.v1";
  generator: string;
  public_scope: "public_claim_boundary_contract";
  non_certification_notice: boolean;
  roadmap_item_ref: "roadmap-15";
  review_status: string;
  claim_rule_count: number;
  blocked_claim_count: number;
  required_qualifier_count: number;
  public_surface_count: number;
  public_surfaces: PublicNarrativeSurface[];
  claim_rules: PublicNarrativeClaimRule[];
  forbidden_public_claims: string[];
  required_public_concepts: string[];
  allowed_phrasing: string[];
  replacement_guidance: PublicNarrativeReplacementGuidance[];
  source_claim_matrix: PublicNarrativeSourceClaim[];
  source_rollups: Record<string, unknown>;
  external_evidence_gaps: string[];
  browser_boundary: {
    artifact_only_rendering: boolean;
    client_side_claim_recomputation_allowed: boolean;
    blocked_claim_suppression_allowed: boolean;
    external_gap_softening_allowed: boolean;
  };
  rollup: {
    unsafe_public_overclaim_count: number;
    all_required_concepts_present: boolean;
    external_wording_audit_completed: boolean;
    audience_testing_completed: boolean;
    legal_review_completed: boolean;
    public_claim_approval_completed: boolean;
    external_validation_claimed: boolean;
    third_party_review_completed: boolean;
    independent_reproduction_completed: boolean;
    procurement_grade_estimate_available: boolean;
    vendor_quote_count: number;
    global_optimum_claimed: boolean;
    full_mission_probability_closed_count: number;
    independent_backend_complete: boolean;
    source_correctness_claimed: boolean;
    trust_grades_upgraded_automatically: boolean;
    persistent_reviewed_archive_claimed: boolean;
  };
  interpretation_limits: string[];
  determinism_signature?: string;
}

export interface MissionDagV2BoundaryRow {
  module_id: string;
  module_type: string;
  module_version: string;
  domain: string;
  entrypoint: string;
  input_schema_ref: string;
  output_schema_ref: string;
  scenario_node_ids: string[];
  failure_taxonomy_ids: string[];
  current_v1_support: {
    wrapper_over_reduced_order_baseline: boolean;
    module_io_schema_declared: boolean;
    hashchained_module_artifacts: boolean;
    failure_taxonomy_mapping_declared: boolean;
    independent_backend_id_declared: boolean;
    high_fidelity_state_trace_available: boolean;
    cross_backend_comparison_available: boolean;
  };
  v2_boundary_requirements: string[];
  open_external_evidence_gaps: string[];
  blocked_claims: string[];
}

export interface MissionDagV2BoundaryArtifact {
  schema_version: "mission_dag_v2_boundary.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  module_count: number;
  registry_version: "v1";
  scenario_ref: string;
  failure_taxonomy_ref: string;
  module_boundaries: MissionDagV2BoundaryRow[];
  rollup: {
    module_count: number;
    module_io_schema_contract_available: boolean;
    hashchain_contract_available: boolean;
    failure_taxonomy_mapping_module_count: number;
    state_trace_contract_complete: boolean;
    independent_backend_complete: boolean;
    high_fidelity_state_traces_available: boolean;
    cross_backend_comparison_available: boolean;
    flight_ready_module_claimed: boolean;
    external_reproduction_completed: boolean;
  };
  external_evidence_gaps: string[];
  blocked_claims: string[];
  interpretation_limits: string[];
  determinism_signature: string;
}

export type CapsuleOutcomeBand = "nominal" | "stressed" | "critical";

export interface CapsuleControlOption {
  id: string;
  label: string;
  detail: string;
}

export interface CapsuleStageOutput {
  stage: "S0" | "S1" | "S2" | "S3";
  label: string;
  status: "PASS" | "WATCH" | "FAIL";
  summary: string;
}

export interface CapsuleSurvivalRow {
  rowId: string;
  artifactDigest: string;
  targetId: string;
  timeId: string;
  velocityId: string;
  capsuleId: string;
  distanceLy: number;
  velocityKmS: number;
  flightYears: number;
  output: {
    survivalProbability: number;
    survivalP05: number;
    survivalP95: number;
    structureProbability: number;
    dataIntegrityProbability: number;
    shieldMargin: number;
    thermalMargin: number;
    outcomeBand: CapsuleOutcomeBand;
    verdict: string;
    confidence: string;
  };
  stages: CapsuleStageOutput[];
  driverLabels: string[];
  scenarioBands: Record<string, Record<string, number>>;
  assumptionSummary: Record<string, number>;
  uncertaintyDrivers: Array<{
    name: string;
    target: string;
    provenance: string;
  }>;
}

export interface CapsuleSurvivabilityLabArtifact {
  schema_version: "capsule_survivability_lab.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  source_paths: Record<string, string>;
  source_artifacts: BrowserSourceArtifact[];
  source_index: Array<{
    source_id: string;
    label: string;
    url: string;
    trust_class: "A" | "B" | "C" | "D";
    stable_value: string;
    applicability: string;
  }>;
  source_data: Array<Record<string, unknown>>;
  capsule_design: Record<string, unknown>;
  controls: {
    targets: CapsuleControlOption[];
    timeHorizons: CapsuleControlOption[];
    velocityBands: CapsuleControlOption[];
    capsuleProfiles: CapsuleControlOption[];
  };
  rows: CapsuleSurvivalRow[];
}

export interface CapsuleRiskBudgetArtifact {
  schema_version: "capsule_risk_budget.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  source_artifact_ref: string;
  source_artifact_sha256: string;
  sample_count: number;
  seed: number;
  sampling_method: string;
  default_row_id: string;
  risk_budget_count: number;
  source_policy?: Record<string, unknown>;
  failure_modes?: Array<Record<string, unknown>>;
  qualification_roadmap?: Array<Record<string, unknown>>;
  uncertainty_dimensions: Array<Record<string, unknown>>;
  attack_modes:
    | Array<Record<string, unknown>>
    | {
        default_row_id?: string;
        modes?: Array<Record<string, unknown>>;
      };
  risk_budgets?: Array<Record<string, unknown>>;
  interpretation_limits?: string[];
}

export interface MissionFeasibilityRow {
  id: string;
  source_capsule_row_id: string;
  target_id: string;
  target_label: string;
  target_detail: string;
  distance_ly: number;
  velocity_id: string;
  velocity_label: string;
  velocity_detail: string;
  velocity_km_s: number;
  velocity_fraction_c: number;
  flight_years: number;
  time_horizon_class: string;
  black_hole_screen: Record<string, unknown>;
  dust_screen: Record<string, unknown>;
  gas_screen: Record<string, unknown>;
  radiation_material_hooks: Record<string, unknown>;
  capsule_risk_budget_link: {
    matched: boolean;
    row_id: string;
    attack_mode_id?: string;
    survival_p05?: number;
    survival_p50?: number;
    survival_p95?: number;
    data_integrity_p50?: number;
    evidence_gap_ids?: string[];
    blocking_claims?: string[];
  };
  cost_energy_proxy: Record<string, unknown>;
  feasibility: {
    status: string;
    blockers: string[];
    non_certification_notice: true;
  };
  external_evidence_gaps: string[];
  blocked_claims: string[];
}

export interface MissionFeasibilityScreenArtifact {
  schema_version: "mission_feasibility_screen.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  target_count: number;
  velocity_count: number;
  scenario_count: number;
  default_scenario_id: string;
  default_black_hole_flight_years: number;
  capsule_risk_budget_match_count: number;
  constants: Record<string, unknown>;
  scenario_rows: MissionFeasibilityRow[];
  interpretation_limits: string[];
}

export interface UserMissionRunRow {
  run_id: string;
  selection_hash: string;
  selection: {
    feasibility_row_id: string;
    source_capsule_row_id: string;
    target_id: string;
    target_label: string;
    target_detail: string;
    distance_ly: number;
    velocity_id: string;
    velocity_label: string;
    velocity_detail: string;
    velocity_km_s: number;
    velocity_fraction_c: number;
    flight_years: number;
    time_horizon_class: string;
  };
  source_refs: Record<string, unknown>;
  probability_snapshot: {
    p_hit_policy: string;
    capsule_survival_p05?: number;
    capsule_survival_p50?: number;
    capsule_survival_p95?: number;
    data_integrity_p50?: number;
    capsule_data_coupled_p50?: number;
    claim_boundary: string;
  };
  feasibility_status: {
    status: string;
    blockers: string[];
    non_certification_notice: true;
  };
  exposure_snapshot: Record<string, unknown>;
  cost_energy_proxy: Record<string, unknown>;
  external_evidence_gaps: string[];
  blocked_claims: string[];
  runtime_pack_template: {
    script: string;
    output_root: string;
    args: Record<string, unknown>;
    writes_tracked_files: false;
  };
}

export interface UserMissionRunCatalogArtifact {
  schema_version: "user_mission_run_catalog.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  run_store_policy: Record<string, unknown>;
  target_count: number;
  velocity_count: number;
  run_count: number;
  default_run_id: string;
  target_ids: string[];
  velocity_ids: string[];
  run_rows: UserMissionRunRow[];
  interpretation_limits: string[];
}

export interface RuntimeScenarioGenerationRow {
  run_id: string;
  selection_hash: string;
  target_id: string;
  target_label: string;
  velocity_id: string;
  velocity_label: string;
  flight_years: number;
  time_horizon_class: string;
  command_preview: string;
  cli_args: Record<string, unknown>;
  compiled_scenario_delta: Record<string, unknown>;
  run_pack_contract: {
    output_root: string;
    summary_schema_version: string;
    output_files: string[];
    validation_function: string;
    determinism_flag: string;
    writes_tracked_files: false;
  };
  ownership_boundary: {
    user_owned: true;
    remote_execution: false;
    persistent_reviewed_archive: false;
    tracked_by_default: false;
  };
  external_evidence_gaps: string[];
  blocked_claims: string[];
}

export interface RuntimeScenarioGenerationArtifact {
  schema_version: "runtime_scenario_generation.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  selection_axes: {
    target_count: number;
    velocity_count: number;
    target_options: Array<Record<string, unknown>>;
    velocity_options: Array<Record<string, unknown>>;
    supported_modes: string[];
    default_seed: number;
    default_run_id: string;
  };
  scenario_generation_contract: {
    source_catalog: string;
    runner: string;
    allowed_user_inputs: string[];
    scenario_compiler: string;
    forbidden_runtime_claims: string[];
    browser_execution_policy: string;
  };
  run_pack_contract: {
    output_root: string;
    tracked_by_default: false;
    writes_tracked_files: false;
    summary_schema_version: string;
    output_files: string[];
    required_summary_fields: string[];
  };
  generation_row_count: number;
  generation_rows: RuntimeScenarioGenerationRow[];
  rollup: {
    rows_with_command_preview: number;
    rows_writing_tracked_files: number;
    remote_execution_claimed: false;
    persistent_reviewed_archive_claimed: false;
    determinism_flag_required: true;
  };
  blocked_claims: string[];
  interpretation_limits: string[];
}

export interface CostArchitectureRow {
  row_id: string;
  source_feasibility_row_id: string;
  source_capsule_row_id: string;
  is_default_reference: boolean;
  target_id: string;
  target_label: string;
  velocity_id: string;
  velocity_label: string;
  flight_years: number;
  time_horizon_class: string;
  capsule_mass_kg: number;
  capsule_kinetic_energy_j: number;
  relative_to_23_17_km_s: number;
  cost_proxy_score: number;
  procurement_status: "external_required";
  architecture_feasibility_status: "review_required" | "blocked_external_evidence";
  scenario_feasibility_status: string;
  review_blockers: string[];
  claim_boundary: string;
  external_evidence_gaps: string[];
  blocked_claims: string[];
}

export interface CostProcurementArchitectureFeasibilityArtifact {
  schema_version: "cost_procurement_architecture_feasibility.v1";
  generator: string;
  public_scope: "roadmap_13_cost_procurement_architecture_screen";
  non_certification_notice: true;
  roadmap_item: {
    id: "roadmap-13";
    title: string;
    implementation_mode: "tracked_cost_procurement_architecture_screen";
    summary: string;
    external_evidence_gaps: string[];
  };
  claim_boundaries: {
    artifact_status: string;
    cost_status: "order_of_magnitude_proxy_only";
    procurement_status: "external_required";
    architecture_status: string;
    browser_policy: string;
  };
  mass_budget: Record<string, unknown>;
  cost_model: {
    method: string;
    model: string;
    currency_year: null;
    calibrated_cost_model_available: false;
    cost_boundary: string;
    capsule_mass_kg: number;
    qualification_cost_proxy_musd: number;
    launch_architecture_cost_proxy_musd: number;
    optimization_cost_proxy_min: number | null;
    optimization_cost_proxy_max: number | null;
    components: Array<Record<string, unknown>>;
  };
  procurement_gates: Array<{
    id: string;
    status: "external_required";
    required_evidence: string[];
    blocked_claim: string;
  }>;
  architecture_row_count: number;
  architecture_rows: CostArchitectureRow[];
  architecture_options: Array<Record<string, unknown>>;
  optimization_cost_axis: {
    axis_id: "cost_proxy";
    status: "screening_proxy";
    method?: string;
    source_ref?: string;
    candidate_count?: number;
    frontier_candidate_count?: number;
    min_score: number | null;
    max_score: number | null;
    top_candidate_id?: string | null;
    top_candidate_cost_proxy: number | null;
    top_candidate_qualification_gap: number | null;
    calibrated_cost_model_available: false;
    qualification_complete: false;
    blocked_claims: string[];
    external_evidence_gaps: string[];
  };
  rollup: {
    row_count: number;
    procurement_grade_estimate_available: false;
    vendor_quote_count: 0;
    launch_vehicle_selected: false;
    architecture_selected_for_flight: false;
    calibrated_cost_model_available: false;
    qualification_complete: false;
    all_rows_review_required: true;
    external_gate_count: number;
  };
  blocked_claims: string[];
  external_evidence_gaps: string[];
  interpretation_limits: string[];
}

export interface MissionProbabilityFactor {
  factor_id: "target_delivery" | "environment_path" | "capsule_survival" | "data_integrity" | "recovery_readout";
  label: string;
  status: "external_required" | "repo_estimated_review_proxy";
  value_p50: number | null;
  evidence_class: string;
  source_ref: string | null;
  external_evidence_gap: string | null;
}

export interface MissionProbabilityCouplingRow {
  coupling_id: string;
  run_id: string;
  selection_hash: string;
  target_id: string;
  target_label: string;
  velocity_id: string;
  velocity_label: string;
  flight_years: number;
  time_horizon_class: string;
  source_refs: Record<string, unknown>;
  formula: string;
  factor_budget: MissionProbabilityFactor[];
  closed_factor_count: number;
  open_external_factor_count: number;
  closed_capsule_data_probability: {
    p05: number;
    p50: number;
    p95: number;
    status: "review_proxy_only";
    claim_boundary: string;
  };
  full_mission_probability: {
    p05: null;
    p50: null;
    p95: null;
    status: "not_closed_external_factors_open";
    blocking_open_factors: string[];
  };
  risk_budget_snapshot: Record<string, unknown>;
  dag_coupling: {
    status: string;
    runtime_script: string;
    mission_dag_scenario: string;
    manifest_hash_policy: string;
    writes_tracked_files: false;
  };
  dag_snapshot: {
    status: "PASS" | "FAIL";
    mode: "dual";
    seed: number;
    compiled_mission_scenario_sha256: string;
    execution_modes: string[];
    manifest_hash: string;
    module_artifact_count: number;
    hashchain_status: "PASS" | "FAIL";
    failure_taxonomy_status: "PASS" | "FAIL";
    used_failure_ids: string[];
    mode_summaries: Record<
      string,
      {
        mode: string;
        final_metrics: Record<string, number>;
        core_probability: number;
        trust_weighted_score: number;
        speculative_parameters_used: string[];
      }
    >;
    determinism_policy: string;
  };
  external_evidence_gaps: string[];
  blocked_claims: string[];
  verdict: "review_required";
  non_certification_notice: true;
}

export interface MissionProbabilityCouplingArtifact {
  schema_version: "mission_probability_coupling.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  formula: string;
  factor_policy: Record<string, unknown>;
  coupling_count: number;
  default_coupling_id: string;
  default_run_id: string;
  coupling_rows: MissionProbabilityCouplingRow[];
  rollup: {
    rows_with_full_mission_probability_closed: 0;
    rows_with_review_proxy: number;
    open_external_factor_total: number;
    blocked_claims: string[];
  };
  interpretation_limits: string[];
}

export interface UncertaintyMainEffect {
  entry_id: string;
  parameter_id: string;
  distribution: string;
  units: string;
  mode: string;
  category: string;
  trust_grade: string;
  source_rationale: string;
  stress_values: {
    low: number;
    nominal: number;
    high: number;
  };
  p_success_low: number;
  p_success_nominal: number;
  p_success_high: number;
  effect_low: number;
  effect_high: number;
  max_abs_effect: number;
  sensitivity_summary: string | null;
  claim_boundary: string;
}

export interface UncertaintyPairInteraction {
  pair_id: string;
  parameter_ids: [string, string];
  status: "external_correlation_evidence_required";
  baseline_p_success: number;
  stress_p_success: {
    low_low: number;
    low_high: number;
    high_low: number;
    high_high: number;
  };
  main_effect_reference: Record<
    string,
    {
      effect_low: number;
      effect_high: number;
    }
  >;
  interaction_residual: {
    low_low: number;
    low_high: number;
    high_low: number;
    high_high: number;
    max_abs: number;
    classification: "negligible" | "weak" | "material";
  };
  correlation: {
    rho: null;
    status: "external_correlation_evidence_required";
    evidence_gap_id: string;
  };
  claim_boundary: string;
}

export interface UncertaintyInteractionsArtifact {
  schema_version: "uncertainty_interactions.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  mode: "realistic";
  method: Record<string, unknown>;
  baseline: {
    p_success: number;
    p_hit: number;
    p_survive: number;
    p_data_intact: number;
  };
  uncertainty_entry_count: number;
  interaction_pair_count: number;
  main_effects: UncertaintyMainEffect[];
  pair_interactions: UncertaintyPairInteraction[];
  rollup: {
    dominant_pair_id: string | null;
    material_pair_count: number;
    material_pair_ids: string[];
    pairs_requiring_external_correlation_evidence: number;
    validated_correlation_count: 0;
    full_uncertainty_interaction_closure: false;
  };
  external_evidence_gaps: string[];
  blocked_claims: string[];
  interpretation_limits: string[];
}

export interface EvidenceUpgradeCampaignRow {
  campaign_id: string;
  parameter_id: string;
  visibility: "public";
  current_trust_grade: "A" | "B" | "C" | "D";
  target_trust_grade: "A" | "B" | "maintain_A" | "keep_speculative_isolated";
  mode: string;
  classification: string;
  category: string;
  affects_core_probability: boolean;
  public_surfaces: string[];
  evidence_source_ids: string[];
  source_types: string[];
  source_quality_gaps: string[];
  value_origin_type: string | null;
  has_uncertainty: boolean;
  defensibility_status: "PASS" | "FAIL" | null;
  sensitivity: {
    influence_score: number | null;
    delta_p_success: number | null;
  };
  priority_score: number;
  gap_types: string[];
  recommended_actions: string[];
  acceptance_criteria: string[];
  blocked_claims: string[];
}

export interface EvidenceUpgradeCampaignArtifact {
  schema_version: "evidence_upgrade_campaign.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  campaign_policy: Record<string, unknown>;
  claim_count: number;
  public_campaign_count: number;
  internal_audit_count: number;
  trust_distribution: Record<string, number>;
  public_trust_distribution: Record<string, number>;
  source_type_distribution: Record<string, number>;
  top_priority_count: number;
  public_top_priorities: EvidenceUpgradeCampaignRow[];
  internal_audit_rollup: {
    visibility: "internal";
    row_count: number;
    trust_distribution: Record<string, number>;
    public_surface_policy: string;
  };
  rollup: Record<string, unknown>;
  external_evidence_gaps: string[];
  blocked_claims: string[];
  interpretation_limits: string[];
}

export interface RoadmapClosureItem {
  id: string;
  title: string;
  status: "repo_native_closure_implemented_external_evidence_open";
  implementation_mode: string;
  summary: string;
  artifacts: string[];
  validators: string[];
  model_summary_ref: string;
  external_evidence_gaps: string[];
  acceptance_criteria: string[];
  false_claims_blocked: string[];
  non_certification_notice: true;
  claim_boundary: string;
}

export interface RoadmapClosureArtifact {
  schema_version: "roadmap_closure.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  roadmap_item_count: number;
  closure_metrics: {
    repo_native_closure_count: number;
    external_evidence_gap_count: number;
    non_certification_notice_count: number;
    trust_grade_distribution: Record<string, number>;
  };
  roadmap_items: RoadmapClosureItem[];
  model_summaries: Record<string, unknown>;
  qualification_tracks: Record<string, unknown>;
  runtime_runs: Record<string, unknown>;
  review_pack: Record<string, unknown>;
  public_narrative: {
    status?: string;
    artifact_ref?: string;
    schema_version?: string;
    review_status?: string;
    claim_rule_count?: number;
    blocked_claim_count?: number;
    required_qualifier_count?: number;
    public_surface_count?: number;
    unsafe_public_overclaim_count?: number;
    external_wording_audit_completed?: boolean;
    audience_testing_completed?: boolean;
    legal_review_completed?: boolean;
    public_claim_approval_completed?: boolean;
    all_required_concepts_present?: boolean;
    forbidden_claims?: string[];
    required_claims?: string[];
    allowed_phrasing?: string[];
    browser_boundary?: Record<string, unknown>;
    external_evidence_gaps?: string[];
  };
}

export interface ExternalValidationExecutionCase {
  review_case_id: string;
  title: string;
  execution_status: "external_required";
  external_record_status: "no_external_record_uploaded";
  source_inputs: string[];
  external_deliverable_ids: string[];
  required_record_schema: Record<string, boolean>;
  blocked_claims: string[];
}

export interface ExternalValidationExecutionLedgerArtifact {
  schema_version: "external_validation_execution_ledger.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  execution_ledger_status: string;
  review_pack_ref: string;
  required_external_deliverables: ExternalReviewDeliverable[];
  review_case_count: number;
  execution_record_count: number;
  external_record_count: number;
  execution_cases: ExternalValidationExecutionCase[];
  acceptance_record_policy: Record<string, unknown>;
  rollup: {
    review_case_count: number;
    execution_record_count: number;
    external_record_count: number;
    all_cases_require_external_records: boolean;
    third_party_records_uploaded: boolean;
    external_validation_completed: boolean;
    independent_reproduction_completed: boolean;
    external_red_team_completed: boolean;
  };
  blocked_claims: string[];
  external_evidence_gaps: string[];
  interpretation_limits: string[];
  determinism_signature?: string;
}

export interface IndependentPhysicsAnalyticCheck {
  check_id: string;
  description: string;
  units: string;
  analytic_value: number;
  artifact_value: number;
  absolute_error: number;
  relative_error: number;
  status: "match";
}

export interface IndependentPhysicsBackendComparisonArtifact {
  schema_version: "independent_physics_backend_comparison.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  comparison_status: string;
  backend_boundary: Record<string, unknown>;
  default_scenario_ref: string;
  analytic_check_count: number;
  analytic_checks: IndependentPhysicsAnalyticCheck[];
  dag_boundary_snapshot: Record<string, unknown>;
  rollup: {
    analytic_check_count: number;
    all_repo_analytic_checks_match: boolean;
    max_relative_error: number;
    independent_external_backend_complete: boolean;
    cross_backend_comparison_completed: boolean;
    high_fidelity_state_trace_complete: boolean;
    independent_physics_backend_validated: boolean;
  };
  blocked_claims: string[];
  external_evidence_gaps: string[];
  interpretation_limits: string[];
  determinism_signature?: string;
}

export interface CapsuleQualificationEvidencePackArtifact {
  schema_version: "capsule_qualification_evidence_pack.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  capsule_design: Record<string, unknown>;
  material_count: number;
  layer_count: number;
  material_stack: Array<Record<string, unknown>>;
  mass_closure: {
    configured_capsule_mass_kg: number;
    component_mass_kg: number;
    declared_margin_kg: number;
    absolute_delta_kg: number;
    within_declared_margin: boolean;
    closure_rule?: string;
  };
  survivability_model_inputs: Record<string, unknown>;
  failure_modes: Array<Record<string, unknown>>;
  qualification_test_count: number;
  qualification_tests: Array<Record<string, unknown>>;
  lab_record_count: number;
  rollup: {
    material_count: number;
    layer_count: number;
    qualification_test_count: number;
    lab_record_count: number;
    mass_budget_closed: boolean;
    all_tests_external_required: boolean;
    qualification_complete: boolean;
    flight_ready_claimed: boolean;
    certified_hardware_survivability: boolean;
  };
  blocked_claims: string[];
  external_evidence_gaps: string[];
  interpretation_limits: string[];
  determinism_signature?: string;
}

export interface EvidenceUpgradeClosureArtifact {
  schema_version: "evidence_upgrade_closure.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  campaign_ref: string;
  closure_status: string;
  closure_cycle_count: number;
  closure_rows: Array<Record<string, unknown> & { parameter_id: string; closure_status: string }>;
  rollup: {
    closure_cycle_count: number;
    speculative_quarantine_count: number;
    external_required_count: number;
    external_source_upgrade_count: number;
    trust_grade_promotion_count: number;
    source_correctness_claimed: boolean;
    trust_grades_upgraded_automatically: boolean;
    realistic_D_grade_public_rows_closed: number;
  };
  blocked_claims: string[];
  external_evidence_gaps: string[];
  interpretation_limits: string[];
  determinism_signature?: string;
}

export interface ExternalReproductionKitArtifact {
  schema_version: "external_reproduction_kit.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  kit_status: string;
  review_case_count: number;
  review_cases: Array<Record<string, unknown>>;
  primary_tracks: Array<Record<string, unknown>>;
  pack_contract: {
    export_cli?: string;
    pack_validator?: string;
    default_archive_name?: string;
    output_root_semantics?: string;
    pack_file_count?: number;
    pack_files?: string[];
    commands?: string[];
  };
  readiness_snapshot: Record<string, unknown>;
  rollup: {
    external_reproduction_kit_ready: boolean;
    export_cli_available: boolean;
    record_schema_available: boolean;
    external_execution_completed: boolean;
    first_real_external_record_present: boolean;
    fake_external_records_accepted: boolean;
    external_validation_completed: boolean;
    independent_backend_validated: boolean;
  };
  blocked_claims: string[];
  external_evidence_gaps: string[];
  interpretation_limits: string[];
  determinism_signature?: string;
}

export interface ExternalEvidenceIntakeArtifact {
  schema_version: "external_evidence_intake.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  intake_status: string;
  record_schema_ref: string;
  external_records_dir: string;
  record_count: number;
  accepted_record_count: number;
  rejected_record_count: number;
  accepted_records: Array<Record<string, unknown>>;
  rejected_records: Array<Record<string, unknown>>;
  record_templates: Array<Record<string, unknown>>;
  validation_policy: Record<string, boolean>;
  rollup: {
    intake_contract_ready: boolean;
    record_schema_available: boolean;
    record_count: number;
    accepted_record_count: number;
    rejected_record_count: number;
    first_real_external_record_present: boolean;
    self_signed_records_accepted: boolean;
    external_validation_completed: boolean;
    independent_reproduction_completed: boolean;
    independent_backend_validated: boolean;
    qualification_complete: boolean;
    certification_go: boolean;
    flight_readiness_go: boolean;
  };
  blocked_claims: string[];
  external_evidence_gaps: string[];
  interpretation_limits: string[];
  determinism_signature?: string;
}

export interface ExternalValidationCampaignArtifact {
  schema_version: "external_validation_campaign.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  campaign_status: string;
  campaign_policy: {
    records_do_not_directly_unlock_claims: boolean;
    proof_promotion_requires_followup_review: boolean;
    repo_native_artifacts_are_not_external_records?: boolean;
  };
  workstream_count: number;
  workstreams: Array<{
    workstream_id: string;
    status: string;
    evidence_ref: string;
    current_accepted_record_count: number;
  }>;
  independent_backend_execution_plan: Record<string, unknown>;
  line_of_sight_environment_model: Record<string, unknown>;
  capsule_qualification_program: Record<string, unknown>;
  proof_promotion_review: {
    status: string;
    requires_followup_review: boolean;
    automatic_claim_promotion_allowed: boolean;
    promoted_claims: string[];
    rollup: Record<string, unknown>;
    claim_reviews: Array<Record<string, unknown>>;
  };
  public_evidence_dossier: {
    status: string;
    sections: string[];
    shows_blocked_claims: boolean;
    marketing_claim_surface: boolean;
    certification_language_allowed: boolean;
    public_claim_approval_completed: boolean;
  };
  rollup: {
    campaign_ready: boolean;
    workstream_count: number;
    accepted_record_count: number;
    accepted_external_record_count: number;
    first_real_external_record_present: boolean;
    external_validation_completed: boolean;
    independent_backend_validated: boolean;
    line_of_sight_model_complete: boolean;
    qualification_complete: boolean;
    proof_promotion_applied: boolean;
    public_dossier_ready: boolean;
    certification_go: boolean;
  };
  blocked_claims: string[];
  external_evidence_gaps: string[];
  interpretation_limits: string[];
  determinism_signature?: string;
}

export interface ReleaseCandidateReadinessArtifact {
  schema_version: "release_candidate_readiness.v1";
  generator: string;
  public_scope: string;
  non_certification_notice: true;
  release_candidate_status: string;
  component_rollups: Record<string, unknown>;
  repository_gates: Array<Record<string, unknown>>;
  rollup: {
    repo_publication_candidate_ready: boolean;
    certification_go: boolean;
    flight_readiness_go: boolean;
    external_validation_completed: boolean;
    qualification_complete: boolean;
    independent_backend_validated: boolean;
    trust_grade_promotions_completed: boolean;
    public_claim_boundary_ready: boolean;
  };
  blocked_claims: string[];
  external_evidence_gaps: string[];
  interpretation_limits: string[];
  determinism_signature?: string;
}

export interface BrowserDatasetPayload {
  schema_version: "browser_dataset.v1";
  generator: string;
  public_scope: "tracked_generated_only";
  source_paths: PublicDatasetPaths;
  source_artifacts: BrowserSourceArtifact[];
  determinism_status: DeterminismStatusSnapshot;
  failure_surface_baseline: FailureSurfaceBaseline;
  manifest: ParameterDrilldownManifest;
  static_usage_graph: Record<string, ParameterStaticUsageEntry>;
  evidence_index: Record<string, ParameterEvidenceEntry>;
  p_success_defensibility: PSuccessDefensibility;
  objective_contract: ObjectiveContract;
  objective_score_baseline: ObjectiveScoreBaseline;
  optimization_search_space: OptimizationSearchSpaceArtifact;
  optimization_frontier: OptimizationFrontierArtifact;
  optimization_v2: OptimizationV2Artifact;
  capsule_survivability_lab: CapsuleSurvivabilityLabArtifact;
  capsule_risk_budget: CapsuleRiskBudgetArtifact;
  mission_feasibility_screen: MissionFeasibilityScreenArtifact;
  user_mission_run_catalog: UserMissionRunCatalogArtifact;
  runtime_scenario_generation: RuntimeScenarioGenerationArtifact;
  cost_procurement_architecture_feasibility: CostProcurementArchitectureFeasibilityArtifact;
  external_validation_review_pack: ExternalValidationReviewPackArtifact;
  public_narrative_hardening: PublicNarrativeHardeningArtifact;
  external_validation_execution_ledger: ExternalValidationExecutionLedgerArtifact;
  independent_physics_backend_comparison: IndependentPhysicsBackendComparisonArtifact;
  capsule_qualification_evidence_pack: CapsuleQualificationEvidencePackArtifact;
  evidence_upgrade_closure: EvidenceUpgradeClosureArtifact;
  external_reproduction_kit: ExternalReproductionKitArtifact;
  external_evidence_intake: ExternalEvidenceIntakeArtifact;
  external_validation_campaign: ExternalValidationCampaignArtifact;
  release_candidate_readiness: ReleaseCandidateReadinessArtifact;
  mission_probability_coupling: MissionProbabilityCouplingArtifact;
  uncertainty_interactions: UncertaintyInteractionsArtifact;
  evidence_upgrade_campaign: EvidenceUpgradeCampaignArtifact;
  mission_dag_v2_boundary: MissionDagV2BoundaryArtifact;
  roadmap_closure: RoadmapClosureArtifact;
}

export interface ParameterDrilldownDataset {
  manifest: ParameterDrilldownManifest;
  staticUsageGraph: Record<string, ParameterStaticUsageEntry>;
  evidenceIndex: Record<string, ParameterEvidenceEntry>;
  pSuccessDefensibility: PSuccessDefensibility;
  failureSurfaceBaseline: FailureSurfaceBaseline;
  objectiveContract: ObjectiveContract;
  objectiveScoreBaseline: ObjectiveScoreBaseline;
  optimizationSearchSpace: OptimizationSearchSpaceArtifact;
  optimizationFrontier: OptimizationFrontierArtifact;
  optimizationV2: OptimizationV2Artifact;
  capsuleSurvivabilityLab: CapsuleSurvivabilityLabArtifact;
  capsuleRiskBudget: CapsuleRiskBudgetArtifact;
  missionFeasibilityScreen: MissionFeasibilityScreenArtifact;
  userMissionRunCatalog: UserMissionRunCatalogArtifact;
  runtimeScenarioGeneration: RuntimeScenarioGenerationArtifact;
  costProcurementArchitectureFeasibility: CostProcurementArchitectureFeasibilityArtifact;
  externalValidationReviewPack: ExternalValidationReviewPackArtifact;
  publicNarrativeHardening: PublicNarrativeHardeningArtifact;
  externalValidationExecutionLedger: ExternalValidationExecutionLedgerArtifact;
  independentPhysicsBackendComparison: IndependentPhysicsBackendComparisonArtifact;
  capsuleQualificationEvidencePack: CapsuleQualificationEvidencePackArtifact;
  evidenceUpgradeClosure: EvidenceUpgradeClosureArtifact;
  externalReproductionKit: ExternalReproductionKitArtifact;
  externalEvidenceIntake: ExternalEvidenceIntakeArtifact;
  externalValidationCampaign: ExternalValidationCampaignArtifact;
  releaseCandidateReadiness: ReleaseCandidateReadinessArtifact;
  missionProbabilityCoupling: MissionProbabilityCouplingArtifact;
  uncertaintyInteractions: UncertaintyInteractionsArtifact;
  evidenceUpgradeCampaign: EvidenceUpgradeCampaignArtifact;
  missionDagV2Boundary: MissionDagV2BoundaryArtifact;
  roadmapClosure: RoadmapClosureArtifact;
  determinismStatus: DeterminismStatusSnapshot;
  parameters: ParameterManifestEntry[];
  parameterById: Record<string, ParameterManifestEntry>;
  errors: string[];
}
