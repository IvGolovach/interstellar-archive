import type { FailureSurfaceBaseline } from "../../lib/parameter_drilldown_loader";

interface MissionTimeline2DProps {
  baseline: FailureSurfaceBaseline;
}

const STAGE_ORDER: Record<"S0" | "S1" | "S2" | "S3", number> = {
  S0: 0,
  S1: 1,
  S2: 2,
  S3: 3,
};

function formatProbability(value: number): string {
  return `${(value * 100).toFixed(3)}%`;
}

function statusClass(status: "PASS" | "FAIL" | "N/A"): string {
  if (status === "PASS") {
    return "timeline-stage-status pass";
  }
  if (status === "FAIL") {
    return "timeline-stage-status fail";
  }
  return "timeline-stage-status na";
}

export function MissionTimeline2D(props: MissionTimeline2DProps): JSX.Element {
  const { baseline } = props;
  const failureStage = baseline.outcome.failure_stage;
  const orderedTimeline = [...baseline.timeline].sort((left, right) => STAGE_ORDER[left.stage] - STAGE_ORDER[right.stage]);

  return (
    <article className="visualization-pane" aria-label="mission timeline visualization">
      <header className="visualization-pane-header">
        <h4>Mission Timeline (S0-S3)</h4>
        <p className="help-text mono-cell">
          outcome={baseline.outcome.outcome_class} | p_success={formatProbability(baseline.outcome.p_success)}
        </p>
        <p className="help-text mono-cell">
          failure_mode={baseline.outcome.failure_mode} | failure_stage={baseline.outcome.failure_stage}
        </p>
      </header>

      <div className="timeline-grid">
        {orderedTimeline.map((stageEntry) => {
          const isFailurePoint = failureStage !== "NONE" && stageEntry.stage === failureStage;
          return (
            <section
              key={stageEntry.stage}
              className={`timeline-stage-card${isFailurePoint ? " is-failure-point" : ""}`}
              aria-label={`stage ${stageEntry.stage}`}
            >
              <div className="timeline-stage-header">
                <p className="timeline-stage-label">{stageEntry.stage}</p>
                <p className={statusClass(stageEntry.status)}>{stageEntry.status}</p>
              </div>
              <p className="timeline-stage-summary">{stageEntry.summary}</p>
            </section>
          );
        })}
      </div>

      <section className="timeline-drivers">
        <h5>Dominant drivers (top-3)</h5>
        <p className="help-text mono-cell">
          method={baseline.dominant_drivers.method}; confidence={baseline.dominant_drivers.confidence}
        </p>
        <ol className="compact-list">
          {baseline.dominant_drivers.top3.map((driver) => (
            <li key={driver.parameter_id}>
              <a href={`#parameters/${encodeURIComponent(driver.parameter_id)}`} className="mono-cell">
                {driver.parameter_id}
              </a>{" "}
              <span className="help-text">({driver.reason})</span>
            </li>
          ))}
        </ol>
      </section>
    </article>
  );
}
