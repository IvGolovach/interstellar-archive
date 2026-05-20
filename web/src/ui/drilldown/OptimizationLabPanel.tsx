import { useMemo } from "react";

import { PUBLIC_DATASET_PATHS } from "../../lib/artifact_public_contracts";
import type {
  ObjectiveContract,
  OptimizationFrontierArtifact,
  OptimizationSearchSpaceArtifact,
  OptimizationV2Artifact,
} from "../../lib/parameter_drilldown_loader";

interface OptimizationLabPanelProps {
  contract: ObjectiveContract;
  frontier: OptimizationFrontierArtifact;
  optimizationV2: OptimizationV2Artifact;
  searchSpace: OptimizationSearchSpaceArtifact;
  selectedCandidateId?: string;
}

function formatScore(value: number): string {
  if (!Number.isFinite(value)) {
    return "N/A";
  }
  return value.toFixed(6);
}

interface ScatterPoint {
  id: string;
  x: number;
  y: number;
  pSuccess: number;
  riskEnvelope: number;
  isPareto: boolean;
  paramsLabel: string;
}

function buildScatter(
  points: OptimizationFrontierArtifact["points"],
  paretoIndices: number[],
): {
  points: ScatterPoint[];
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
} {
  if (!Array.isArray(points) || points.length === 0) {
    return { points: [], xMin: 0, xMax: 1, yMin: 0, yMax: 1 };
  }
  const width = 620;
  const height = 220;
  const padding = 24;

  const xMin = Math.min(...points.map((point) => point.scores.p_success));
  const xMax = Math.max(...points.map((point) => point.scores.p_success));
  const xSpan = xMax - xMin || 1;

  const riskValues = points.map((point) =>
    typeof point.scores.risk_envelope === "number" ? point.scores.risk_envelope : 0,
  );
  const yMin = Math.min(...riskValues);
  const yMax = Math.max(...riskValues);
  const ySpan = yMax - yMin || 1;

  const paretoSet = new Set<number>(paretoIndices);
  const scatterPoints = points.map((point, index) => {
    const riskEnvelope = riskValues[index];
    const x = padding + ((point.scores.p_success - xMin) / xSpan) * (width - padding * 2);
    const y = height - padding - ((riskEnvelope - yMin) / ySpan) * (height - padding * 2);
    return {
      id: point.candidate_id,
      x,
      y,
      pSuccess: point.scores.p_success,
      riskEnvelope,
      isPareto: paretoSet.has(index),
      paramsLabel: JSON.stringify(point.parameters),
    };
  });

  return {
    points: scatterPoints,
    xMin,
    xMax,
    yMin,
    yMax,
  };
}

export function OptimizationLabPanel(props: OptimizationLabPanelProps): JSX.Element {
  const { contract, frontier, optimizationV2, searchSpace, selectedCandidateId } = props;
  const scatter = useMemo(
    () => buildScatter(frontier.points, frontier.pareto_frontier_indices),
    [frontier.points, frontier.pareto_frontier_indices],
  );
  const topCandidates = useMemo(
    () => optimizationV2.candidates.filter((candidate) => candidate.pareto_frontier_member).slice(0, 5),
    [optimizationV2.candidates],
  );
  const selectedCandidate = useMemo(() => {
    if (!selectedCandidateId) {
      return topCandidates[0] ?? optimizationV2.candidates[0];
    }
    return optimizationV2.candidates.find((candidate) => candidate.candidate_id === selectedCandidateId);
  }, [optimizationV2.candidates, selectedCandidateId, topCandidates]);
  const riskQuantile = useMemo(() => {
    const raw = contract.definitions?.risk_envelope?.quantile;
    return typeof raw === "number" && Number.isFinite(raw) ? raw : 0.05;
  }, [contract]);

  const frontierHref = useMemo(
    () =>
      `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(frontier, null, 2))}`,
    [frontier],
  );
  const optimizationV2Href = useMemo(
    () =>
      `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(optimizationV2, null, 2))}`,
    [optimizationV2],
  );

  return (
    <article className="drilldown-section">
      <h3>Optimization Lab (v2 decision surface)</h3>
      <p className="help-text">
        Sources: <code>{PUBLIC_DATASET_PATHS.objectiveContract}</code>,{" "}
        <code>{PUBLIC_DATASET_PATHS.optimizationSearchSpace}</code>,{" "}
        <code>{PUBLIC_DATASET_PATHS.optimizationFrontier}</code>,{" "}
        <code>{PUBLIC_DATASET_PATHS.optimizationV2}</code>
      </p>

      <h4>Objective contract summary</h4>
      <ul className="compact-list mono-cell">
        <li>mode: realistic</li>
        <li>primary: {contract.objective_sets.realistic.primary.metric}</li>
        <li>aggregation: {contract.objective_sets.realistic.aggregation.type}</li>
        <li>dimensions: {(contract.objective_sets.realistic.aggregation.dimensions ?? []).join(" x ")}</li>
        <li>trust filter: {searchSpace.trust_filter}</li>
        <li>
          search space: {searchSpace.parameters_considered.length} considered / {searchSpace.excluded_parameters.length} public excluded / {searchSpace.excluded_internal_parameter_count} internal constants omitted
        </li>
      </ul>

      <h4>Optimization v2 axes</h4>
      <ul className="compact-list mono-cell">
        <li>aggregation: {optimizationV2.rollup.aggregation_policy}</li>
        <li>axes: {optimizationV2.rollup.axis_ids.join(" x ")}</li>
        <li>candidates: {optimizationV2.candidate_count} source / {optimizationV2.frontier_candidate_count} Pareto</li>
        <li>cost calibration: {optimizationV2.rollup.calibrated_cost_model_available ? "closed" : "external required"}</li>
        <li>qualification: {optimizationV2.rollup.qualification_complete ? "complete" : "gap screen only"}</li>
      </ul>

      <h4>Frontier scatter (2D)</h4>
      <svg className="optimization-scatter" viewBox="0 0 620 220" role="img" aria-label="optimization frontier scatter">
        <path className="line-chart-grid" d="M24 24 L596 24 M24 110 L596 110 M24 196 L596 196 M24 196 L24 24 M596 196 L596 24" />
        {scatter.points.map((point) => (
          <circle
            key={point.id}
            cx={point.x}
            cy={point.y}
            r={point.isPareto ? 5.5 : 4.0}
            className={point.isPareto ? "optimization-point optimization-point-pareto" : "optimization-point"}
          >
            <title>
              {`${point.id} | p_success=${formatScore(point.pSuccess)} | risk_envelope=${formatScore(point.riskEnvelope)} | pareto=${point.isPareto ? "yes" : "no"} | parameters=${point.paramsLabel}`}
            </title>
          </circle>
        ))}
      </svg>
      <p className="help-text mono-cell">
        x-axis: p_success [{formatScore(scatter.xMin)}..{formatScore(scatter.xMax)}], y-axis:
        risk_envelope [{formatScore(scatter.yMin)}..{formatScore(scatter.yMax)}], method: lower_quantile q=
        {riskQuantile}, evaluations: {frontier.evaluation_count}, pareto_size: {frontier.pareto_frontier_indices.length}
      </p>

      <h4>Pareto candidate points</h4>
      <ol className="compact-list mono-cell">
        {topCandidates.map((candidate) => (
          <li key={candidate.candidate_id}>
            {candidate.candidate_id} | p_success={formatScore(candidate.scores.p_success)} | risk_envelope=
            {formatScore(candidate.scores.risk_envelope)} | qualification_gap=
            {formatScore(candidate.scores.qualification_gap)} | cost_proxy=
            {formatScore(candidate.scores.cost_proxy)}
          </li>
        ))}
      </ol>

      {selectedCandidateId && !selectedCandidate ? (
        <>
          <h4>Selected candidate</h4>
          <p className="help-text mono-cell">
            candidate id not found in optimization_v2_frontier.v1: {selectedCandidateId}
          </p>
        </>
      ) : null}

      {selectedCandidate ? (
        <>
          <h4>Selected candidate</h4>
          <ul className="compact-list mono-cell">
            <li>{selectedCandidate.candidate_id} from {selectedCandidate.source_candidate_id}</li>
            <li>objective_vector: [{selectedCandidate.scores.objective_vector.map((value) => formatScore(value)).join(", ")}]</li>
            <li>rank: {selectedCandidate.scores.rank_key}</li>
            <li>source v1 Pareto: {selectedCandidate.source_v1_pareto_member ? "yes" : "no"}</li>
            <li>v2 Pareto: {selectedCandidate.pareto_frontier_member ? "yes" : "no"}</li>
          </ul>
        </>
      ) : null}

      <h4>External evidence still required</h4>
      <ul className="compact-list">
        {optimizationV2.external_evidence_gaps.map((gap) => (
          <li key={gap}>{gap}</li>
        ))}
      </ul>

      <h4>Blocked claims</h4>
      <ul className="compact-list">
        {optimizationV2.blocked_claims.map((claim) => (
          <li key={claim}>{claim}</li>
        ))}
      </ul>

      <h4>Artifact link</h4>
      <p className="compact-list">
        <a href={optimizationV2Href} download="optimization_v2_frontier.v1.json">
          Open optimization v2 artifact JSON
        </a>{" "}
        <a href={frontierHref} download="optimization_frontier_realistic.v1.json">
          Open full frontier artifact JSON
        </a>
      </p>
    </article>
  );
}
