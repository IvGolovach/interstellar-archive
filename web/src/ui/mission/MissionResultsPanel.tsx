import type { MissionResultsPanelModel } from "./mission_mode_contract";
import { formatScore } from "./mission_mode_helpers";

interface MissionResultsPanelProps {
  model: MissionResultsPanelModel;
}

export function MissionResultsPanel(props: MissionResultsPanelProps): JSX.Element {
  const { model } = props;
  const lastRun = model.lastRun;
  const hasLastRun = lastRun !== null;

  return (
    <section className="panel mission-results-panel">
      <h2>Results Panel</h2>
      {model.runError ? <p className="error-text">{model.runError}</p> : null}
      {hasLastRun ? <h3>Projected from static frontier</h3> : null}
      <div className="mission-results-grid">
        <article className="metric-card">
          <p className="metric-label">
            {hasLastRun
              ? "Projected success probability (p_success)"
              : "Success probability (p_success)"}
          </p>
          <p className="metric-value">{formatScore(model.projection.projectedPSuccess)}</p>
          <p className="metric-unit">
            {hasLastRun ? "static frontier projection" : "realistic-mode proxy output"}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">{hasLastRun ? "Projected risk envelope" : "Risk envelope"}</p>
          <p className="metric-value">{formatScore(model.projection.projectedRiskEnvelope)}</p>
          <p className="metric-unit">
            {hasLastRun ? "static frontier projection" : "lower-tail downside"}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">{hasLastRun ? "Baseline failure stage" : "Failure stage"}</p>
          <p className="metric-value">{model.projection.failureStage}</p>
          <p className="metric-unit">{hasLastRun ? "static failure surface" : "taxonomy stage"}</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">{hasLastRun ? "Baseline failure mode" : "Failure mode"}</p>
          <p className="metric-value mission-long-value">{model.projection.failureMode}</p>
          <p className="metric-unit">
            {hasLastRun ? "static failure surface" : "baseline failure surface"}
          </p>
        </article>
      </div>
      <div className="mission-drivers">
        <h3>{hasLastRun ? "Projected dominant drivers" : "Dominant drivers"}</h3>
        <ol className="compact-list">
          {model.projection.dominantDrivers.map((parameterId) => (
            <li key={parameterId}>
              <span className="mono-cell">{parameterId}</span>
            </li>
          ))}
        </ol>
      </div>
      {lastRun ? (
        <div className="mission-last-run">
          <h3>Last run output</h3>
          <div className="mission-results-grid">
            <article className="metric-card">
              <p className="metric-label">Encounter likelihood</p>
              <p className="metric-value">
                {formatScore(lastRun.output.derived_metrics.encounter_likelihood_percent)}
              </p>
              <p className="metric-unit">percent from runSimulation</p>
            </article>
            <article className="metric-card">
              <p className="metric-label">Finite control window</p>
              <p className="metric-value">
                {formatScore(lastRun.output.derived_metrics.finite_control_window_year)}
              </p>
              <p className="metric-unit">years from runSimulation</p>
            </article>
            <article className="metric-card">
              <p className="metric-label">Expected mm-tail hits</p>
              <p className="metric-value">
                {formatScore(lastRun.output.derived_metrics.expected_mm_tail_hits)}
              </p>
              <p className="metric-unit">hits from runSimulation</p>
            </article>
            <article className="metric-card">
              <p className="metric-label">Shield survival margin</p>
              <p className="metric-value">
                {formatScore(lastRun.output.derived_metrics.shield_survival_margin)}
              </p>
              <p className="metric-unit">ratio from runSimulation</p>
            </article>
            <article className="metric-card">
              <p className="metric-label">Golden checksum</p>
              <p className="metric-value mission-long-value mono-cell">
                {lastRun.output.golden_checksum}
              </p>
              <p className="metric-unit">last run checksum</p>
            </article>
            <article className="metric-card">
              <p className="metric-label">Run invariants</p>
              <p className="metric-value">{lastRun.output.invariants_passed ? "pass" : "fail"}</p>
              <p className="metric-unit">
                {lastRun.output.engine_version} / {lastRun.output.schema_version}
              </p>
            </article>
          </div>
          <div className="mission-drivers">
            <h3>Warnings</h3>
            {lastRun.output.warnings.length > 0 ? (
              <ul className="compact-list">
                {lastRun.output.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : (
              <p className="help-text">No warnings emitted by runSimulation.</p>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}
