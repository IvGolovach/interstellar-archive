import { formatPercent } from "./mission_mode_helpers";
import type { MissionModeOverviewModel } from "./mission_mode_contract";

interface MissionModeOverviewProps {
  model: MissionModeOverviewModel;
}

export function MissionModeOverview(props: MissionModeOverviewProps): JSX.Element {
  const { model } = props;

  return (
    <header className="hero mission-overview">
      <p className="eyebrow">Mission Mode</p>
      <h1>Horizon-Crossing Mission Interface</h1>
      <p className="hero-copy">
        This interface treats the run as a mission story: stage timeline, parameter controls, deterministic run, and
        provenance-linked outcomes with explicit assumption boundaries. Physical laws are locked; engineering and
        speculative controls are explicit.
      </p>
      <div className="mission-overview-summary">
        <p>
          Success contract: <code>p_success = p_hit * p_survival * p_data_intact</code>
        </p>
        <p>
          Current baseline result: <strong>{formatPercent(model.baselinePSuccess)}</strong> (realistic mode)
        </p>
      </div>
      <button type="button" className="mission-run-button" onClick={model.onRunMission}>
        🚀 Run Mission
      </button>
    </header>
  );
}
