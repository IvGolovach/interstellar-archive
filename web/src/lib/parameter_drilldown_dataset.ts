import { BROWSER_DATASET, PUBLIC_DATASET_PATHS } from "./artifact_public_contracts";
import type {
  BrowserDatasetPayload,
  FailureSurfaceBaseline,
  ObjectiveContract,
  ObjectiveScoreBaseline,
  OptimizationSearchSpaceArtifact,
  OptimizationV2Artifact,
  CapsuleSurvivabilityLabArtifact,
  ParameterDrilldownDataset,
  ParameterDrilldownManifest,
  ParameterEvidenceEntry,
  ParameterManifestEntry,
  ParameterStaticUsageEntry,
} from "./parameter_drilldown_dataset_contract";

export class ParameterDrilldownDatasetError extends Error {
  readonly validationErrors: string[];

  constructor(errors: string[]) {
    super(
      [
        "Invalid browser dataset contract.",
        ...errors.map((error) => `- ${error}`),
      ].join("\n"),
    );
    this.name = "ParameterDrilldownDatasetError";
    this.validationErrors = [...errors];
  }
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isInternalParameterId(parameterId: string): boolean {
  return parameterId.startsWith("code_literal.");
}

function jsonEqual(left: unknown, right: unknown): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

function collectParameterMap(args: {
  manifest: ParameterDrilldownManifest;
  staticUsageGraph: Record<string, ParameterStaticUsageEntry>;
  evidenceIndex: Record<string, ParameterEvidenceEntry>;
  errors: string[];
}): {
  parameters: ParameterManifestEntry[];
  parameterById: Record<string, ParameterManifestEntry>;
} {
  const { manifest, staticUsageGraph, evidenceIndex, errors } = args;
  const parameterById: Record<string, ParameterManifestEntry> = {};
  const parameterIds: string[] = [];

  for (const entry of manifest.parameters ?? []) {
    if (!isObject(entry)) {
      errors.push("manifest parameter entry must be an object");
      continue;
    }

    const parameterId = String(entry.parameter_id ?? "").trim();
    if (!parameterId) {
      errors.push("manifest parameter entry missing parameter_id");
      continue;
    }
    if (isInternalParameterId(parameterId)) {
      errors.push(`manifest contains internal parameter_id: ${parameterId}`);
      continue;
    }
    if (parameterById[parameterId]) {
      errors.push(`manifest duplicated parameter_id: ${parameterId}`);
      continue;
    }
    if (!staticUsageGraph[parameterId]) {
      errors.push(`static usage graph missing parameter: ${parameterId}`);
    }
    if (!evidenceIndex[parameterId]) {
      errors.push(`evidence index missing parameter: ${parameterId}`);
    }

    parameterById[parameterId] = entry as ParameterManifestEntry;
    parameterIds.push(parameterId);
  }

  const parameters = [...parameterIds]
    .sort()
    .map((parameterId) => parameterById[parameterId]);

  return { parameters, parameterById };
}

function validateFailureSurface(
  failureSurfaceBaseline: FailureSurfaceBaseline,
  manifestIdSet: Set<string>,
  errors: string[],
): void {
  if (failureSurfaceBaseline.schema_version !== "failure_surface.v1") {
    errors.push(`failure surface schema_version mismatch: ${failureSurfaceBaseline.schema_version}`);
  }
  if (!Array.isArray(failureSurfaceBaseline.timeline) || failureSurfaceBaseline.timeline.length !== 4) {
    errors.push("failure surface timeline must contain exactly 4 stage entries");
  } else {
    const stageOrder = failureSurfaceBaseline.timeline.map((entry) => entry.stage).join(",");
    if (stageOrder !== "S0,S1,S2,S3") {
      errors.push("failure surface timeline stages must be S0,S1,S2,S3 in order");
    }
  }
  if (
    !Array.isArray(failureSurfaceBaseline.dominant_drivers?.top3) ||
    failureSurfaceBaseline.dominant_drivers.top3.length !== 3
  ) {
    errors.push("failure surface dominant_drivers.top3 must contain exactly 3 entries");
  }
  if (
    !["SUCCESS", "FAIL", "UNHEALTHY", "INVALID"].includes(
      failureSurfaceBaseline.outcome?.outcome_class ?? "",
    )
  ) {
    errors.push(`failure surface outcome_class invalid: ${failureSurfaceBaseline.outcome?.outcome_class}`);
  }
  if (
    !isFiniteNumber(failureSurfaceBaseline.outcome?.p_success) ||
    failureSurfaceBaseline.outcome.p_success < 0 ||
    failureSurfaceBaseline.outcome.p_success > 1
  ) {
    errors.push("failure surface outcome.p_success must be a number in [0,1]");
  }

  for (const driver of failureSurfaceBaseline.dominant_drivers?.top3 ?? []) {
    if (!manifestIdSet.has(driver.parameter_id)) {
      errors.push(`failure surface dominant driver not found in manifest: ${driver.parameter_id}`);
    }
    const expectedRef = `${PUBLIC_DATASET_PATHS.parameterEvidenceIndex}#${driver.parameter_id}`;
    if (driver.evidence_ref !== expectedRef) {
      errors.push(
        `failure surface dominant driver evidence_ref mismatch for ${driver.parameter_id}: ${driver.evidence_ref}`,
      );
    }
  }
}

function validateObjectiveContract(
  objectiveContract: ObjectiveContract,
  objectiveScoreBaseline: ObjectiveScoreBaseline,
  errors: string[],
): void {
  if (objectiveContract.schema_version !== "objective_contract.v1") {
    errors.push(`objective contract schema_version mismatch: ${objectiveContract.schema_version}`);
  }
  if (objectiveScoreBaseline.schema_version !== "objective_score.v1") {
    errors.push(`objective score schema_version mismatch: ${objectiveScoreBaseline.schema_version}`);
  }
  if (objectiveScoreBaseline.contract_ref !== PUBLIC_DATASET_PATHS.objectiveContract) {
    errors.push(`objective score contract_ref mismatch: ${objectiveScoreBaseline.contract_ref}`);
  }
  if (!jsonEqual(objectiveScoreBaseline.contract_snapshot, objectiveContract)) {
    errors.push("objective contract must equal objective_score_baseline.contract_snapshot");
  }
  if (objectiveScoreBaseline.defensibility?.p_success_ref !== PUBLIC_DATASET_PATHS.pSuccessDefensibility) {
    errors.push(
      `objective score defensibility.p_success_ref mismatch: ${objectiveScoreBaseline.defensibility?.p_success_ref}`,
    );
  }
  if (
    !Array.isArray(objectiveScoreBaseline.scores?.realistic?.objective_vector) ||
    objectiveScoreBaseline.scores.realistic.objective_vector.length !== 2
  ) {
    errors.push("objective score realistic objective_vector must have length 2");
  }
  if (
    !Array.isArray(objectiveScoreBaseline.scores?.speculative?.objective_vector) ||
    objectiveScoreBaseline.scores.speculative.objective_vector.length !== 1
  ) {
    errors.push("objective score speculative objective_vector must have length 1");
  }
}

function validateOptimizationArtifacts(
  optimizationSearchSpace: OptimizationSearchSpaceArtifact,
  optimizationFrontier: ParameterDrilldownDataset["optimizationFrontier"],
  optimizationV2: OptimizationV2Artifact,
  errors: string[],
): void {
  const optimizationV2AxisIds = ["p_success", "risk_envelope", "qualification_gap", "cost_proxy"] as const;
  if (optimizationSearchSpace.schema_version !== "optimization_search_space.v1") {
    errors.push(
      `optimization search-space schema_version mismatch: ${optimizationSearchSpace.schema_version}`,
    );
  }
  if (optimizationSearchSpace.mode !== "realistic") {
    errors.push(`optimization search-space mode must be realistic: ${optimizationSearchSpace.mode}`);
  }
  if (optimizationSearchSpace.objective_contract_ref !== PUBLIC_DATASET_PATHS.objectiveContract) {
    errors.push(
      `optimization search-space objective_contract_ref mismatch: ${optimizationSearchSpace.objective_contract_ref}`,
    );
  }
  if (
    !Number.isInteger(optimizationSearchSpace.excluded_internal_parameter_count) ||
    optimizationSearchSpace.excluded_internal_parameter_count < 0
  ) {
    errors.push("optimization search-space excluded_internal_parameter_count must be int >= 0");
  }
  if (
    !Array.isArray(optimizationSearchSpace.internal_parameter_prefixes_excluded) ||
    !optimizationSearchSpace.internal_parameter_prefixes_excluded.includes("code_literal.")
  ) {
    errors.push("optimization search-space internal_parameter_prefixes_excluded must include code_literal.");
  }
  if (
    !Array.isArray(optimizationSearchSpace.parameters_considered) ||
    optimizationSearchSpace.parameters_considered.some((entry) => isInternalParameterId(entry.parameter_id))
  ) {
    errors.push("optimization search-space parameters_considered must exclude internal code_literal.* entries");
  }
  if (
    !Array.isArray(optimizationSearchSpace.excluded_parameters) ||
    optimizationSearchSpace.excluded_parameters.some((entry) => isInternalParameterId(entry.parameter_id))
  ) {
    errors.push("optimization search-space excluded_parameters must exclude internal code_literal.* entries");
  }

  if (optimizationFrontier.schema_version !== "optimization_frontier.v1") {
    errors.push(`optimization frontier schema_version mismatch: ${optimizationFrontier.schema_version}`);
  }
  if (optimizationFrontier.mode !== "realistic") {
    errors.push(`optimization frontier mode must be realistic: ${optimizationFrontier.mode}`);
  }
  if (optimizationFrontier.objective_contract_ref !== PUBLIC_DATASET_PATHS.objectiveContract) {
    errors.push(
      `optimization frontier objective_contract_ref mismatch: ${optimizationFrontier.objective_contract_ref}`,
    );
  }
  if (!Array.isArray(optimizationFrontier.points) || optimizationFrontier.points.length === 0) {
    errors.push("optimization frontier points must be non-empty");
  }
  if (optimizationFrontier.evaluation_count !== optimizationFrontier.points?.length) {
    errors.push(
      `optimization frontier evaluation_count mismatch: ${optimizationFrontier.evaluation_count} != ${optimizationFrontier.points?.length}`,
    );
  }
  if (
    !Array.isArray(optimizationFrontier.pareto_frontier_indices) ||
    optimizationFrontier.pareto_frontier_indices.some(
      (value) =>
        !Number.isInteger(value) ||
        value < 0 ||
        value >= (optimizationFrontier.points?.length ?? 0),
    )
  ) {
    errors.push("optimization frontier pareto_frontier_indices must contain valid point indices");
  }

  if (optimizationV2.schema_version !== "optimization_v2_frontier.v1") {
    errors.push(`optimization v2 schema_version mismatch: ${optimizationV2.schema_version}`);
  }
  if (optimizationV2.mode !== "realistic") {
    errors.push(`optimization v2 mode must be realistic: ${optimizationV2.mode}`);
  }
  if (optimizationV2.non_certification_notice !== true) {
    errors.push("optimization v2 non_certification_notice must be true");
  }
  const expectedAxisContract: Record<
    (typeof optimizationV2AxisIds)[number],
    { direction: "maximize" | "minimize"; status: "computed" | "screening_proxy"; sourceRef: string }
  > = {
    p_success: {
      direction: "maximize",
      status: "computed",
      sourceRef: PUBLIC_DATASET_PATHS.optimizationFrontier,
    },
    risk_envelope: {
      direction: "minimize",
      status: "computed",
      sourceRef: "mission/objectives/risk_envelope.v1.json",
    },
    qualification_gap: {
      direction: "minimize",
      status: "screening_proxy",
      sourceRef: "parameters/registry/parameter_claims.v1.json",
    },
    cost_proxy: {
      direction: "minimize",
      status: "screening_proxy",
      sourceRef: PUBLIC_DATASET_PATHS.optimizationSearchSpace,
    },
  };
  const axisContractIds = optimizationV2.axis_contract?.axes?.map((axis) => axis.id) ?? [];
  if (!jsonEqual(axisContractIds, optimizationV2AxisIds)) {
    errors.push("optimization v2 axis_contract axes must match rollup axes");
  }
  for (const axis of optimizationV2.axis_contract?.axes ?? []) {
    const expected = expectedAxisContract[axis.id];
    if (!expected) {
      errors.push(`optimization v2 axis_contract contains unknown axis: ${axis.id}`);
      continue;
    }
    if (axis.direction !== expected.direction) {
      errors.push(`optimization v2 axis ${axis.id} direction mismatch`);
    }
    if (axis.status !== expected.status) {
      errors.push(`optimization v2 axis ${axis.id} status mismatch`);
    }
    if (axis.source_ref !== expected.sourceRef) {
      errors.push(`optimization v2 axis ${axis.id} source_ref mismatch`);
    }
  }
  if (
    optimizationV2.rollup?.aggregation_policy !== "pareto_first_no_hidden_weighted_sum" ||
    !jsonEqual(optimizationV2.rollup?.axis_ids ?? [], optimizationV2AxisIds)
  ) {
    errors.push("optimization v2 rollup must expose the four Pareto axes");
  }
  for (const field of [
    "global_optimum_claimed",
    "hidden_weighted_sum_used",
    "calibrated_cost_model_available",
    "qualification_complete",
  ] as const) {
    if (optimizationV2.rollup?.[field] !== false) {
      errors.push(`optimization v2 rollup.${field} must be false`);
    }
  }
  if (
    optimizationV2.candidate_count !== optimizationV2.candidates?.length ||
    !Array.isArray(optimizationV2.candidates) ||
    optimizationV2.candidates.length === 0
  ) {
    errors.push("optimization v2 candidates must be non-empty and match candidate_count");
  }
  if (
    optimizationV2.frontier_candidate_count !== optimizationV2.pareto_frontier_candidate_ids?.length ||
    !Array.isArray(optimizationV2.pareto_frontier_candidate_ids) ||
    optimizationV2.pareto_frontier_candidate_ids.length === 0
  ) {
    errors.push("optimization v2 pareto ids must be non-empty and match frontier_candidate_count");
  }
  const sourceCandidateIds = new Set(
    (optimizationFrontier.points ?? []).map((point) => point.candidate_id),
  );
  const candidateIds = new Set<string>();
  const paretoMemberIds: string[] = [];
  for (const candidate of optimizationV2.candidates ?? []) {
    if (!candidate.candidate_id.startsWith("optv2-pt-")) {
      errors.push(`optimization v2 candidate id invalid: ${candidate.candidate_id}`);
    }
    if (candidateIds.has(candidate.candidate_id)) {
      errors.push(`optimization v2 duplicate candidate id: ${candidate.candidate_id}`);
    }
    candidateIds.add(candidate.candidate_id);
    if (!sourceCandidateIds.has(candidate.source_candidate_id)) {
      errors.push(`optimization v2 candidate ${candidate.candidate_id} source_candidate_id not found`);
    }
    for (const axis of optimizationV2AxisIds) {
      const value = candidate.scores?.[axis];
      if (!isFiniteNumber(value) || value < 0 || value > 1) {
        errors.push(`optimization v2 candidate ${candidate.candidate_id} ${axis} must be in [0,1]`);
      }
    }
    if (!Array.isArray(candidate.scores?.objective_vector) || candidate.scores.objective_vector.length !== 4) {
      errors.push(`optimization v2 candidate ${candidate.candidate_id} objective_vector must have length 4`);
    } else {
      for (const [axisIndex, axis] of optimizationV2AxisIds.entries()) {
        const vectorValue = candidate.scores.objective_vector[axisIndex];
        const scalarValue = candidate.scores[axis];
        if (!isFiniteNumber(vectorValue) || Math.abs(vectorValue - scalarValue) > 1e-12) {
          errors.push(`optimization v2 candidate ${candidate.candidate_id} objective_vector ${axis} mismatch`);
        }
      }
    }
    if (candidate.scores?.rank_key !== "pareto") {
      errors.push(`optimization v2 candidate ${candidate.candidate_id} rank_key must be pareto`);
    }
    if (!Array.isArray(candidate.dominant_drivers?.parameter_ids)) {
      errors.push(`optimization v2 candidate ${candidate.candidate_id} dominant_drivers.parameter_ids must be list`);
    } else {
      for (const parameterId of candidate.dominant_drivers.parameter_ids) {
        if (isInternalParameterId(parameterId)) {
          errors.push(`optimization v2 candidate ${candidate.candidate_id} leaks internal dominant driver: ${parameterId}`);
        }
      }
    }
    if (
      !Number.isInteger(candidate.dominant_drivers?.excluded_internal_parameter_count) ||
      candidate.dominant_drivers.excluded_internal_parameter_count < 0
    ) {
      errors.push(
        `optimization v2 candidate ${candidate.candidate_id} dominant_drivers.excluded_internal_parameter_count must be int >= 0`,
      );
    }
    if (candidate.pareto_frontier_member === true) {
      paretoMemberIds.push(candidate.candidate_id);
    } else if (candidate.pareto_frontier_member !== false) {
      errors.push(`optimization v2 candidate ${candidate.candidate_id} pareto_frontier_member must be boolean`);
    }
  }
  const paretoIds = optimizationV2.pareto_frontier_candidate_ids ?? [];
  if (paretoIds.some((candidateId) => !candidateIds.has(candidateId))) {
    errors.push("optimization v2 pareto ids must reference candidates");
  }
  if (!jsonEqual(paretoMemberIds, paretoIds)) {
    errors.push("optimization v2 pareto member flags must match pareto_frontier_candidate_ids");
  }
  if (!optimizationV2.blocked_claims.includes("global optimum proven")) {
    errors.push("optimization v2 must block global optimum claims");
  }
  if (!optimizationV2.blocked_claims.includes("procurement-grade cost estimate")) {
    errors.push("optimization v2 must block procurement-grade cost claims");
  }
  if (!optimizationV2.blocked_claims.includes("qualification complete")) {
    errors.push("optimization v2 must block qualification completion claims");
  }
  if (!optimizationV2.blocked_claims.includes("flight-ready design selected")) {
    errors.push("optimization v2 must block flight-ready design-selection claims");
  }
}

function validateCapsuleSurvivabilityLab(
  capsuleSurvivabilityLab: CapsuleSurvivabilityLabArtifact,
  errors: string[],
): void {
  if (capsuleSurvivabilityLab.schema_version !== "capsule_survivability_lab.v1") {
    errors.push(
      `capsule survivability schema_version mismatch: ${capsuleSurvivabilityLab.schema_version}`,
    );
  }
  if (capsuleSurvivabilityLab.non_certification_notice !== true) {
    errors.push("capsule survivability non_certification_notice must be true");
  }
  if (!Array.isArray(capsuleSurvivabilityLab.source_index) || capsuleSurvivabilityLab.source_index.length < 10) {
    errors.push("capsule survivability source_index must contain at least 10 entries");
  }
  if (!Array.isArray(capsuleSurvivabilityLab.source_data) || capsuleSurvivabilityLab.source_data.length < 16) {
    errors.push("capsule survivability source_data must contain at least 16 entries");
  }
  if (!Array.isArray(capsuleSurvivabilityLab.rows) || capsuleSurvivabilityLab.rows.length < 100) {
    errors.push("capsule survivability rows must contain at least 100 entries");
    return;
  }

  const targetIds = new Set(capsuleSurvivabilityLab.controls?.targets?.map((option) => option.id) ?? []);
  const timeIds = new Set(capsuleSurvivabilityLab.controls?.timeHorizons?.map((option) => option.id) ?? []);
  const velocityIds = new Set(capsuleSurvivabilityLab.controls?.velocityBands?.map((option) => option.id) ?? []);
  const capsuleIds = new Set(capsuleSurvivabilityLab.controls?.capsuleProfiles?.map((option) => option.id) ?? []);
  let hasDefaultBlackHoleRow = false;

  for (const row of capsuleSurvivabilityLab.rows) {
    if (!targetIds.has(row.targetId)) {
      errors.push(`capsule row ${row.rowId} references unknown targetId ${row.targetId}`);
    }
    if (!timeIds.has(row.timeId)) {
      errors.push(`capsule row ${row.rowId} references unknown timeId ${row.timeId}`);
    }
    if (!velocityIds.has(row.velocityId)) {
      errors.push(`capsule row ${row.rowId} references unknown velocityId ${row.velocityId}`);
    }
    if (!capsuleIds.has(row.capsuleId)) {
      errors.push(`capsule row ${row.rowId} references unknown capsuleId ${row.capsuleId}`);
    }
    for (const [key, value] of Object.entries({
      survivalProbability: row.output?.survivalProbability,
      dataIntegrityProbability: row.output?.dataIntegrityProbability,
      structureProbability: row.output?.structureProbability,
    })) {
      if (!isFiniteNumber(value) || value < 0 || value > 1) {
        errors.push(`capsule row ${row.rowId} output.${key} must be a probability`);
      }
    }
    if (!["nominal", "stressed", "critical"].includes(row.output?.outcomeBand ?? "")) {
      errors.push(`capsule row ${row.rowId} outcomeBand invalid: ${row.output?.outcomeBand}`);
    }
    if (
      row.targetId === "reference-black-hole" &&
      row.velocityId === "conditional-45" &&
      row.timeId === "ballistic-arrival" &&
      row.capsuleId === "baseline-stack"
    ) {
      hasDefaultBlackHoleRow = true;
      if (row.flightYears < 10_000_000 || row.flightYears > 11_000_000) {
        errors.push(`capsule default black-hole row flightYears not near 10 Myr: ${row.flightYears}`);
      }
    }
  }
  if (!hasDefaultBlackHoleRow) {
    errors.push("capsule survivability missing default black-hole arrival row");
  }
}

function validateCapsuleRiskBudget(capsuleRiskBudget: ParameterDrilldownDataset["capsuleRiskBudget"], errors: string[]): void {
  if (capsuleRiskBudget.schema_version !== "capsule_risk_budget.v1") {
    errors.push(`capsule risk budget schema_version mismatch: ${capsuleRiskBudget.schema_version}`);
  }
  if (capsuleRiskBudget.non_certification_notice !== true) {
    errors.push("capsule risk budget non_certification_notice must be true");
  }
  if (capsuleRiskBudget.source_artifact_ref !== PUBLIC_DATASET_PATHS.capsuleSurvivabilityLab) {
    errors.push(`capsule risk budget source_artifact_ref mismatch: ${capsuleRiskBudget.source_artifact_ref}`);
  }
  if (!Number.isInteger(capsuleRiskBudget.sample_count) || capsuleRiskBudget.sample_count < 1000) {
    errors.push(`capsule risk budget sample_count must be >= 1000: ${String(capsuleRiskBudget.sample_count)}`);
  }
  const attackModes = Array.isArray(capsuleRiskBudget.attack_modes)
    ? capsuleRiskBudget.attack_modes
    : capsuleRiskBudget.attack_modes?.modes;
  if (!Array.isArray(attackModes) || attackModes.length < 4) {
    errors.push("capsule risk budget attack_modes must contain at least 4 entries");
  }
  if (!Number.isInteger(capsuleRiskBudget.risk_budget_count) || capsuleRiskBudget.risk_budget_count < 100) {
    errors.push("capsule risk budget risk_budget_count must be at least 100");
  }
  if (!capsuleRiskBudget.source_policy || typeof capsuleRiskBudget.source_policy !== "object") {
    errors.push("capsule risk budget source_policy must be present");
  }
  if (!Array.isArray(capsuleRiskBudget.failure_modes) || capsuleRiskBudget.failure_modes.length < 8) {
    errors.push("capsule risk budget failure_modes must contain at least 8 entries");
  }
  if (!Array.isArray(capsuleRiskBudget.qualification_roadmap) || capsuleRiskBudget.qualification_roadmap.length < 5) {
    errors.push("capsule risk budget qualification_roadmap must contain at least 5 entries");
  }
}

function validateMissionFeasibilityScreen(
  missionFeasibilityScreen: ParameterDrilldownDataset["missionFeasibilityScreen"],
  errors: string[],
): void {
  if (missionFeasibilityScreen.schema_version !== "mission_feasibility_screen.v1") {
    errors.push(`mission feasibility schema_version mismatch: ${missionFeasibilityScreen.schema_version}`);
  }
  if (missionFeasibilityScreen.non_certification_notice !== true) {
    errors.push("mission feasibility non_certification_notice must be true");
  }
  if (missionFeasibilityScreen.target_count !== 3 || missionFeasibilityScreen.velocity_count !== 5) {
    errors.push("mission feasibility target/velocity counts must be 3 x 5");
  }
  if (
    missionFeasibilityScreen.scenario_count !== 15 ||
    !Array.isArray(missionFeasibilityScreen.scenario_rows) ||
    missionFeasibilityScreen.scenario_rows.length !== 15
  ) {
    errors.push("mission feasibility must expose exactly 15 scenario rows");
    return;
  }
  if (missionFeasibilityScreen.capsule_risk_budget_match_count !== 15) {
    errors.push("mission feasibility must link all rows to capsule risk budget rows");
  }
  const defaultRow = missionFeasibilityScreen.scenario_rows.find(
    (row) => row.id === missionFeasibilityScreen.default_scenario_id,
  );
  if (!defaultRow || defaultRow.target_id !== "reference-black-hole" || defaultRow.velocity_id !== "conditional-45") {
    errors.push("mission feasibility default row must be reference-black-hole conditional-45");
  } else if (defaultRow.flight_years < 10_000_000 || defaultRow.flight_years > 10_700_000) {
    errors.push(`mission feasibility default row flight_years must be near 10 Myr: ${defaultRow.flight_years}`);
  }
  for (const row of missionFeasibilityScreen.scenario_rows) {
    if (row.feasibility?.non_certification_notice !== true) {
      errors.push(`mission feasibility row ${row.id} must keep non_certification_notice`);
    }
    if (!row.capsule_risk_budget_link?.matched) {
      errors.push(`mission feasibility row ${row.id} must link to risk budget`);
    }
    if (!Array.isArray(row.external_evidence_gaps) || row.external_evidence_gaps.length === 0) {
      errors.push(`mission feasibility row ${row.id} must expose external evidence gaps`);
    }
    if (!Array.isArray(row.blocked_claims) || !row.blocked_claims.includes("flight ready")) {
      errors.push(`mission feasibility row ${row.id} must block flight ready claims`);
    }
  }
}

function validateUserMissionRunCatalog(
  userMissionRunCatalog: ParameterDrilldownDataset["userMissionRunCatalog"],
  errors: string[],
): void {
  if (userMissionRunCatalog.schema_version !== "user_mission_run_catalog.v1") {
    errors.push(`user mission run catalog schema_version mismatch: ${userMissionRunCatalog.schema_version}`);
  }
  if (userMissionRunCatalog.non_certification_notice !== true) {
    errors.push("user mission run catalog non_certification_notice must be true");
  }
  if (userMissionRunCatalog.target_count !== 3 || userMissionRunCatalog.velocity_count !== 5) {
    errors.push("user mission run catalog target/velocity counts must be 3 x 5");
  }
  if (
    userMissionRunCatalog.run_count !== 15 ||
    !Array.isArray(userMissionRunCatalog.run_rows) ||
    userMissionRunCatalog.run_rows.length !== 15
  ) {
    errors.push("user mission run catalog must expose exactly 15 run rows");
    return;
  }
  const defaultRow = userMissionRunCatalog.run_rows.find(
    (row) => row.run_id === userMissionRunCatalog.default_run_id,
  );
  if (
    !defaultRow ||
    defaultRow.selection.target_id !== "reference-black-hole" ||
    defaultRow.selection.velocity_id !== "conditional-45"
  ) {
    errors.push("user mission run catalog default row must be reference-black-hole conditional-45");
  }
  for (const row of userMissionRunCatalog.run_rows) {
    if (!row.run_id.startsWith("umr-")) {
      errors.push(`user mission run row ${row.run_id} must use umr-* id`);
    }
    if (row.selection_hash.length !== 64) {
      errors.push(`user mission run row ${row.run_id} selection_hash must be sha256`);
    }
    if (row.feasibility_status?.non_certification_notice !== true) {
      errors.push(`user mission run row ${row.run_id} must keep non_certification_notice`);
    }
    if (!Array.isArray(row.external_evidence_gaps) || row.external_evidence_gaps.length === 0) {
      errors.push(`user mission run row ${row.run_id} must expose external evidence gaps`);
    }
    if (!Array.isArray(row.blocked_claims) || !row.blocked_claims.includes("flight ready")) {
      errors.push(`user mission run row ${row.run_id} must block flight ready claims`);
    }
    if (
      row.runtime_pack_template?.script !== "scripts/run_user_mission_scenario.py" ||
      row.runtime_pack_template?.writes_tracked_files !== false
    ) {
      errors.push(`user mission run row ${row.run_id} runtime pack template mismatch`);
    }
  }
}

function validateRuntimeScenarioGeneration(
  runtimeScenarioGeneration: ParameterDrilldownDataset["runtimeScenarioGeneration"],
  errors: string[],
): void {
  if (runtimeScenarioGeneration.schema_version !== "runtime_scenario_generation.v1") {
    errors.push(`runtime scenario generation schema_version mismatch: ${runtimeScenarioGeneration.schema_version}`);
  }
  if (runtimeScenarioGeneration.non_certification_notice !== true) {
    errors.push("runtime scenario generation non_certification_notice must be true");
  }
  if (
    runtimeScenarioGeneration.selection_axes?.target_count !== 3 ||
    runtimeScenarioGeneration.selection_axes?.velocity_count !== 5
  ) {
    errors.push("runtime scenario generation target/velocity counts must be 3 x 5");
  }
  if (runtimeScenarioGeneration.selection_axes?.supported_modes?.join(",") !== "realistic,speculative,dual") {
    errors.push("runtime scenario generation supported modes mismatch");
  }
  if (
    runtimeScenarioGeneration.generation_row_count !== 15 ||
    !Array.isArray(runtimeScenarioGeneration.generation_rows) ||
    runtimeScenarioGeneration.generation_rows.length !== 15
  ) {
    errors.push("runtime scenario generation must expose exactly 15 recipe rows");
    return;
  }
  if (
    runtimeScenarioGeneration.run_pack_contract?.tracked_by_default !== false ||
    runtimeScenarioGeneration.run_pack_contract?.writes_tracked_files !== false
  ) {
    errors.push("runtime scenario generation run pack contract must not write tracked files");
  }
  if (!runtimeScenarioGeneration.run_pack_contract?.output_files?.includes("USER_RUN_SUMMARY.json")) {
    errors.push("runtime scenario generation run pack output files must include USER_RUN_SUMMARY.json");
  }
  const defaultRow = runtimeScenarioGeneration.generation_rows.find(
    (row) => row.run_id === runtimeScenarioGeneration.selection_axes.default_run_id,
  );
  if (
    !defaultRow ||
    defaultRow.target_id !== "reference-black-hole" ||
    defaultRow.velocity_id !== "conditional-45"
  ) {
    errors.push("runtime scenario generation default row must be reference-black-hole conditional-45");
  }
  for (const row of runtimeScenarioGeneration.generation_rows) {
    if (!row.run_id.startsWith("umr-")) {
      errors.push(`runtime scenario generation row ${row.run_id} must use umr-* id`);
    }
    if (row.selection_hash.length !== 64) {
      errors.push(`runtime scenario generation row ${row.run_id} selection_hash must be sha256`);
    }
    if (
      !row.command_preview.includes("scripts/run_user_mission_scenario.py") ||
      !row.command_preview.includes("--verify-deterministic")
    ) {
      errors.push(`runtime scenario generation row ${row.run_id} command_preview must call deterministic runner`);
    }
    if (
      row.ownership_boundary.remote_execution !== false ||
      row.ownership_boundary.persistent_reviewed_archive !== false ||
      row.ownership_boundary.tracked_by_default !== false
    ) {
      errors.push(`runtime scenario generation row ${row.run_id} must keep user-owned local boundary`);
    }
    if (row.run_pack_contract.writes_tracked_files !== false) {
      errors.push(`runtime scenario generation row ${row.run_id} must not write tracked files`);
    }
    if (!row.blocked_claims.includes("flight ready") || !row.blocked_claims.includes("persistent reviewed run archive")) {
      errors.push(`runtime scenario generation row ${row.run_id} must block runtime overclaims`);
    }
  }
  if (
    runtimeScenarioGeneration.rollup.rows_writing_tracked_files !== 0 ||
    runtimeScenarioGeneration.rollup.remote_execution_claimed ||
    runtimeScenarioGeneration.rollup.persistent_reviewed_archive_claimed
  ) {
    errors.push("runtime scenario generation rollup must keep tracked writes, remote execution, and persistent archive claims closed");
  }
  if (!runtimeScenarioGeneration.blocked_claims.includes("persistent reviewed run archive")) {
    errors.push("runtime scenario generation must block persistent archive claims");
  }
}

function validateCostProcurementArchitectureFeasibility(
  costArchitecture: ParameterDrilldownDataset["costProcurementArchitectureFeasibility"],
  errors: string[],
): void {
  if (costArchitecture.schema_version !== "cost_procurement_architecture_feasibility.v1") {
    errors.push(`cost architecture schema_version mismatch: ${costArchitecture.schema_version}`);
  }
  if (costArchitecture.non_certification_notice !== true) {
    errors.push("cost architecture non_certification_notice must be true");
  }
  if (costArchitecture.roadmap_item?.id !== "roadmap-13") {
    errors.push("cost architecture roadmap item must be roadmap-13");
  }
  if (costArchitecture.claim_boundaries?.procurement_status !== "external_required") {
    errors.push("cost architecture procurement boundary must stay external_required");
  }
  if (costArchitecture.cost_model?.calibrated_cost_model_available !== false) {
    errors.push("cost architecture calibrated cost model must be unavailable");
  }
  if (!costArchitecture.cost_model?.cost_boundary?.includes("procurement-grade")) {
    errors.push("cost architecture cost boundary must mention procurement-grade limit");
  }
  if (
    costArchitecture.architecture_row_count !== 15 ||
    !Array.isArray(costArchitecture.architecture_rows) ||
    costArchitecture.architecture_rows.length !== 15
  ) {
    errors.push("cost architecture must expose exactly 15 architecture rows");
    return;
  }
  let defaultSeen = false;
  for (const row of costArchitecture.architecture_rows) {
    if (!row.row_id.startsWith("cost-arch-")) {
      errors.push(`cost architecture row ${row.row_id} must use cost-arch-* id`);
    }
    if (row.procurement_status !== "external_required") {
      errors.push(`cost architecture row ${row.row_id} procurement_status must be external_required`);
    }
    if (!isFiniteNumber(row.cost_proxy_score) || row.cost_proxy_score < 0 || row.cost_proxy_score > 1) {
      errors.push(`cost architecture row ${row.row_id} cost_proxy_score must be in [0,1]`);
    }
    if (
      row.architecture_feasibility_status !== "review_required" &&
      row.architecture_feasibility_status !== "blocked_external_evidence"
    ) {
      errors.push(`cost architecture row ${row.row_id} architecture_feasibility_status mismatch`);
    }
    if (row.is_default_reference) {
      defaultSeen = row.target_id === "reference-black-hole" && row.velocity_id === "conditional-45";
    }
    if (!row.blocked_claims.includes("procurement-grade cost estimate")) {
      errors.push(`cost architecture row ${row.row_id} must block procurement-grade estimate`);
    }
  }
  if (!defaultSeen) {
    errors.push("cost architecture default row must be reference-black-hole conditional-45");
  }
  if (
    costArchitecture.optimization_cost_axis?.axis_id !== "cost_proxy" ||
    costArchitecture.optimization_cost_axis?.status !== "screening_proxy"
  ) {
    errors.push("cost architecture optimization axis must be cost_proxy screening_proxy");
  }
  if (
    costArchitecture.optimization_cost_axis?.calibrated_cost_model_available !== false ||
    costArchitecture.optimization_cost_axis?.qualification_complete !== false
  ) {
    errors.push("cost architecture optimization axis must keep cost model and qualification open");
  }
  if (
    costArchitecture.rollup?.procurement_grade_estimate_available !== false ||
    costArchitecture.rollup?.vendor_quote_count !== 0 ||
    costArchitecture.rollup?.launch_vehicle_selected !== false ||
    costArchitecture.rollup?.architecture_selected_for_flight !== false ||
    costArchitecture.rollup?.calibrated_cost_model_available !== false ||
    costArchitecture.rollup?.qualification_complete !== false ||
    costArchitecture.rollup?.all_rows_review_required !== true
  ) {
    errors.push("cost architecture rollup must keep procurement and flight architecture claims open");
  }
  if (!costArchitecture.blocked_claims.includes("procurement-grade cost estimate")) {
    errors.push("cost architecture must block procurement-grade cost estimate");
  }
  if (!costArchitecture.blocked_claims.includes("flight-ready architecture selected")) {
    errors.push("cost architecture must block flight-ready architecture selection");
  }
}

function validateExternalValidationReviewPack(
  reviewPack: ParameterDrilldownDataset["externalValidationReviewPack"],
  errors: string[],
): void {
  if (reviewPack.schema_version !== "external_validation_review_pack.v1") {
    errors.push(`external review pack schema_version mismatch: ${reviewPack.schema_version}`);
  }
  if (reviewPack.non_certification_notice !== true) {
    errors.push("external review pack non_certification_notice must be true");
  }
  if (reviewPack.review_pack_status !== "repo_native_review_pack_ready_external_review_not_completed") {
    errors.push("external review pack status must keep external review incomplete");
  }
  if (
    reviewPack.review_case_count !== 7 ||
    !Array.isArray(reviewPack.review_cases) ||
    reviewPack.review_cases.length !== 7
  ) {
    errors.push("external review pack must expose exactly 7 review cases");
    return;
  }
  for (const row of reviewPack.review_cases) {
    if (row.status !== "external_required") {
      errors.push(`external review case ${row.id} must be external_required`);
    }
    if (row.independent_result_available !== false) {
      errors.push(`external review case ${row.id} must keep independent_result_available=false`);
    }
    if (!Array.isArray(row.external_deliverable_ids) || row.external_deliverable_ids.length === 0) {
      errors.push(`external review case ${row.id} must request external deliverables`);
    }
    if (!row.blocked_claims.includes("external validation completed")) {
      errors.push(`external review case ${row.id} must block external validation completion`);
    }
  }
  if (
    !Array.isArray(reviewPack.required_external_deliverables) ||
    reviewPack.required_external_deliverables.length !== 6
  ) {
    errors.push("external review pack must expose exactly 6 required deliverables");
  }
  if (
    reviewPack.rollup.third_party_review_completed !== false ||
    reviewPack.rollup.independent_reproduction_completed !== false ||
    reviewPack.rollup.independent_benchmark_completed !== false ||
    reviewPack.rollup.high_fidelity_state_trace_complete !== false ||
    reviewPack.rollup.external_red_team_completed !== false ||
    reviewPack.rollup.external_validation_claimed !== false ||
    reviewPack.rollup.all_cases_require_external_review !== true
  ) {
    errors.push("external review pack rollup must keep every external validation claim open");
  }
  if (!reviewPack.blocked_claims.includes("third-party validated")) {
    errors.push("external review pack must block third-party validation claims");
  }
  if (!reviewPack.blocked_claims.includes("independent reproduction completed")) {
    errors.push("external review pack must block independent reproduction claims");
  }
}

function validatePublicNarrativeHardening(
  narrative: ParameterDrilldownDataset["publicNarrativeHardening"],
  errors: string[],
): void {
  if (narrative.schema_version !== "public_narrative_hardening.v1") {
    errors.push(`public narrative hardening schema_version mismatch: ${narrative.schema_version}`);
  }
  if (narrative.non_certification_notice !== true) {
    errors.push("public narrative hardening non_certification_notice must be true");
  }
  if (narrative.roadmap_item_ref !== "roadmap-15") {
    errors.push("public narrative hardening roadmap_item_ref must be roadmap-15");
  }
  if (narrative.claim_rule_count !== 10 || !Array.isArray(narrative.claim_rules) || narrative.claim_rules.length !== 10) {
    errors.push("public narrative hardening must expose exactly 10 claim rules");
  }
  if (
    narrative.public_surface_count < 8 ||
    !Array.isArray(narrative.public_surfaces) ||
    narrative.public_surfaces.length < 8
  ) {
    errors.push("public narrative hardening must expose at least 8 public surfaces");
  }
  const forbidden = Array.isArray(narrative.forbidden_public_claims) ? narrative.forbidden_public_claims : [];
  const required = Array.isArray(narrative.required_public_concepts) ? narrative.required_public_concepts : [];
  const boundary = (isObject(narrative.browser_boundary) ? narrative.browser_boundary : {}) as Record<string, unknown>;
  const rollup = (isObject(narrative.rollup) ? narrative.rollup : {}) as Record<string, unknown>;
  if (!forbidden.includes("certified")) {
    errors.push("public narrative hardening must block certified");
  }
  if (!forbidden.includes("external validation completed")) {
    errors.push("public narrative hardening must block external validation completion");
  }
  if (!forbidden.includes("procurement-grade cost estimate")) {
    errors.push("public narrative hardening must block procurement-grade cost estimate");
  }
  if (!required.includes("non-certifying")) {
    errors.push("public narrative hardening must require non-certifying");
  }
  if (!required.includes("deterministic artifact")) {
    errors.push("public narrative hardening must require deterministic artifact");
  }
  if (
    boundary.artifact_only_rendering !== true ||
    boundary.client_side_claim_recomputation_allowed !== false ||
    boundary.blocked_claim_suppression_allowed !== false ||
    boundary.external_gap_softening_allowed !== false
  ) {
    errors.push("public narrative hardening browser boundary must be artifact-only with no suppression or softening");
  }
  if (
    rollup.unsafe_public_overclaim_count !== 0 ||
    rollup.all_required_concepts_present !== true ||
    rollup.external_wording_audit_completed !== false ||
    rollup.audience_testing_completed !== false ||
    rollup.legal_review_completed !== false ||
    rollup.public_claim_approval_completed !== false ||
    rollup.external_validation_claimed !== false
  ) {
    errors.push("public narrative hardening rollup must keep public claim approval and external audit open");
  }
}

function validateExternalProofPhase(dataset: {
  externalLedger: ParameterDrilldownDataset["externalValidationExecutionLedger"];
  physicsComparison: ParameterDrilldownDataset["independentPhysicsBackendComparison"];
  capsuleQualification: ParameterDrilldownDataset["capsuleQualificationEvidencePack"];
  evidenceClosure: ParameterDrilldownDataset["evidenceUpgradeClosure"];
  reproductionKit: ParameterDrilldownDataset["externalReproductionKit"];
  evidenceIntake: ParameterDrilldownDataset["externalEvidenceIntake"];
  validationCampaign: ParameterDrilldownDataset["externalValidationCampaign"];
  releaseCandidate: ParameterDrilldownDataset["releaseCandidateReadiness"];
}, errors: string[]): void {
  const {
    externalLedger,
    physicsComparison,
    capsuleQualification,
    evidenceClosure,
    reproductionKit,
    evidenceIntake,
    validationCampaign,
    releaseCandidate,
  } = dataset;

  if (externalLedger.schema_version !== "external_validation_execution_ledger.v1") {
    errors.push(`external validation execution ledger schema_version mismatch: ${externalLedger.schema_version}`);
  }
  if (externalLedger.execution_record_count !== 0 || externalLedger.external_record_count !== 0) {
    errors.push("external validation execution ledger must keep external record counts at 0");
  }
  if (
    externalLedger.rollup.external_validation_completed !== false ||
    externalLedger.rollup.third_party_records_uploaded !== false ||
    externalLedger.rollup.independent_reproduction_completed !== false
  ) {
    errors.push("external validation execution ledger rollup must keep external review claims open");
  }
  for (const row of externalLedger.execution_cases ?? []) {
    if (row.execution_status !== "external_required") {
      errors.push(`external validation execution case ${row.review_case_id} must be external_required`);
    }
    if (row.external_record_status !== "no_external_record_uploaded") {
      errors.push(`external validation execution case ${row.review_case_id} must have no external record uploaded`);
    }
  }

  if (physicsComparison.schema_version !== "independent_physics_backend_comparison.v1") {
    errors.push(`physics comparison schema_version mismatch: ${physicsComparison.schema_version}`);
  }
  if (physicsComparison.comparison_status !== "repo_analytic_crosscheck_ready_external_backend_open") {
    errors.push("physics comparison must keep external backend open");
  }
  if (
    physicsComparison.rollup.independent_external_backend_complete !== false ||
    physicsComparison.rollup.cross_backend_comparison_completed !== false ||
    physicsComparison.rollup.high_fidelity_state_trace_complete !== false ||
    physicsComparison.rollup.independent_physics_backend_validated !== false
  ) {
    errors.push("physics comparison rollup must keep independent backend validation open");
  }
  if (
    physicsComparison.analytic_check_count < 4 ||
    !Array.isArray(physicsComparison.analytic_checks) ||
    physicsComparison.analytic_checks.some((check) => check.status !== "match")
  ) {
    errors.push("physics comparison must expose matching repo analytic checks");
  }

  if (capsuleQualification.schema_version !== "capsule_qualification_evidence_pack.v1") {
    errors.push(`capsule qualification schema_version mismatch: ${capsuleQualification.schema_version}`);
  }
  if (
    capsuleQualification.mass_closure.configured_capsule_mass_kg !== 206 ||
    capsuleQualification.mass_closure.within_declared_margin !== true
  ) {
    errors.push("capsule qualification mass closure must keep the 206 kg configured stack closed");
  }
  if (
    capsuleQualification.lab_record_count !== 0 ||
    capsuleQualification.rollup.qualification_complete !== false ||
    capsuleQualification.rollup.flight_ready_claimed !== false ||
    capsuleQualification.rollup.certified_hardware_survivability !== false
  ) {
    errors.push("capsule qualification must keep lab records, qualification, and flight readiness open");
  }
  if (!capsuleQualification.blocked_claims.includes("qualified")) {
    errors.push("capsule qualification must block qualified claims");
  }

  if (evidenceClosure.schema_version !== "evidence_upgrade_closure.v1") {
    errors.push(`evidence closure schema_version mismatch: ${evidenceClosure.schema_version}`);
  }
  if (
    evidenceClosure.closure_cycle_count !== 15 ||
    evidenceClosure.rollup.trust_grade_promotion_count !== 0 ||
    evidenceClosure.rollup.external_source_upgrade_count !== 0 ||
    evidenceClosure.rollup.source_correctness_claimed !== false ||
    evidenceClosure.rollup.trust_grades_upgraded_automatically !== false
  ) {
    errors.push("evidence closure must keep the first closure cycle non-promotional");
  }

  if (reproductionKit.schema_version !== "external_reproduction_kit.v1") {
    errors.push(`external reproduction kit schema_version mismatch: ${reproductionKit.schema_version}`);
  }
  if (
    reproductionKit.kit_status !== "repo_native_reproduction_kit_ready_external_execution_open" ||
    reproductionKit.review_case_count !== 7 ||
    reproductionKit.rollup.export_cli_available !== true ||
    reproductionKit.rollup.external_execution_completed !== false ||
    reproductionKit.rollup.first_real_external_record_present !== false ||
    reproductionKit.rollup.fake_external_records_accepted !== false
  ) {
    errors.push("external reproduction kit must be export-ready while keeping execution and records open");
  }

  if (evidenceIntake.schema_version !== "external_evidence_intake.v1") {
    errors.push(`external evidence intake schema_version mismatch: ${evidenceIntake.schema_version}`);
  }
  if (
    evidenceIntake.intake_status !== "external_record_intake_ready_awaiting_external_submission" ||
    evidenceIntake.record_count !== 0 ||
    evidenceIntake.accepted_record_count !== 0 ||
    evidenceIntake.rejected_record_count !== 0 ||
    evidenceIntake.rollup.first_real_external_record_present !== false ||
    evidenceIntake.rollup.external_validation_completed !== false ||
    evidenceIntake.rollup.independent_backend_validated !== false ||
    evidenceIntake.rollup.certification_go !== false
  ) {
    errors.push("external evidence intake must keep first real external record and claim promotion open");
  }
  if (
    evidenceIntake.validation_policy.reject_repository_maintainer_as_external !== true ||
    evidenceIntake.validation_policy.reject_self_signed_repo_native_records !== true
  ) {
    errors.push("external evidence intake must reject maintainer/self-signed external records");
  }

  if (validationCampaign.schema_version !== "external_validation_campaign.v1") {
    errors.push(`external validation campaign schema_version mismatch: ${validationCampaign.schema_version}`);
  }
  if (
    validationCampaign.campaign_status !== "repo_campaign_ready_external_execution_required" ||
    validationCampaign.workstream_count !== 6 ||
    validationCampaign.campaign_policy.records_do_not_directly_unlock_claims !== true ||
    validationCampaign.campaign_policy.proof_promotion_requires_followup_review !== true
  ) {
    errors.push("external validation campaign must expose six workstreams without direct claim promotion");
  }
  if (
    validationCampaign.rollup.accepted_record_count !== 0 ||
    validationCampaign.rollup.first_real_external_record_present !== false ||
    validationCampaign.rollup.external_validation_completed !== false ||
    validationCampaign.rollup.independent_backend_validated !== false ||
    validationCampaign.rollup.line_of_sight_model_complete !== false ||
    validationCampaign.rollup.qualification_complete !== false ||
    validationCampaign.rollup.certification_go !== false
  ) {
    errors.push("external validation campaign rollup must keep external proof and certification open");
  }
  if (
    validationCampaign.proof_promotion_review.automatic_claim_promotion_allowed !== false ||
    !Array.isArray(validationCampaign.proof_promotion_review.promoted_claims) ||
    validationCampaign.proof_promotion_review.promoted_claims.length !== 0
  ) {
    errors.push("external validation campaign proof promotion must require follow-up review");
  }
  if (
    validationCampaign.public_evidence_dossier.marketing_claim_surface !== false ||
    validationCampaign.public_evidence_dossier.certification_language_allowed !== false
  ) {
    errors.push("external validation campaign public dossier must block marketing and certification language");
  }

  if (releaseCandidate.schema_version !== "release_candidate_readiness.v1") {
    errors.push(`release candidate schema_version mismatch: ${releaseCandidate.schema_version}`);
  }
  if (releaseCandidate.release_candidate_status !== "repo_publication_candidate_external_evidence_open") {
    errors.push("release candidate must keep external evidence open");
  }
  if (releaseCandidate.rollup.repo_publication_candidate_ready !== true) {
    errors.push("release candidate must be repo-publication ready");
  }
  for (const field of [
    "certification_go",
    "flight_readiness_go",
    "external_validation_completed",
    "qualification_complete",
    "independent_backend_validated",
    "trust_grade_promotions_completed",
  ] as const) {
    if (releaseCandidate.rollup[field] !== false) {
      errors.push(`release candidate rollup.${field} must be false`);
    }
  }
}

function validateMissionProbabilityCoupling(
  missionProbabilityCoupling: ParameterDrilldownDataset["missionProbabilityCoupling"],
  errors: string[],
): void {
  if (missionProbabilityCoupling.schema_version !== "mission_probability_coupling.v1") {
    errors.push(`mission probability coupling schema_version mismatch: ${missionProbabilityCoupling.schema_version}`);
  }
  if (missionProbabilityCoupling.non_certification_notice !== true) {
    errors.push("mission probability coupling non_certification_notice must be true");
  }
  if (missionProbabilityCoupling.coupling_count !== 15) {
    errors.push(`mission probability coupling coupling_count must be 15: ${missionProbabilityCoupling.coupling_count}`);
  }
  if (missionProbabilityCoupling.rollup?.rows_with_full_mission_probability_closed !== 0) {
    errors.push("mission probability coupling must keep full mission probability open");
  }
  if (
    !Array.isArray(missionProbabilityCoupling.coupling_rows) ||
    missionProbabilityCoupling.coupling_rows.length !== 15
  ) {
    errors.push("mission probability coupling must expose exactly 15 rows");
    return;
  }
  const defaultRow = missionProbabilityCoupling.coupling_rows.find(
    (row) => row.coupling_id === missionProbabilityCoupling.default_coupling_id,
  );
  if (!defaultRow || defaultRow.run_id !== missionProbabilityCoupling.default_run_id) {
    errors.push("mission probability coupling default row must reference default run");
  }
  for (const row of missionProbabilityCoupling.coupling_rows) {
    if (!row.coupling_id.startsWith("mpc-")) {
      errors.push(`mission probability coupling row ${row.coupling_id} must use mpc-* id`);
    }
    if (row.open_external_factor_count !== 3 || row.closed_factor_count !== 2) {
      errors.push(`mission probability coupling row ${row.coupling_id} must keep 3 open and 2 closed factors`);
    }
    if (
      row.full_mission_probability?.status !== "not_closed_external_factors_open" ||
      row.full_mission_probability.p50 !== null
    ) {
      errors.push(`mission probability coupling row ${row.coupling_id} must keep full mission probability open`);
    }
    const closed = row.closed_capsule_data_probability;
    if (
      !isFiniteNumber(closed?.p50) ||
      closed.p50 < 0 ||
      closed.p50 > 1 ||
      closed.status !== "review_proxy_only"
    ) {
      errors.push(`mission probability coupling row ${row.coupling_id} closed proxy p50 must be a review probability`);
    }
    const factorsById = Object.fromEntries(row.factor_budget.map((factor) => [factor.factor_id, factor]));
    const survival = factorsById.capsule_survival?.value_p50;
    const data = factorsById.data_integrity?.value_p50;
    if (isFiniteNumber(survival) && isFiniteNumber(data) && isFiniteNumber(closed?.p50)) {
      const expected = Number((survival * data).toFixed(12));
      if (Math.abs(expected - closed.p50) > 1e-12) {
        errors.push(`mission probability coupling row ${row.coupling_id} closed proxy must equal survival x data`);
      }
    }
    if (!Array.isArray(row.external_evidence_gaps) || row.external_evidence_gaps.length === 0) {
      errors.push(`mission probability coupling row ${row.coupling_id} must expose external evidence gaps`);
    }
    if (!Array.isArray(row.blocked_claims) || !row.blocked_claims.includes("full mission probability closed")) {
      errors.push(`mission probability coupling row ${row.coupling_id} must block full probability closure claims`);
    }
    if (row.dag_coupling?.writes_tracked_files !== false) {
      errors.push(`mission probability coupling row ${row.coupling_id} dag coupling must not write tracked files`);
    }
  }
}

function validateUncertaintyInteractions(
  uncertaintyInteractions: ParameterDrilldownDataset["uncertaintyInteractions"],
  errors: string[],
): void {
  if (uncertaintyInteractions.schema_version !== "uncertainty_interactions.v1") {
    errors.push(`uncertainty interactions schema_version mismatch: ${uncertaintyInteractions.schema_version}`);
  }
  if (uncertaintyInteractions.non_certification_notice !== true) {
    errors.push("uncertainty interactions non_certification_notice must be true");
  }
  if (uncertaintyInteractions.mode !== "realistic") {
    errors.push(`uncertainty interactions mode must be realistic: ${uncertaintyInteractions.mode}`);
  }
  if (uncertaintyInteractions.uncertainty_entry_count !== 4) {
    errors.push(`uncertainty interactions must expose 4 dimensions: ${uncertaintyInteractions.uncertainty_entry_count}`);
  }
  if (uncertaintyInteractions.interaction_pair_count !== 6) {
    errors.push(`uncertainty interactions must expose 6 pair rows: ${uncertaintyInteractions.interaction_pair_count}`);
  }
  if (!Array.isArray(uncertaintyInteractions.main_effects) || uncertaintyInteractions.main_effects.length !== 4) {
    errors.push("uncertainty interactions main_effects must contain 4 rows");
  }
  if (
    !Array.isArray(uncertaintyInteractions.pair_interactions) ||
    uncertaintyInteractions.pair_interactions.length !== 6
  ) {
    errors.push("uncertainty interactions pair_interactions must contain 6 rows");
    return;
  }
  if (uncertaintyInteractions.rollup?.validated_correlation_count !== 0) {
    errors.push("uncertainty interactions must not claim validated correlations");
  }
  if (uncertaintyInteractions.rollup?.full_uncertainty_interaction_closure !== false) {
    errors.push("uncertainty interactions full closure must remain false");
  }
  if (uncertaintyInteractions.rollup?.pairs_requiring_external_correlation_evidence !== 6) {
    errors.push("uncertainty interactions all pairs must require external correlation evidence");
  }
  for (const effect of uncertaintyInteractions.main_effects ?? []) {
    if (!effect.entry_id.startsWith("ui-param-")) {
      errors.push(`uncertainty main effect ${effect.entry_id} must use ui-param-* id`);
    }
    if (!isFiniteNumber(effect.max_abs_effect) || effect.max_abs_effect < 0) {
      errors.push(`uncertainty main effect ${effect.entry_id} max_abs_effect must be >= 0`);
    }
    if (
      !isFiniteNumber(effect.p_success_low) ||
      !isFiniteNumber(effect.p_success_nominal) ||
      !isFiniteNumber(effect.p_success_high)
    ) {
      errors.push(`uncertainty main effect ${effect.entry_id} p_success values must be finite`);
    }
  }
  for (const row of uncertaintyInteractions.pair_interactions) {
    if (!row.pair_id.startsWith("ui-pair-")) {
      errors.push(`uncertainty pair ${row.pair_id} must use ui-pair-* id`);
    }
    if (row.status !== "external_correlation_evidence_required") {
      errors.push(`uncertainty pair ${row.pair_id} must keep status open`);
    }
    if (row.correlation?.rho !== null || row.correlation?.status !== "external_correlation_evidence_required") {
      errors.push(`uncertainty pair ${row.pair_id} must keep correlation rho null and open`);
    }
    const residual = row.interaction_residual;
    if (
      !isFiniteNumber(residual?.max_abs) ||
      residual.max_abs < 0 ||
      !["negligible", "weak", "material"].includes(residual.classification)
    ) {
      errors.push(`uncertainty pair ${row.pair_id} residual classification invalid`);
    }
  }
  if (
    !Array.isArray(uncertaintyInteractions.blocked_claims) ||
    !uncertaintyInteractions.blocked_claims.includes("validated uncertainty independence")
  ) {
    errors.push("uncertainty interactions must block validated independence claims");
  }
  if (!Array.isArray(uncertaintyInteractions.external_evidence_gaps) || uncertaintyInteractions.external_evidence_gaps.length === 0) {
    errors.push("uncertainty interactions external_evidence_gaps must be non-empty");
  }
}

function validateEvidenceUpgradeCampaign(
  evidenceUpgradeCampaign: ParameterDrilldownDataset["evidenceUpgradeCampaign"],
  errors: string[],
): void {
  if (evidenceUpgradeCampaign.schema_version !== "evidence_upgrade_campaign.v1") {
    errors.push(`evidence campaign schema_version mismatch: ${evidenceUpgradeCampaign.schema_version}`);
  }
  if (evidenceUpgradeCampaign.non_certification_notice !== true) {
    errors.push("evidence campaign non_certification_notice must be true");
  }
  if (evidenceUpgradeCampaign.claim_count !== 66) {
    errors.push(`evidence campaign claim_count must be 66: ${String(evidenceUpgradeCampaign.claim_count)}`);
  }
  if (evidenceUpgradeCampaign.public_campaign_count !== 31) {
    errors.push(
      `evidence campaign public_campaign_count must be 31: ${String(evidenceUpgradeCampaign.public_campaign_count)}`,
    );
  }
  if (evidenceUpgradeCampaign.internal_audit_count !== 35) {
    errors.push(
      `evidence campaign internal_audit_count must be 35: ${String(evidenceUpgradeCampaign.internal_audit_count)}`,
    );
  }
  if (!jsonEqual(evidenceUpgradeCampaign.trust_distribution, { B: 8, C: 56, D: 2 })) {
    errors.push("evidence campaign trust_distribution mismatch");
  }
  if (!jsonEqual(evidenceUpgradeCampaign.public_trust_distribution, { B: 8, C: 21, D: 2 })) {
    errors.push("evidence campaign public_trust_distribution mismatch");
  }
  if (!Array.isArray(evidenceUpgradeCampaign.public_top_priorities) || evidenceUpgradeCampaign.public_top_priorities.length === 0) {
    errors.push("evidence campaign public_top_priorities must be non-empty");
    return;
  }
  let previousScore: number | null = null;
  for (const row of evidenceUpgradeCampaign.public_top_priorities) {
    if (row.visibility !== "public") {
      errors.push(`evidence campaign row ${row.campaign_id} visibility must be public`);
    }
    if (isInternalParameterId(row.parameter_id)) {
      errors.push(`evidence campaign row leaks internal parameter_id: ${row.parameter_id}`);
    }
    if (!isFiniteNumber(row.priority_score) || row.priority_score < 0) {
      errors.push(`evidence campaign row ${row.campaign_id} priority_score must be >= 0`);
    }
    if (previousScore !== null && row.priority_score > previousScore + 1e-12) {
      errors.push("evidence campaign public_top_priorities must be sorted by priority");
    }
    previousScore = row.priority_score;
    if (!Array.isArray(row.recommended_actions) || row.recommended_actions.length === 0) {
      errors.push(`evidence campaign row ${row.campaign_id} must expose recommended actions`);
    }
    if (!Array.isArray(row.blocked_claims) || !row.blocked_claims.includes("automatic trust promotion")) {
      errors.push(`evidence campaign row ${row.campaign_id} must block automatic trust promotion`);
    }
  }
  if (
    !Array.isArray(evidenceUpgradeCampaign.blocked_claims) ||
    !evidenceUpgradeCampaign.blocked_claims.includes("trust grades upgraded automatically")
  ) {
    errors.push("evidence campaign blocked_claims must block automatic trust upgrades");
  }
  if (
    !Array.isArray(evidenceUpgradeCampaign.blocked_claims) ||
    !evidenceUpgradeCampaign.blocked_claims.includes("source correctness proven")
  ) {
    errors.push("evidence campaign blocked_claims must block source correctness proof");
  }
  if (!Array.isArray(evidenceUpgradeCampaign.external_evidence_gaps) || evidenceUpgradeCampaign.external_evidence_gaps.length === 0) {
    errors.push("evidence campaign external_evidence_gaps must be non-empty");
  }
}

function validateMissionDagV2Boundary(
  missionDagV2Boundary: ParameterDrilldownDataset["missionDagV2Boundary"],
  errors: string[],
): void {
  if (missionDagV2Boundary.schema_version !== "mission_dag_v2_boundary.v1") {
    errors.push(`mission DAG v2 boundary schema_version mismatch: ${missionDagV2Boundary.schema_version}`);
  }
  if (missionDagV2Boundary.non_certification_notice !== true) {
    errors.push("mission DAG v2 boundary non_certification_notice must be true");
  }
  if (missionDagV2Boundary.module_count !== 6 || missionDagV2Boundary.module_boundaries.length !== 6) {
    errors.push("mission DAG v2 boundary must expose 6 module rows");
  }
  if (
    missionDagV2Boundary.rollup.state_trace_contract_complete !== true ||
    missionDagV2Boundary.rollup.module_io_schema_contract_available !== true ||
    missionDagV2Boundary.rollup.hashchain_contract_available !== true
  ) {
    errors.push("mission DAG v2 boundary must expose state trace, schema, and hashchain contracts");
  }
  for (const field of [
    "independent_backend_complete",
    "high_fidelity_state_traces_available",
    "cross_backend_comparison_available",
    "flight_ready_module_claimed",
    "external_reproduction_completed",
  ] as const) {
    if (missionDagV2Boundary.rollup[field] !== false) {
      errors.push(`mission DAG v2 boundary rollup.${field} must be false`);
    }
  }
  const moduleIds = new Set<string>();
  for (const row of missionDagV2Boundary.module_boundaries) {
    if (moduleIds.has(row.module_id)) {
      errors.push(`mission DAG v2 boundary duplicate module_id: ${row.module_id}`);
    }
    moduleIds.add(row.module_id);
    if (!Array.isArray(row.scenario_node_ids) || row.scenario_node_ids.length === 0) {
      errors.push(`mission DAG v2 boundary ${row.module_id} must map to scenario nodes`);
    }
    if (!Array.isArray(row.failure_taxonomy_ids) || row.failure_taxonomy_ids.length === 0) {
      errors.push(`mission DAG v2 boundary ${row.module_id} must map to failure taxonomy`);
    }
    if (!row.v2_boundary_requirements.includes("state trace hash")) {
      errors.push(`mission DAG v2 boundary ${row.module_id} must require state trace hash`);
    }
    if (row.current_v1_support.independent_backend_id_declared !== false) {
      errors.push(`mission DAG v2 boundary ${row.module_id} must keep independent backend open`);
    }
    if (!Array.isArray(row.open_external_evidence_gaps) || row.open_external_evidence_gaps.length === 0) {
      errors.push(`mission DAG v2 boundary ${row.module_id} must expose evidence gaps`);
    }
  }
  if (!missionDagV2Boundary.blocked_claims.includes("independent physics backend validated")) {
    errors.push("mission DAG v2 boundary must block independent backend validation");
  }
  if (!missionDagV2Boundary.blocked_claims.includes("flight-ready module approved")) {
    errors.push("mission DAG v2 boundary must block flight-ready module approval");
  }
}

function validateRoadmapClosure(roadmapClosure: ParameterDrilldownDataset["roadmapClosure"], errors: string[]): void {
  if (roadmapClosure.schema_version !== "roadmap_closure.v1") {
    errors.push(`roadmap closure schema_version mismatch: ${roadmapClosure.schema_version}`);
  }
  if (roadmapClosure.non_certification_notice !== true) {
    errors.push("roadmap closure non_certification_notice must be true");
  }
  if (roadmapClosure.roadmap_item_count !== 15) {
    errors.push(`roadmap closure roadmap_item_count must be 15: ${String(roadmapClosure.roadmap_item_count)}`);
  }
  if (
    roadmapClosure.closure_metrics?.repo_native_closure_count !== 15 ||
    roadmapClosure.closure_metrics?.non_certification_notice_count !== 15
  ) {
    errors.push("roadmap closure metrics must count 15 repo-native closure rows and notices");
  }
  if (roadmapClosure.runtime_runs?.schema_version !== "runtime_scenario_generation.v1") {
    errors.push("roadmap closure runtime_runs must reference runtime_scenario_generation.v1");
  }
  if (roadmapClosure.runtime_runs?.run_store_tracked_by_default !== false) {
    errors.push("roadmap closure runtime_runs must keep run store untracked by default");
  }
  if (!Array.isArray(roadmapClosure.roadmap_items) || roadmapClosure.roadmap_items.length !== 15) {
    errors.push("roadmap closure roadmap_items must contain exactly 15 entries");
    return;
  }
  for (const item of roadmapClosure.roadmap_items) {
    if (item.status !== "repo_native_closure_implemented_external_evidence_open") {
      errors.push(`roadmap closure item ${item.id} has invalid status: ${item.status}`);
    }
    if (item.non_certification_notice !== true) {
      errors.push(`roadmap closure item ${item.id} must keep non_certification_notice=true`);
    }
    if (!Array.isArray(item.external_evidence_gaps) || item.external_evidence_gaps.length === 0) {
      errors.push(`roadmap closure item ${item.id} must expose external evidence gaps`);
    }
    if (!Array.isArray(item.false_claims_blocked) || !item.false_claims_blocked.includes("certified")) {
      errors.push(`roadmap closure item ${item.id} must block certification claims`);
    }
  }
  const roadmap15 = roadmapClosure.roadmap_items.find((item) => item.id === "roadmap-15");
  if (!roadmap15) {
    errors.push("roadmap closure must include roadmap-15");
  } else {
    if (roadmap15.implementation_mode !== "tracked_public_narrative_hardening") {
      errors.push("roadmap-15 must be tracked_public_narrative_hardening");
    }
    if (!roadmap15.artifacts.includes(PUBLIC_DATASET_PATHS.publicNarrativeHardening)) {
      errors.push("roadmap-15 must reference public narrative hardening artifact");
    }
    if (!roadmap15.validators.includes("scripts/ci/public_narrative_hardening_validate.py")) {
      errors.push("roadmap-15 must reference public narrative hardening validator");
    }
    if (!roadmap15.false_claims_blocked.includes("certified")) {
      errors.push("roadmap-15 must block certified");
    }
  }

  const narrative = roadmapClosure.public_narrative;
  if (narrative?.status !== "implemented_as_tracked_public_narrative_hardening") {
    errors.push("roadmap closure public_narrative must be artifact-backed");
  }
  if (narrative?.artifact_ref !== PUBLIC_DATASET_PATHS.publicNarrativeHardening) {
    errors.push("roadmap closure public_narrative must reference public narrative hardening artifact");
  }
  if (narrative?.unsafe_public_overclaim_count !== 0) {
    errors.push("roadmap closure public_narrative unsafe_public_overclaim_count must be 0");
  }
  if (
    narrative?.external_wording_audit_completed !== false ||
    narrative?.audience_testing_completed !== false ||
    narrative?.legal_review_completed !== false ||
    narrative?.public_claim_approval_completed !== false ||
    narrative?.all_required_concepts_present !== true
  ) {
    errors.push("roadmap closure public_narrative must keep public audit and approval work open");
  }
  if (!narrative?.forbidden_claims?.includes("certified")) {
    errors.push("roadmap closure public_narrative must block certified");
  }
  if (!narrative?.forbidden_claims?.includes("external validation completed")) {
    errors.push("roadmap closure public_narrative must block external validation completion");
  }
  if (!narrative?.required_claims?.includes("non-certifying")) {
    errors.push("roadmap closure public_narrative must require non-certifying");
  }
}

export function loadParameterDrilldownDataset(
  options: { strict?: boolean } = {},
): ParameterDrilldownDataset {
  const browserDataset = clone(BROWSER_DATASET) as BrowserDatasetPayload;
  const errors: string[] = [];

  if (browserDataset.schema_version !== "browser_dataset.v1") {
    errors.push(`browser dataset schema_version mismatch: ${browserDataset.schema_version}`);
  }
  if (browserDataset.public_scope !== "tracked_generated_only") {
    errors.push(`browser dataset public_scope mismatch: ${browserDataset.public_scope}`);
  }

  if (!isObject(browserDataset.source_paths)) {
    errors.push("browser dataset source_paths must be an object");
  } else {
    for (const [key, expectedPath] of Object.entries(PUBLIC_DATASET_PATHS)) {
      const actualPath = browserDataset.source_paths[key as keyof typeof PUBLIC_DATASET_PATHS];
      if (actualPath !== expectedPath) {
        errors.push(`browser dataset source_paths.${key} mismatch: ${String(actualPath)}`);
      }
    }
  }

  if (!Array.isArray(browserDataset.source_artifacts) || browserDataset.source_artifacts.length === 0) {
    errors.push("browser dataset source_artifacts must be a non-empty array");
  }

  const manifest = clone(browserDataset.manifest ?? { parameters: [] }) as ParameterDrilldownManifest;
  const staticUsageGraph = clone(browserDataset.static_usage_graph ?? {}) as Record<
    string,
    ParameterStaticUsageEntry
  >;
  const evidenceIndex = clone(browserDataset.evidence_index ?? {}) as Record<string, ParameterEvidenceEntry>;
  const pSuccessDefensibility = clone(browserDataset.p_success_defensibility ?? {}) as ParameterDrilldownDataset["pSuccessDefensibility"];
  const determinismStatus = clone(browserDataset.determinism_status ?? {}) as ParameterDrilldownDataset["determinismStatus"];
  const failureSurfaceBaseline = clone(
    browserDataset.failure_surface_baseline ?? {},
  ) as ParameterDrilldownDataset["failureSurfaceBaseline"];
  const objectiveContract = clone(browserDataset.objective_contract ?? {}) as ParameterDrilldownDataset["objectiveContract"];
  const objectiveScoreBaseline = clone(
    browserDataset.objective_score_baseline ?? {},
  ) as ParameterDrilldownDataset["objectiveScoreBaseline"];
  const optimizationSearchSpace = clone(
    browserDataset.optimization_search_space ?? {},
  ) as ParameterDrilldownDataset["optimizationSearchSpace"];
  const optimizationFrontier = clone(
    browserDataset.optimization_frontier ?? {},
  ) as ParameterDrilldownDataset["optimizationFrontier"];
  const optimizationV2 = clone(
    browserDataset.optimization_v2 ?? {},
  ) as ParameterDrilldownDataset["optimizationV2"];
  const capsuleSurvivabilityLab = clone(
    browserDataset.capsule_survivability_lab ?? {},
  ) as ParameterDrilldownDataset["capsuleSurvivabilityLab"];
  const capsuleRiskBudget = clone(
    browserDataset.capsule_risk_budget ?? {},
  ) as ParameterDrilldownDataset["capsuleRiskBudget"];
  const missionFeasibilityScreen = clone(
    browserDataset.mission_feasibility_screen ?? {},
  ) as ParameterDrilldownDataset["missionFeasibilityScreen"];
  const userMissionRunCatalog = clone(
    browserDataset.user_mission_run_catalog ?? {},
  ) as ParameterDrilldownDataset["userMissionRunCatalog"];
  const runtimeScenarioGeneration = clone(
    browserDataset.runtime_scenario_generation ?? {},
  ) as ParameterDrilldownDataset["runtimeScenarioGeneration"];
  const costProcurementArchitectureFeasibility = clone(
    browserDataset.cost_procurement_architecture_feasibility ?? {},
  ) as ParameterDrilldownDataset["costProcurementArchitectureFeasibility"];
  const externalValidationReviewPack = clone(
    browserDataset.external_validation_review_pack ?? {},
  ) as ParameterDrilldownDataset["externalValidationReviewPack"];
  const publicNarrativeHardening = clone(
    browserDataset.public_narrative_hardening ?? {},
  ) as ParameterDrilldownDataset["publicNarrativeHardening"];
  const externalValidationExecutionLedger = clone(
    browserDataset.external_validation_execution_ledger ?? {},
  ) as ParameterDrilldownDataset["externalValidationExecutionLedger"];
  const independentPhysicsBackendComparison = clone(
    browserDataset.independent_physics_backend_comparison ?? {},
  ) as ParameterDrilldownDataset["independentPhysicsBackendComparison"];
  const capsuleQualificationEvidencePack = clone(
    browserDataset.capsule_qualification_evidence_pack ?? {},
  ) as ParameterDrilldownDataset["capsuleQualificationEvidencePack"];
  const evidenceUpgradeClosure = clone(
    browserDataset.evidence_upgrade_closure ?? {},
  ) as ParameterDrilldownDataset["evidenceUpgradeClosure"];
  const externalReproductionKit = clone(
    browserDataset.external_reproduction_kit ?? {},
  ) as ParameterDrilldownDataset["externalReproductionKit"];
  const externalEvidenceIntake = clone(
    browserDataset.external_evidence_intake ?? {},
  ) as ParameterDrilldownDataset["externalEvidenceIntake"];
  const externalValidationCampaign = clone(
    browserDataset.external_validation_campaign ?? {},
  ) as ParameterDrilldownDataset["externalValidationCampaign"];
  const releaseCandidateReadiness = clone(
    browserDataset.release_candidate_readiness ?? {},
  ) as ParameterDrilldownDataset["releaseCandidateReadiness"];
  const missionProbabilityCoupling = clone(
    browserDataset.mission_probability_coupling ?? {},
  ) as ParameterDrilldownDataset["missionProbabilityCoupling"];
  const uncertaintyInteractions = clone(
    browserDataset.uncertainty_interactions ?? {},
  ) as ParameterDrilldownDataset["uncertaintyInteractions"];
  const evidenceUpgradeCampaign = clone(
    browserDataset.evidence_upgrade_campaign ?? {},
  ) as ParameterDrilldownDataset["evidenceUpgradeCampaign"];
  const missionDagV2Boundary = clone(
    browserDataset.mission_dag_v2_boundary ?? {},
  ) as ParameterDrilldownDataset["missionDagV2Boundary"];
  const roadmapClosure = clone(
    browserDataset.roadmap_closure ?? {},
  ) as ParameterDrilldownDataset["roadmapClosure"];

  if (manifest.schema_version !== "parameter_drilldown_manifest.v1") {
    errors.push(`manifest schema_version mismatch: ${manifest.schema_version}`);
  }
  if (manifest.public_scope !== "public_mission_parameters_only") {
    errors.push(
      `manifest public_scope must be public_mission_parameters_only: ${manifest.public_scope}`,
    );
  }
  if (manifest.ui_scope !== "mission_design_environment_only") {
    errors.push(
      `manifest ui_scope must be mission_design_environment_only: ${manifest.ui_scope}`,
    );
  }
  if (manifest.dynamic_trace_semantics !== "module_level_attribution") {
    errors.push(
      `manifest dynamic_trace_semantics must be module_level_attribution: ${manifest.dynamic_trace_semantics}`,
    );
  }
  if (!Array.isArray(manifest.parameters) || manifest.parameters.length === 0) {
    errors.push("manifest parameters must be a non-empty array");
    manifest.parameters = [];
  }

  if (pSuccessDefensibility.schema_version !== "p_success_defensibility.v1") {
    errors.push(
      `p_success defensibility schema_version mismatch: ${pSuccessDefensibility.schema_version}`,
    );
  }
  if (pSuccessDefensibility.formula !== "p_hit * p_survival * p_data_intact") {
    errors.push(`p_success defensibility formula mismatch: ${pSuccessDefensibility.formula}`);
  }
  if (!determinismStatus.golden_checksum) {
    errors.push("determinism status must provide golden_checksum");
  }

  validateObjectiveContract(objectiveContract, objectiveScoreBaseline, errors);
  validateOptimizationArtifacts(optimizationSearchSpace, optimizationFrontier, optimizationV2, errors);
  validateCapsuleSurvivabilityLab(capsuleSurvivabilityLab, errors);
  validateCapsuleRiskBudget(capsuleRiskBudget, errors);
  validateMissionFeasibilityScreen(missionFeasibilityScreen, errors);
  validateUserMissionRunCatalog(userMissionRunCatalog, errors);
  validateRuntimeScenarioGeneration(runtimeScenarioGeneration, errors);
  validateCostProcurementArchitectureFeasibility(costProcurementArchitectureFeasibility, errors);
  validateExternalValidationReviewPack(externalValidationReviewPack, errors);
  validatePublicNarrativeHardening(publicNarrativeHardening, errors);
  validateExternalProofPhase(
    {
      externalLedger: externalValidationExecutionLedger,
      physicsComparison: independentPhysicsBackendComparison,
      capsuleQualification: capsuleQualificationEvidencePack,
      evidenceClosure: evidenceUpgradeClosure,
      reproductionKit: externalReproductionKit,
      evidenceIntake: externalEvidenceIntake,
      validationCampaign: externalValidationCampaign,
      releaseCandidate: releaseCandidateReadiness,
    },
    errors,
  );
  validateMissionProbabilityCoupling(missionProbabilityCoupling, errors);
  validateUncertaintyInteractions(uncertaintyInteractions, errors);
  validateEvidenceUpgradeCampaign(evidenceUpgradeCampaign, errors);
  validateMissionDagV2Boundary(missionDagV2Boundary, errors);
  validateRoadmapClosure(roadmapClosure, errors);

  const { parameters, parameterById } = collectParameterMap({
    manifest,
    staticUsageGraph,
    evidenceIndex,
    errors,
  });
  const manifestIdSet = new Set(parameters.map((parameter) => parameter.parameter_id));

  for (const parameterId of Object.keys(staticUsageGraph)) {
    if (!manifestIdSet.has(parameterId)) {
      errors.push(`static usage graph contains non-public parameter: ${parameterId}`);
    }
  }
  for (const parameterId of Object.keys(evidenceIndex)) {
    if (!manifestIdSet.has(parameterId)) {
      errors.push(`evidence index contains non-public parameter: ${parameterId}`);
    }
  }

  if (manifest.parameter_count !== parameters.length) {
    errors.push(`manifest parameter_count mismatch: ${manifest.parameter_count} != ${parameters.length}`);
  }
  if (!isFiniteNumber(manifest.excluded_internal_parameter_count) || manifest.excluded_internal_parameter_count < 0) {
    errors.push(
      `manifest excluded_internal_parameter_count must be a non-negative number: ${String(manifest.excluded_internal_parameter_count)}`,
    );
  }
  if (
    !Array.isArray(manifest.internal_parameter_prefixes_excluded) ||
    !manifest.internal_parameter_prefixes_excluded.includes("code_literal.")
  ) {
    errors.push("manifest internal_parameter_prefixes_excluded must include code_literal.");
  }

  for (const parameterId of Object.keys(staticUsageGraph)) {
    if (!manifestIdSet.has(parameterId)) {
      errors.push(`static usage graph has parameter not present in manifest: ${parameterId}`);
    }
  }
  for (const parameterId of Object.keys(evidenceIndex)) {
    if (!manifestIdSet.has(parameterId)) {
      errors.push(`evidence index has parameter not present in manifest: ${parameterId}`);
    }
  }

  for (const parameter of parameters) {
    if (parameter.evidence_status.status !== "OK") {
      errors.push(
        `manifest evidence_status FAIL for ${parameter.parameter_id}: ${parameter.evidence_status.reason ?? "unknown"}`,
      );
    }
    if (!parameter.has_source) {
      errors.push(`manifest has_source=false for ${parameter.parameter_id}`);
    }
    if (!parameter.has_uncertainty) {
      errors.push(`manifest has_uncertainty=false for ${parameter.parameter_id}`);
    }
    if (parameter.defensibility_status !== "PASS") {
      errors.push(`manifest defensibility_status=FAIL for ${parameter.parameter_id}`);
    }
  }

  validateFailureSurface(failureSurfaceBaseline, manifestIdSet, errors);

  const dataset: ParameterDrilldownDataset = {
    manifest,
    staticUsageGraph,
    evidenceIndex,
    pSuccessDefensibility,
    failureSurfaceBaseline,
    objectiveContract,
    objectiveScoreBaseline,
    optimizationSearchSpace,
    optimizationFrontier,
    optimizationV2,
    capsuleSurvivabilityLab,
    capsuleRiskBudget,
    missionFeasibilityScreen,
    userMissionRunCatalog,
    runtimeScenarioGeneration,
    costProcurementArchitectureFeasibility,
    externalValidationReviewPack,
    publicNarrativeHardening,
    externalValidationExecutionLedger,
    independentPhysicsBackendComparison,
    capsuleQualificationEvidencePack,
    evidenceUpgradeClosure,
    externalReproductionKit,
    externalEvidenceIntake,
    externalValidationCampaign,
    releaseCandidateReadiness,
    missionProbabilityCoupling,
    uncertaintyInteractions,
    evidenceUpgradeCampaign,
    missionDagV2Boundary,
    roadmapClosure,
    determinismStatus,
    parameters,
    parameterById,
    errors,
  };

  if (errors.length > 0 && options.strict !== false) {
    throw new ParameterDrilldownDatasetError(errors);
  }

  return dataset;
}
