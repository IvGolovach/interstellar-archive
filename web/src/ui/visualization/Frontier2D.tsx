import type { ObjectiveScoreBaseline, OptimizationFrontierArtifact } from "../../lib/parameter_drilldown_loader";

interface Frontier2DProps {
  frontier: OptimizationFrontierArtifact;
  baselineScore: ObjectiveScoreBaseline;
  selectedCandidateId?: string | null;
}

interface PlotPoint {
  originalIndex: number;
  candidateId: string;
  pSuccess: number;
  riskEnvelope: number;
  dominantDrivers: string[];
  isPareto: boolean;
}

const PLOT_WIDTH = 700;
const PLOT_HEIGHT = 260;
const PLOT_PADDING = 32;

function clamp01(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  if (value < 0) {
    return 0;
  }
  if (value > 1) {
    return 1;
  }
  return value;
}

function formatScore(value: number): string {
  return Number.isFinite(value) ? value.toFixed(6) : "N/A";
}

function toPlotX(riskEnvelope: number): number {
  const normalized = clamp01(riskEnvelope);
  return PLOT_PADDING + normalized * (PLOT_WIDTH - PLOT_PADDING * 2);
}

function toPlotY(pSuccess: number): number {
  const normalized = clamp01(pSuccess);
  return PLOT_HEIGHT - PLOT_PADDING - normalized * (PLOT_HEIGHT - PLOT_PADDING * 2);
}

function buildSortedPoints(frontier: OptimizationFrontierArtifact): PlotPoint[] {
  const paretoIndexSet = new Set(frontier.pareto_frontier_indices);
  return frontier.points
    .map((point, index) => ({
      originalIndex: index,
      candidateId: point.candidate_id,
      pSuccess: point.scores.p_success,
      riskEnvelope: typeof point.scores.risk_envelope === "number" ? point.scores.risk_envelope : Number.NaN,
      dominantDrivers: point.dominant_drivers.parameter_ids,
      isPareto: paretoIndexSet.has(index),
    }))
    .sort((left, right) => {
      if (left.pSuccess !== right.pSuccess) {
        return right.pSuccess - left.pSuccess;
      }
      if (left.riskEnvelope !== right.riskEnvelope) {
        return left.riskEnvelope - right.riskEnvelope;
      }
      return left.candidateId.localeCompare(right.candidateId);
    });
}

export function Frontier2D(props: Frontier2DProps): JSX.Element {
  const { frontier, baselineScore, selectedCandidateId = null } = props;
  const points = buildSortedPoints(frontier);
  const quantile = points.length > 0 && typeof frontier.points[0].scores.risk_meta?.quantile === "number"
    ? frontier.points[0].scores.risk_meta.quantile
    : 0.05;

  if (points.length === 0) {
    return (
      <article className="visualization-pane" aria-label="optimization frontier visualization">
        <h4>Optimization Frontier (2D Pareto)</h4>
        <p>No frontier points available in tracked artifact.</p>
      </article>
    );
  }

  const baselinePoint = {
    pSuccess: baselineScore.scores.realistic.p_success,
    riskEnvelope: baselineScore.scores.realistic.risk_envelope ?? Number.NaN,
  };

  return (
    <article className="visualization-pane" aria-label="optimization frontier visualization">
      <header className="visualization-pane-header">
        <h4>Optimization Frontier (2D Pareto)</h4>
        <p className="help-text mono-cell">
          x=risk_envelope [0..1], y=p_success [0..1], method={frontier.method}, q={quantile}
        </p>
        <p className="help-text mono-cell">
          points={frontier.points.length}, pareto_size={frontier.pareto_frontier_indices.length}
        </p>
      </header>

      <svg className="frontier-plot" viewBox={`0 0 ${PLOT_WIDTH} ${PLOT_HEIGHT}`} role="img" aria-label="2D frontier scatter">
        <path
          className="line-chart-grid"
          d={`M${PLOT_PADDING} ${PLOT_PADDING} L${PLOT_WIDTH - PLOT_PADDING} ${PLOT_PADDING}
              M${PLOT_PADDING} ${PLOT_HEIGHT / 2} L${PLOT_WIDTH - PLOT_PADDING} ${PLOT_HEIGHT / 2}
              M${PLOT_PADDING} ${PLOT_HEIGHT - PLOT_PADDING} L${PLOT_WIDTH - PLOT_PADDING} ${PLOT_HEIGHT - PLOT_PADDING}
              M${PLOT_PADDING} ${PLOT_HEIGHT - PLOT_PADDING} L${PLOT_PADDING} ${PLOT_PADDING}
              M${PLOT_WIDTH - PLOT_PADDING} ${PLOT_HEIGHT - PLOT_PADDING} L${PLOT_WIDTH - PLOT_PADDING} ${PLOT_PADDING}`}
        />

        {points.map((point) => (
          <circle
            key={point.candidateId}
            cx={toPlotX(point.riskEnvelope)}
            cy={toPlotY(point.pSuccess)}
            r={point.isPareto ? 5.4 : 3.8}
            className={
              point.candidateId === selectedCandidateId
                ? "frontier-point frontier-point-selected"
                : point.isPareto
                  ? "frontier-point frontier-point-pareto"
                  : "frontier-point"
            }
          >
            <title>
              {`candidate=${point.candidateId}; p_success=${formatScore(point.pSuccess)}; risk_envelope=${formatScore(point.riskEnvelope)}; dominant_drivers=${point.dominantDrivers.join(",") || "none"}`}
            </title>
          </circle>
        ))}

        <circle
          cx={toPlotX(baselinePoint.riskEnvelope)}
          cy={toPlotY(baselinePoint.pSuccess)}
          r={5.2}
          className="frontier-point frontier-point-baseline"
        >
          <title>
            {`baseline; p_success=${formatScore(baselinePoint.pSuccess)}; risk_envelope=${formatScore(
              baselinePoint.riskEnvelope,
            )}`}
          </title>
        </circle>
      </svg>

      <div className="frontier-legend mono-cell">
        <span>green=pareto</span>
        <span>blue=baseline score</span>
        <span>brown=non-pareto</span>
      </div>
    </article>
  );
}
