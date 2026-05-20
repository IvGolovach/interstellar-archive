import type {
  RuntimeScenarioGenerationArtifact,
  RuntimeScenarioGenerationRow,
  UserMissionRunCatalogArtifact,
  UserMissionRunRow,
} from "../../lib/parameter_drilldown_loader";
import "./UserMissionRunPanel.css";

interface UserMissionRunPanelProps {
  artifact: UserMissionRunCatalogArtifact;
  runtimeArtifact: RuntimeScenarioGenerationArtifact;
  selectedRunId?: string;
  onSelectRun: (runId: string) => void;
}

function formatYears(years: number): string {
  if (years >= 1_000_000) {
    return `${(years / 1_000_000).toLocaleString("en-US", { maximumFractionDigits: 2 })} Myr`;
  }
  return `${years.toLocaleString("en-US", { maximumFractionDigits: 0 })} yr`;
}

function formatNumber(value: unknown, digits = 4): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("en-US", { maximumSignificantDigits: digits })
    : "N/A";
}

function pickRun(artifact: UserMissionRunCatalogArtifact, selectedRunId?: string): UserMissionRunRow {
  return (
    artifact.run_rows.find((row) => row.run_id === selectedRunId) ??
    artifact.run_rows.find((row) => row.run_id === artifact.default_run_id) ??
    artifact.run_rows[0]
  );
}

function pickRecipe(
  runtimeArtifact: RuntimeScenarioGenerationArtifact,
  runId: string,
): RuntimeScenarioGenerationRow | undefined {
  return runtimeArtifact.generation_rows.find((row) => row.run_id === runId);
}

function formatPatchValue(value: unknown): string {
  if (typeof value === "number") {
    return formatNumber(value);
  }
  if (typeof value === "string") {
    return value;
  }
  return value === null || value === undefined ? "N/A" : JSON.stringify(value);
}

export function UserMissionRunPanel({
  artifact,
  runtimeArtifact,
  selectedRunId,
  onSelectRun,
}: UserMissionRunPanelProps): JSX.Element {
  const requestedRunMissing =
    typeof selectedRunId === "string" &&
    selectedRunId.length > 0 &&
    !artifact.run_rows.some((row) => row.run_id === selectedRunId);
  const selected = pickRun(artifact, selectedRunId);
  const selection = selected.selection;
  const probability = selected.probability_snapshot;
  const templateArgs = selected.runtime_pack_template.args;
  const recipe = pickRecipe(runtimeArtifact, selected.run_id);

  return (
    <main className="mission-run-shell">
      <section className="mission-run-hero">
        <div>
          <p className="eyebrow">Selected Mission Run</p>
          <h2>{selection.target_label}</h2>
          <p className="help-text">{selected.run_id}</p>
        </div>
        <code>{runtimeArtifact.schema_version}</code>
      </section>

      {requestedRunMissing ? (
        <section className="panel mission-run-warning" role="status">
          <p className="eyebrow">Run Not Found</p>
          <h3>Requested run id is not in the committed catalog.</h3>
          <p className="help-text">Showing the default tracked run instead; no user-owned pack was loaded.</p>
        </section>
      ) : null}

      <section className="panel mission-run-selector" aria-label="Selected mission run">
        <label>
          <span>Run</span>
          <select value={selected.run_id} onChange={(event) => onSelectRun(event.currentTarget.value)}>
            {artifact.run_rows.map((row) => (
              <option key={row.run_id} value={row.run_id}>
                {row.selection.target_label} / {row.selection.velocity_label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="mission-run-metric-grid" aria-label="Selected run metrics">
        <article className="panel mission-run-metric">
          <p className="eyebrow">Flight Time</p>
          <p className="metric-value">{formatYears(selection.flight_years)}</p>
          <p className="help-text">{selection.velocity_label}</p>
        </article>
        <article className="panel mission-run-metric">
          <p className="eyebrow">Capsule p50</p>
          <p className="metric-value">{formatNumber(probability.capsule_survival_p50)}</p>
          <p className="help-text">risk snapshot only</p>
        </article>
        <article className="panel mission-run-metric">
          <p className="eyebrow">Coupled p50</p>
          <p className="metric-value">{formatNumber(probability.capsule_data_coupled_p50)}</p>
          <p className="help-text">capsule survival x data integrity</p>
        </article>
      </section>

      <section className="mission-run-detail-grid">
        <article className="mission-run-detail">
          <p className="eyebrow">Run Identity</p>
          <dl>
            <div>
              <dt>Selection hash</dt>
              <dd>{selected.selection_hash.slice(0, 16)}</dd>
            </div>
            <div>
              <dt>Feasibility row</dt>
              <dd>{selection.feasibility_row_id}</dd>
            </div>
            <div>
              <dt>Risk row</dt>
              <dd>{String(selected.source_refs["capsule_risk_budget_row_id"] ?? "N/A")}</dd>
            </div>
          </dl>
        </article>
        <article className="mission-run-detail">
          <p className="eyebrow">Local Review Pack</p>
          <dl>
            <div>
              <dt>Script</dt>
              <dd>{selected.runtime_pack_template.script}</dd>
            </div>
            <div>
              <dt>Mode</dt>
              <dd>{String(templateArgs["--mode"] ?? "dual")}</dd>
            </div>
            <div>
              <dt>Tracked writes</dt>
              <dd>{selected.runtime_pack_template.writes_tracked_files ? "yes" : "no"}</dd>
            </div>
          </dl>
        </article>
        <article className="mission-run-detail">
          <p className="eyebrow">Verdict Boundary</p>
          <h3>{selected.feasibility_status.status}</h3>
          <p className="help-text">local deterministic review pack, non-certifying</p>
        </article>
      </section>

      {recipe ? (
        <section className="mission-run-recipe">
          <article className="mission-run-detail">
            <p className="eyebrow">Run Recipe</p>
            <pre>{recipe.command_preview}</pre>
            <p className="help-text">{runtimeArtifact.scenario_generation_contract.browser_execution_policy}</p>
          </article>
          <article className="mission-run-detail">
            <p className="eyebrow">Compiled Scenario Preview</p>
            <dl>
              {Object.entries(recipe.compiled_scenario_delta).map(([field, value]) => (
                <div key={field}>
                  <dt>{field}</dt>
                  <dd>{formatPatchValue(value)}</dd>
                </div>
              ))}
            </dl>
          </article>
          <article className="mission-run-detail">
            <p className="eyebrow">Expected Pack Files</p>
            <ul className="mission-run-list">
              {recipe.run_pack_contract.output_files.map((file) => (
                <li key={file}>{file}</li>
              ))}
            </ul>
          </article>
        </section>
      ) : null}

      <section className="mission-run-list-section">
        <article>
          <p className="eyebrow">External Evidence Still Required</p>
          <ul className="mission-run-list">
            {selected.external_evidence_gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </article>
        <article>
          <p className="eyebrow">Blocked Claims</p>
          <ul className="mission-run-list">
            {selected.blocked_claims.map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
