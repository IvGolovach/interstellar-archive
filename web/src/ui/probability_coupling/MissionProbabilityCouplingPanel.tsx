import type {
  MissionProbabilityCouplingArtifact,
  MissionProbabilityCouplingRow,
} from "../../lib/parameter_drilldown_loader";
import "./MissionProbabilityCouplingPanel.css";

interface MissionProbabilityCouplingPanelProps {
  artifact: MissionProbabilityCouplingArtifact;
  selectedCouplingId?: string;
  onSelectCoupling: (couplingId: string) => void;
}

function formatProbability(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("en-US", { maximumSignificantDigits: 4 })
    : "open";
}

function formatYears(years: number): string {
  if (years >= 1_000_000) {
    return `${(years / 1_000_000).toLocaleString("en-US", { maximumFractionDigits: 2 })} Myr`;
  }
  return `${Math.round(years).toLocaleString("en-US")} yr`;
}

function pickRow(artifact: MissionProbabilityCouplingArtifact, selectedCouplingId?: string): MissionProbabilityCouplingRow {
  return (
    artifact.coupling_rows.find((row) => row.coupling_id === selectedCouplingId) ??
    artifact.coupling_rows.find((row) => row.coupling_id === artifact.default_coupling_id) ??
    artifact.coupling_rows[0]
  );
}

export function MissionProbabilityCouplingPanel({
  artifact,
  selectedCouplingId,
  onSelectCoupling,
}: MissionProbabilityCouplingPanelProps): JSX.Element {
  const selected = pickRow(artifact, selectedCouplingId);
  const closed = selected.closed_capsule_data_probability;
  const full = selected.full_mission_probability;
  const dag = selected.dag_snapshot;

  return (
    <main className="probability-coupling-shell">
      <section className="probability-coupling-hero">
        <div>
          <p className="eyebrow">Mission Probability Coupling</p>
          <h2>{selected.target_label}</h2>
          <p className="help-text">{selected.coupling_id}</p>
        </div>
        <code>{artifact.schema_version}</code>
      </section>

      <section className="panel probability-coupling-selector" aria-label="Selected probability coupling">
        <label>
          <span>Coupling</span>
          <select value={selected.coupling_id} onChange={(event) => onSelectCoupling(event.currentTarget.value)}>
            {artifact.coupling_rows.map((row) => (
              <option key={row.coupling_id} value={row.coupling_id}>
                {row.target_label} / {row.velocity_label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="probability-metric-grid" aria-label="Probability coupling metrics">
        <article className="panel probability-metric">
          <p className="eyebrow">Full Mission p50</p>
          <p className="metric-value">{formatProbability(full.p50)}</p>
          <p className="help-text">{full.status}</p>
        </article>
        <article className="panel probability-metric">
          <p className="eyebrow">Capsule/Data p50</p>
          <p className="metric-value">{formatProbability(closed.p50)}</p>
          <p className="help-text">{closed.status}</p>
        </article>
        <article className="panel probability-metric">
          <p className="eyebrow">DAG Manifest</p>
          <p className="metric-value small">{dag.manifest_hash.slice(0, 12)}</p>
          <p className="help-text">{dag.hashchain_status}</p>
        </article>
      </section>

      <section className="probability-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Factor Budget</p>
            <h3>{formatYears(selected.flight_years)} at {selected.velocity_label}</h3>
          </div>
          <code>{selected.run_id}</code>
        </div>
        <div className="factor-grid">
          {selected.factor_budget.map((factor) => (
            <article key={factor.factor_id} className="factor-row">
              <div>
                <p>{factor.label}</p>
                <span>{factor.status}</span>
              </div>
              <strong>{formatProbability(factor.value_p50)}</strong>
            </article>
          ))}
        </div>
      </section>

      <section className="probability-detail-grid">
        <article className="probability-detail">
          <p className="eyebrow">DAG Snapshot</p>
          <dl>
            <div>
              <dt>Modes</dt>
              <dd>{dag.execution_modes.join(", ")}</dd>
            </div>
            <div>
              <dt>Modules</dt>
              <dd>{dag.module_artifact_count}</dd>
            </div>
            <div>
              <dt>Taxonomy</dt>
              <dd>{dag.failure_taxonomy_status}</dd>
            </div>
          </dl>
        </article>
        <article className="probability-detail">
          <p className="eyebrow">Risk Snapshot</p>
          <dl>
            <div>
              <dt>Status</dt>
              <dd>{String(selected.risk_budget_snapshot.status ?? "N/A")}</dd>
            </div>
            <div>
              <dt>Open factors</dt>
              <dd>{selected.open_external_factor_count}</dd>
            </div>
            <div>
              <dt>Closed factors</dt>
              <dd>{selected.closed_factor_count}</dd>
            </div>
          </dl>
        </article>
      </section>

      <section className="probability-list-section">
        <article>
          <p className="eyebrow">External Evidence Still Required</p>
          <ul className="probability-list">
            {selected.external_evidence_gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </article>
        <article>
          <p className="eyebrow">Blocked Claims</p>
          <ul className="probability-list">
            {selected.blocked_claims.map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
