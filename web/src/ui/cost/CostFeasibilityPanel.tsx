import { useMemo, useState } from "react";

import type {
  CostArchitectureRow,
  CostProcurementArchitectureFeasibilityArtifact,
} from "../../lib/parameter_drilldown_loader";
import "./CostFeasibilityPanel.css";

interface CostFeasibilityPanelProps {
  artifact: CostProcurementArchitectureFeasibilityArtifact;
}

interface Option {
  id: string;
  label: string;
}

function formatNumber(value: unknown, digits = 4): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("en-US", { maximumSignificantDigits: digits })
    : "N/A";
}

function formatMoney(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `$${value.toLocaleString("en-US", { maximumFractionDigits: 2 })}M`
    : "N/A";
}

function formatYears(years: number): string {
  if (years >= 1_000_000) {
    return `${(years / 1_000_000).toLocaleString("en-US", { maximumFractionDigits: 2 })} Myr`;
  }
  return `${years.toLocaleString("en-US", { maximumFractionDigits: 0 })} yr`;
}

function uniqueOptions(rows: CostArchitectureRow[], key: "target_id" | "velocity_id", label: "target_label" | "velocity_label"): Option[] {
  const seen = new Map<string, string>();
  for (const row of rows) {
    if (!seen.has(row[key])) {
      seen.set(row[key], row[label]);
    }
  }
  return Array.from(seen, ([id, optionLabel]) => ({ id, label: optionLabel }));
}

function pickDefaultRow(artifact: CostProcurementArchitectureFeasibilityArtifact): CostArchitectureRow {
  return artifact.architecture_rows.find((row) => row.is_default_reference) ?? artifact.architecture_rows[0];
}

export function CostFeasibilityPanel({ artifact }: CostFeasibilityPanelProps): JSX.Element {
  const defaultRow = pickDefaultRow(artifact);
  const [targetId, setTargetId] = useState(defaultRow.target_id);
  const [velocityId, setVelocityId] = useState(defaultRow.velocity_id);
  const targetOptions = useMemo(
    () => uniqueOptions(artifact.architecture_rows, "target_id", "target_label"),
    [artifact.architecture_rows],
  );
  const velocityOptions = useMemo(
    () => uniqueOptions(artifact.architecture_rows, "velocity_id", "velocity_label"),
    [artifact.architecture_rows],
  );
  const selectedRow =
    artifact.architecture_rows.find((row) => row.target_id === targetId && row.velocity_id === velocityId) ??
    defaultRow;

  return (
    <main className="cost-shell">
      <section className="cost-hero">
        <div>
          <p className="eyebrow">Roadmap 13</p>
          <h2>Cost, Procurement &amp; Architecture</h2>
          <p className="help-text">{artifact.cost_model.cost_boundary}</p>
        </div>
        <code>{artifact.schema_version}</code>
      </section>

      <section className="panel cost-boundary" aria-label="Cost claim boundaries">
        <div>
          <p className="eyebrow">Procurement Boundary</p>
          <p>{artifact.claim_boundaries.procurement_status}</p>
        </div>
        <div>
          <p className="eyebrow">Architecture Boundary</p>
          <p>{artifact.claim_boundaries.architecture_status}</p>
        </div>
        <div>
          <p className="eyebrow">Rows</p>
          <p>{artifact.architecture_row_count} review rows</p>
        </div>
      </section>

      <section className="cost-metric-grid" aria-label="Cost screening proxies">
        <article className="panel cost-metric">
          <p className="eyebrow">Capsule Mass</p>
          <p className="metric-value">{formatNumber(artifact.cost_model.capsule_mass_kg)} kg</p>
          <p className="help-text">tracked mass budget</p>
        </article>
        <article className="panel cost-metric">
          <p className="eyebrow">Qualification Proxy</p>
          <p className="metric-value">{formatMoney(artifact.cost_model.qualification_cost_proxy_musd)}</p>
          <p className="help-text">not a vendor estimate</p>
        </article>
        <article className="panel cost-metric">
          <p className="eyebrow">Launch Architecture Proxy</p>
          <p className="metric-value">{formatMoney(artifact.cost_model.launch_architecture_cost_proxy_musd)}</p>
          <p className="help-text">not launch pricing</p>
        </article>
      </section>

      <section className="panel cost-controls" aria-label="Architecture row controls">
        <label>
          <span>Target</span>
          <select value={targetId} onChange={(event) => setTargetId(event.currentTarget.value)}>
            {targetOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Velocity</span>
          <select value={velocityId} onChange={(event) => setVelocityId(event.currentTarget.value)}>
            {velocityOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="cost-detail-grid">
        <article className="cost-detail">
          <p className="eyebrow">Selected Scenario</p>
          <h3>{selectedRow.target_label}</h3>
          <dl>
            <div>
              <dt>Flight time</dt>
              <dd>{formatYears(selectedRow.flight_years)}</dd>
            </div>
            <div>
              <dt>Velocity</dt>
              <dd>{selectedRow.velocity_label}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{selectedRow.architecture_feasibility_status}</dd>
            </div>
          </dl>
        </article>

        <article className="cost-detail">
          <p className="eyebrow">Energy Proxy</p>
          <h3>{formatNumber(selectedRow.capsule_kinetic_energy_j)} J</h3>
          <dl>
            <div>
              <dt>vs 23.17 km/s</dt>
              <dd>{formatNumber(selectedRow.relative_to_23_17_km_s)}x</dd>
            </div>
            <div>
              <dt>Cost pressure</dt>
              <dd>{formatNumber(selectedRow.cost_proxy_score)}</dd>
            </div>
            <div>
              <dt>Procurement</dt>
              <dd>{selectedRow.procurement_status}</dd>
            </div>
          </dl>
        </article>

        <article className="cost-detail">
          <p className="eyebrow">Optimization Axis</p>
          <h3>{artifact.optimization_cost_axis.axis_id}</h3>
          <dl>
            <div>
              <dt>Status</dt>
              <dd>{artifact.optimization_cost_axis.status}</dd>
            </div>
            <div>
              <dt>Top candidate cost</dt>
              <dd>{formatNumber(artifact.optimization_cost_axis.top_candidate_cost_proxy)}</dd>
            </div>
            <div>
              <dt>Calibrated model</dt>
              <dd>{String(artifact.optimization_cost_axis.calibrated_cost_model_available)}</dd>
            </div>
          </dl>
        </article>
      </section>

      <section className="cost-gap-section">
        <article>
          <p className="eyebrow">Procurement Gates</p>
          <ul className="cost-list">
            {artifact.procurement_gates.map((gate) => (
              <li key={gate.id}>
                <span>{gate.id}</span>
                <code>{gate.status}</code>
              </li>
            ))}
          </ul>
        </article>
        <article>
          <p className="eyebrow">Blocked Claims</p>
          <ul className="cost-list">
            {artifact.blocked_claims.map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
