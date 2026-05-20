import type { MissionOptimizationPanelModel } from "./mission_mode_contract";
import { Frontier2D } from "../visualization/Frontier2D";

interface MissionOptimizationPanelProps {
  model: MissionOptimizationPanelModel;
}

export function MissionOptimizationPanel(props: MissionOptimizationPanelProps): JSX.Element {
  const { model } = props;

  return (
    <section className="panel mission-optimization-panel">
      <button
        type="button"
        className="section-toggle"
        onClick={model.onToggle}
      >
        <span>Optimization Panel</span>
        <span>{model.expanded ? "Hide" : "Show"}</span>
      </button>
      {model.expanded ? (
        <>
          <p className="help-text">
            Current frontier position:{" "}
            <code>{model.selectedCandidateId ?? "baseline-reference"}</code>
          </p>
          <Frontier2D
            frontier={model.frontier}
            baselineScore={model.baselineScore}
            selectedCandidateId={model.selectedCandidateId}
          />
        </>
      ) : null}
    </section>
  );
}
