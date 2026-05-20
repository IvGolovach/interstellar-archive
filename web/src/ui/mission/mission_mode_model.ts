import type { SimSchema } from "../../../../sim/public/types";
import { nonPhysicalDifferences } from "../../lib/schema_loader";
import type {
  FailureSurfaceBaseline,
  ObjectiveScoreBaseline,
  OptimizationFrontierArtifact,
  OptimizationSearchSpaceArtifact,
} from "../../lib/parameter_drilldown_loader";

interface SearchSpaceByIdEntry {
  low: number;
  high: number;
  baseline: number;
}

export interface MissionProjection {
  selectedCandidateId: string | null;
  selectedFrontierIndex: number | null;
  projectedPSuccess: number;
  projectedRiskEnvelope: number | null;
  failureStage: FailureSurfaceBaseline["outcome"]["failure_stage"];
  failureMode: string;
  dominantDrivers: string[];
}

function toSearchSpaceMap(
  searchSpace: OptimizationSearchSpaceArtifact,
): Record<string, SearchSpaceByIdEntry> {
  const map: Record<string, SearchSpaceByIdEntry> = {};
  for (const entry of searchSpace.parameters_considered) {
    map[entry.parameter_id] = {
      low: entry.bounds[0],
      high: entry.bounds[1],
      baseline: entry.baseline_value,
    };
  }
  return map;
}

function absolute(value: number): number {
  return value >= 0 ? value : -value;
}

function normalizeDelta(value: number, reference: SearchSpaceByIdEntry): number {
  const span = reference.high - reference.low;
  if (span <= 0) {
    return 0;
  }
  return absolute(value) / span;
}

function readRiskEnvelope(point: OptimizationFrontierArtifact["points"][number]): number | null {
  const value = point.scores.risk_envelope;
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return null;
}

function compareCandidateIds(left: string, right: string): number {
  if (left < right) {
    return -1;
  }
  if (left > right) {
    return 1;
  }
  return 0;
}

export function isSpeculativeWarningActive(
  schema: SimSchema,
  params: Record<string, number>,
): boolean {
  return nonPhysicalDifferences(params, schema).length > 0;
}

export function selectFrontierPointForParams(args: {
  params: Record<string, number>;
  frontier: OptimizationFrontierArtifact;
  searchSpace: OptimizationSearchSpaceArtifact;
}): { selectedCandidateId: string | null; selectedFrontierIndex: number | null } {
  const { params, frontier, searchSpace } = args;
  if (frontier.points.length === 0 || searchSpace.parameters_considered.length === 0) {
    return { selectedCandidateId: null, selectedFrontierIndex: null };
  }

  const searchMap = toSearchSpaceMap(searchSpace);
  let bestDistance = Number.POSITIVE_INFINITY;
  let bestCandidateId: string | null = null;
  let bestIndex: number | null = null;

  frontier.points.forEach((point, index) => {
    let distance = 0;
    for (const [parameterId, reference] of Object.entries(searchMap)) {
      const inputValue = params[parameterId];
      const pointValueRaw = point.parameters[parameterId];
      const pointValue =
        typeof pointValueRaw === "number" && Number.isFinite(pointValueRaw)
          ? pointValueRaw
          : reference.baseline;
      const comparableInput = typeof inputValue === "number" && Number.isFinite(inputValue)
        ? inputValue
        : reference.baseline;
      distance += normalizeDelta(comparableInput - pointValue, reference);
    }

    const candidateId = point.candidate_id;
    const candidateIsBetter = distance < bestDistance;
    const tieBreak =
      distance === bestDistance &&
      bestCandidateId !== null &&
      compareCandidateIds(candidateId, bestCandidateId) < 0;
    if (candidateIsBetter || tieBreak) {
      bestDistance = distance;
      bestCandidateId = candidateId;
      bestIndex = index;
    }
  });

  return {
    selectedCandidateId: bestCandidateId,
    selectedFrontierIndex: bestIndex,
  };
}

export function buildMissionProjection(args: {
  params: Record<string, number>;
  baselineFailureSurface: FailureSurfaceBaseline;
  baselineObjectiveScore: ObjectiveScoreBaseline;
  frontier: OptimizationFrontierArtifact;
  searchSpace: OptimizationSearchSpaceArtifact;
}): MissionProjection {
  const {
    params,
    baselineFailureSurface,
    baselineObjectiveScore,
    frontier,
    searchSpace,
  } = args;
  const selected = selectFrontierPointForParams({ params, frontier, searchSpace });
  const selectedPoint = selected.selectedFrontierIndex === null
    ? null
    : frontier.points[selected.selectedFrontierIndex] ?? null;

  const fallbackPSuccess = baselineObjectiveScore.scores.realistic.p_success;
  const fallbackRisk = baselineObjectiveScore.scores.realistic.risk_envelope ?? null;

  const projectedPSuccess = selectedPoint ? selectedPoint.scores.p_success : fallbackPSuccess;
  const projectedRisk = selectedPoint ? readRiskEnvelope(selectedPoint) : fallbackRisk;
  const dominantDrivers = baselineFailureSurface.dominant_drivers.top3.map(
    (entry) => entry.parameter_id,
  ).slice(0, 3);

  return {
    selectedCandidateId: selected.selectedCandidateId,
    selectedFrontierIndex: selected.selectedFrontierIndex,
    projectedPSuccess,
    projectedRiskEnvelope: projectedRisk,
    failureStage: baselineFailureSurface.outcome.failure_stage,
    failureMode: baselineFailureSurface.outcome.failure_mode,
    dominantDrivers,
  };
}
