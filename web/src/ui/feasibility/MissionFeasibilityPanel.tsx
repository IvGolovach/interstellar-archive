import { useMemo, useState } from "react";

import type { MissionFeasibilityRow, MissionFeasibilityScreenArtifact } from "../../lib/parameter_drilldown_loader";
import "./MissionFeasibilityPanel.css";

interface MissionFeasibilityPanelProps {
  artifact: MissionFeasibilityScreenArtifact;
}

interface Option {
  id: string;
  label: string;
}

function uniqueOptions(rows: MissionFeasibilityRow[], idKey: "target_id" | "velocity_id", labelKey: "target_label" | "velocity_label"): Option[] {
  const seen = new Map<string, string>();
  for (const row of rows) {
    if (!seen.has(row[idKey])) {
      seen.set(row[idKey], row[labelKey]);
    }
  }
  return Array.from(seen, ([id, label]) => ({ id, label }));
}

function formatYears(years: number): string {
  if (years >= 1_000_000) {
    return `${(years / 1_000_000).toLocaleString("en-US", { maximumFractionDigits: 2 })} Myr`;
  }
  return `${Math.round(years).toLocaleString("en-US")} yr`;
}

function formatNumber(value: unknown, digits = 3): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("en-US", { maximumSignificantDigits: digits })
    : "N/A";
}

function pickDefaultRow(artifact: MissionFeasibilityScreenArtifact): MissionFeasibilityRow {
  return (
    artifact.scenario_rows.find((row) => row.id === artifact.default_scenario_id) ??
    artifact.scenario_rows[0]
  );
}

export function MissionFeasibilityPanel({ artifact }: MissionFeasibilityPanelProps): JSX.Element {
  const defaultRow = pickDefaultRow(artifact);
  const [targetId, setTargetId] = useState(defaultRow.target_id);
  const [velocityId, setVelocityId] = useState(defaultRow.velocity_id);
  const targetOptions = useMemo(
    () => uniqueOptions(artifact.scenario_rows, "target_id", "target_label"),
    [artifact.scenario_rows],
  );
  const velocityOptions = useMemo(
    () => uniqueOptions(artifact.scenario_rows, "velocity_id", "velocity_label"),
    [artifact.scenario_rows],
  );
  const selectedRow =
    artifact.scenario_rows.find((row) => row.target_id === targetId && row.velocity_id === velocityId) ??
    defaultRow;
  const dust = selectedRow.dust_screen as Record<string, unknown>;
  const cost = selectedRow.cost_energy_proxy as Record<string, unknown>;
  const blackHole = selectedRow.black_hole_screen as Record<string, unknown>;
  const risk = selectedRow.capsule_risk_budget_link;

  return (
    <main className="feasibility-shell">
      <section className="feasibility-hero">
        <div>
          <p className="eyebrow">Mission Feasibility Screen</p>
          <h2>{selectedRow.target_label}</h2>
          <p className="help-text">{selectedRow.target_detail}</p>
        </div>
        <code>{artifact.schema_version}</code>
      </section>

      <section className="panel feasibility-controls" aria-label="Mission feasibility controls">
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

      <section className="feasibility-metric-grid" aria-label="Selected feasibility metrics">
        <article className="panel feasibility-metric">
          <p className="eyebrow">Flight Time</p>
          <p className="metric-value">{formatYears(selectedRow.flight_years)}</p>
          <p className="help-text">{selectedRow.velocity_label}</p>
        </article>
        <article className="panel feasibility-metric">
          <p className="eyebrow">Dust Sweep</p>
          <p className="metric-value">{formatNumber(dust.swept_scaled_dust_mass_kg, 4)} kg</p>
          <p className="help-text">{formatNumber(dust.bulk_kinetic_energy_j, 4)} J bulk energy</p>
        </article>
        <article className="panel feasibility-metric">
          <p className="eyebrow">Capsule Risk Link</p>
          <p className="metric-value">{formatNumber(risk.survival_p50, 4)}</p>
          <p className="help-text">nominal p50, non-certifying</p>
        </article>
      </section>

      <section className="feasibility-detail-grid">
        <article className="feasibility-detail">
          <p className="eyebrow">Trajectory</p>
          <h3>{formatNumber(selectedRow.distance_ly, 5)} ly</h3>
          <dl>
            <div>
              <dt>Velocity</dt>
              <dd>{selectedRow.velocity_km_s} km/s</dd>
            </div>
            <div>
              <dt>Fraction of c</dt>
              <dd>{formatNumber(selectedRow.velocity_fraction_c, 4)}</dd>
            </div>
            <div>
              <dt>Class</dt>
              <dd>{selectedRow.time_horizon_class}</dd>
            </div>
          </dl>
        </article>

        <article className="feasibility-detail">
          <p className="eyebrow">Black-Hole Screen</p>
          <h3>{blackHole.applies ? "Horizon screen active" : "Not a black-hole target"}</h3>
          <dl>
            <div>
              <dt>Crossing</dt>
              <dd>{blackHole.crossing_condition_met === true ? "yes" : "n/a"}</dd>
            </div>
            <div>
              <dt>Periapsis / rs</dt>
              <dd>{formatNumber(blackHole.periapsis_to_schwarzschild_ratio, 5)}</dd>
            </div>
          </dl>
        </article>

        <article className="feasibility-detail">
          <p className="eyebrow">Energy Proxy</p>
          <h3>{formatNumber(cost.capsule_kinetic_energy_j, 4)} J</h3>
          <dl>
            <div>
              <dt>vs 23.17 km/s</dt>
              <dd>{formatNumber(cost.relative_to_23_17_km_s, 4)}x</dd>
            </div>
            <div>
              <dt>Procurement</dt>
              <dd>{String(cost.procurement_status ?? "external_required")}</dd>
            </div>
          </dl>
        </article>
      </section>

      <section className="feasibility-gap-section">
        <article>
          <p className="eyebrow">External Evidence Still Required</p>
          <ul className="feasibility-gap-list">
            {selectedRow.external_evidence_gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </article>
        <article>
          <p className="eyebrow">Blocked Claims</p>
          <ul className="feasibility-gap-list">
            {selectedRow.blocked_claims.map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
