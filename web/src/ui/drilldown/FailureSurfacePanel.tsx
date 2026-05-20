import type { SimOutput } from "../../../../sim/public/types";
import { PUBLIC_DATASET_PATHS } from "../../lib/artifact_public_contracts";
import type { FailureSurfaceBaseline } from "../../lib/parameter_drilldown_loader";

interface FailureSurfacePanelProps {
  baseline: FailureSurfaceBaseline;
  simulationOutput: SimOutput | null;
}

function formatProbability(value: number): string {
  return `${(value * 100).toFixed(3)}%`;
}

function formatOutcomeClass(value: FailureSurfaceBaseline["outcome"]["outcome_class"]): string {
  return value;
}

function outcomeBannerClass(outcomeClass: FailureSurfaceBaseline["outcome"]["outcome_class"]): string {
  if (outcomeClass === "SUCCESS") {
    return "failure-outcome-banner success";
  }
  if (outcomeClass === "UNHEALTHY") {
    return "failure-outcome-banner unhealthy";
  }
  if (outcomeClass === "INVALID") {
    return "failure-outcome-banner invalid";
  }
  return "failure-outcome-banner fail";
}

export function FailureSurfacePanel(props: FailureSurfacePanelProps): JSX.Element {
  const { baseline, simulationOutput } = props;
  const hasCurrentComparableRun = false;

  return (
    <article className="drilldown-section">
      <h3>Failure Surface &amp; Breakdown (baseline)</h3>
      <p className="help-text">
        Source: <code>{PUBLIC_DATASET_PATHS.failureSurfaceBaseline}</code> (tracked, deterministic).
      </p>

      <div className={outcomeBannerClass(baseline.outcome.outcome_class)}>
        <p className="failure-outcome-title">Outcome</p>
        <p className="failure-outcome-main">
          {formatOutcomeClass(baseline.outcome.outcome_class)} | p_success={formatProbability(baseline.outcome.p_success)}
        </p>
        <p className="failure-outcome-meta mono-cell">
          failure_mode={baseline.outcome.failure_mode} | failure_stage={baseline.outcome.failure_stage}
        </p>
      </div>

      <h4>Stage timeline (S0–S3)</h4>
      <ul className="compact-list mono-cell">
        {baseline.timeline.map((entry) => (
          <li key={entry.stage}>
            {entry.stage} | {entry.status} | {entry.summary}
          </li>
        ))}
      </ul>

      <h4>Dominant drivers (top-3)</h4>
      <p className="help-text mono-cell">
        method={baseline.dominant_drivers.method}; confidence={baseline.dominant_drivers.confidence}
      </p>
      <ul className="compact-list">
        {baseline.dominant_drivers.top3.map((item) => (
          <li key={item.parameter_id}>
            <a href={`#/parameters/${encodeURIComponent(item.parameter_id)}`} className="mono-cell">
              {item.parameter_id}
            </a>{" "}
            <span className="help-text">({item.reason})</span>
          </li>
        ))}
      </ul>

      <h4>Compare to baseline</h4>
      {simulationOutput === null ? (
        <p>Baseline only. Current run output is not loaded.</p>
      ) : hasCurrentComparableRun ? (
        <p>Current run comparison available.</p>
      ) : (
        <div>
          <p>
            Baseline only. The current browser run uses <code>sim_output.v1</code>, which does not expose mission
            failure-surface fields (`p_success`, `failure_mode`, `failure_stage`, driver attribution).
          </p>
          <ul className="compact-list mono-cell">
            <li>delta.p_success: N/A</li>
            <li>delta.failure_mode: N/A</li>
            <li>delta.failure_stage: N/A</li>
            <li>delta.drivers: N/A</li>
          </ul>
        </div>
      )}
    </article>
  );
}
