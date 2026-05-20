import { useMemo, useState } from "react";

import { PUBLIC_DATASET_PATHS } from "../../lib/artifact_public_contracts";
import type {
  FailureSurfaceBaseline,
  ObjectiveScoreBaseline,
  OptimizationFrontierArtifact,
} from "../../lib/parameter_drilldown_loader";
import { Frontier2D } from "./Frontier2D";
import { MissionTimeline2D } from "./MissionTimeline2D";

interface VisualizationLayerPanelProps {
  failureSurfaceBaseline: FailureSurfaceBaseline;
  optimizationFrontier: OptimizationFrontierArtifact;
  objectiveScoreBaseline: ObjectiveScoreBaseline;
  initialVisualizationEnabled?: boolean;
  initialTab?: "timeline" | "frontier";
}

function formatProbability(value: number): string {
  return `${(value * 100).toFixed(3)}%`;
}

export function VisualizationLayerPanel(props: VisualizationLayerPanelProps): JSX.Element {
  const {
    failureSurfaceBaseline,
    optimizationFrontier,
    objectiveScoreBaseline,
    initialVisualizationEnabled = false,
    initialTab = "timeline",
  } = props;

  const [visualizationEnabled, setVisualizationEnabled] = useState<boolean>(initialVisualizationEnabled);
  const [activeTab, setActiveTab] = useState<"timeline" | "frontier">(initialTab);

  const baselineSummary = useMemo(
    () => ({
      outcomeClass: failureSurfaceBaseline.outcome.outcome_class,
      pSuccess: failureSurfaceBaseline.outcome.p_success,
      failureMode: failureSurfaceBaseline.outcome.failure_mode,
      failureStage: failureSurfaceBaseline.outcome.failure_stage,
      frontierPoints: optimizationFrontier.points.length,
      paretoSize: optimizationFrontier.pareto_frontier_indices.length,
      baselineRisk: objectiveScoreBaseline.scores.realistic.risk_envelope,
    }),
    [failureSurfaceBaseline, optimizationFrontier, objectiveScoreBaseline],
  );

  return (
    <article className="drilldown-section visualization-shell">
      <h3>Visualization Layer (Data-driven, deterministic)</h3>
      <p className="help-text">
        Sources: <code>{PUBLIC_DATASET_PATHS.failureSurfaceBaseline}</code>,{" "}
        <code>{PUBLIC_DATASET_PATHS.optimizationFrontier}</code>,{" "}
        <code>{PUBLIC_DATASET_PATHS.objectiveScoreBaseline}</code>
      </p>

      <div className="visualization-toolbar">
        <label className="checkbox-row visualization-toggle">
          <input
            type="checkbox"
            checked={visualizationEnabled}
            onChange={(event) => setVisualizationEnabled(event.target.checked)}
          />
          <span>Visualization: {visualizationEnabled ? "ON" : "OFF"}</span>
        </label>
      </div>

      {!visualizationEnabled ? (
        <div className="visualization-text-only">
          <p>Text-only research mode. Enable visualization to inspect timeline and frontier graphics.</p>
          <ul className="compact-list mono-cell">
            <li>outcome_class={baselineSummary.outcomeClass}</li>
            <li>p_success={formatProbability(baselineSummary.pSuccess)}</li>
            <li>failure_mode={baselineSummary.failureMode}</li>
            <li>failure_stage={baselineSummary.failureStage}</li>
            <li>frontier_points={baselineSummary.frontierPoints}</li>
            <li>pareto_size={baselineSummary.paretoSize}</li>
            <li>baseline_risk_envelope={baselineSummary.baselineRisk ?? "N/A"}</li>
          </ul>
        </div>
      ) : (
        <>
          <div className="visualization-tab-row" role="tablist" aria-label="visualization views">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "timeline"}
              className={`visualization-tab${activeTab === "timeline" ? " active" : ""}`}
              onClick={() => setActiveTab("timeline")}
            >
              Timeline (A)
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "frontier"}
              className={`visualization-tab${activeTab === "frontier" ? " active" : ""}`}
              onClick={() => setActiveTab("frontier")}
            >
              Frontier (B)
            </button>
          </div>

          {activeTab === "timeline" ? <MissionTimeline2D baseline={failureSurfaceBaseline} /> : null}
          {activeTab === "frontier" ? (
            <Frontier2D frontier={optimizationFrontier} baselineScore={objectiveScoreBaseline} />
          ) : null}
        </>
      )}
    </article>
  );
}
