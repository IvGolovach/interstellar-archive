import type { FailureSurfaceBaseline } from "../../lib/parameter_drilldown_loader";

interface MissionStageTimelineProps {
  baseline: FailureSurfaceBaseline;
}

const STAGE_DESCRIPTIONS: Record<"S0" | "S1" | "S2" | "S3", string> = {
  S0: "Initialization and launch assumptions are established.",
  S1: "Cruise phase where uncertainty and guidance drift accumulate.",
  S2: "Approach and interaction corridor where correction leverage decays.",
  S3: "Data integrity and survivability checkpoint at mission outcome.",
};

function statusClass(status: "PASS" | "FAIL" | "N/A"): string {
  if (status === "PASS") {
    return "mission-stage-status pass";
  }
  if (status === "FAIL") {
    return "mission-stage-status fail";
  }
  return "mission-stage-status na";
}

function riskLabel(status: "PASS" | "FAIL" | "N/A"): string {
  if (status === "PASS") {
    return "Low risk";
  }
  if (status === "FAIL") {
    return "High risk";
  }
  return "Unknown risk";
}

export function MissionStageTimeline(props: MissionStageTimelineProps): JSX.Element {
  const { baseline } = props;
  return (
    <section className="panel mission-stage-panel">
      <h2>Mission Stage Timeline (S0-S3)</h2>
      <div className="mission-stage-grid">
        {baseline.timeline.map((entry) => {
          const stage = entry.stage;
          const isFailure = baseline.outcome.failure_stage === stage;
          return (
            <article
              key={stage}
              className={`mission-stage-card${isFailure ? " mission-stage-card-failure" : ""}`}
            >
              <header className="mission-stage-card-header">
                <p className="mission-stage-name">{stage}</p>
                <span className={statusClass(entry.status)}>{entry.status}</span>
              </header>
              <p className="mission-stage-description">{STAGE_DESCRIPTIONS[stage]}</p>
              <p className="mission-stage-summary">{entry.summary}</p>
              <p className="mission-stage-risk">{riskLabel(entry.status)}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
