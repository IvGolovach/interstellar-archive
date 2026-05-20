import { PUBLIC_DATASET_PATHS } from "../../lib/artifact_public_contracts";
import type {
  EvidenceUpgradeCampaignArtifact,
  EvidenceUpgradeCampaignRow,
} from "../../lib/parameter_drilldown_loader";
import "./EvidenceCampaignPanel.css";

interface EvidenceCampaignPanelProps {
  artifact: EvidenceUpgradeCampaignArtifact;
  selectedCampaignId?: string;
  onSelectCampaign: (campaignId: string) => void;
}

function formatNumber(value: number): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: 3 });
}

function displayId(value: string): string {
  return value.replaceAll("_", " ");
}

function pickRow(artifact: EvidenceUpgradeCampaignArtifact, selectedCampaignId?: string): EvidenceUpgradeCampaignRow {
  return (
    artifact.public_top_priorities.find((row) => row.campaign_id === selectedCampaignId) ??
    artifact.public_top_priorities[0]
  );
}

export function EvidenceCampaignPanel({
  artifact,
  selectedCampaignId,
  onSelectCampaign,
}: EvidenceCampaignPanelProps): JSX.Element {
  const selected = pickRow(artifact, selectedCampaignId);
  const publicDistribution = Object.entries(artifact.public_trust_distribution)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([grade, count]) => `${grade}: ${count}`)
    .join(" / ");

  return (
    <main className="evidence-campaign-shell">
      <section className="evidence-campaign-hero">
        <div>
          <p className="eyebrow">Evidence Upgrade Campaign</p>
          <h2>{displayId(selected.parameter_id)}</h2>
          <p className="help-text">
            This route renders the committed campaign ledger. It ranks review work without promoting
            trust grades or certifying source correctness.
          </p>
        </div>
        <a className="ghost-button" href={PUBLIC_DATASET_PATHS.evidenceUpgradeCampaign}>
          Open artifact JSON
        </a>
      </section>

      <section className="evidence-metric-grid" aria-label="Evidence campaign metrics">
        <article className="panel evidence-metric">
          <p className="eyebrow">All claims</p>
          <p className="metric-value">{artifact.claim_count}</p>
          <p className="help-text">{Object.entries(artifact.trust_distribution).map(([grade, count]) => `${grade}:${count}`).join(" / ")}</p>
        </article>
        <article className="panel evidence-metric">
          <p className="eyebrow">Public campaign</p>
          <p className="metric-value">{artifact.public_campaign_count}</p>
          <p className="help-text">{publicDistribution}</p>
        </article>
        <article className="panel evidence-metric">
          <p className="eyebrow">Internal audit</p>
          <p className="metric-value">{artifact.internal_audit_count}</p>
          <p className="help-text">{artifact.internal_audit_rollup.public_surface_policy}</p>
        </article>
      </section>

      <section className="panel evidence-selector" aria-label="Selected evidence campaign row">
        <label>
          <span>Public priority row</span>
          <select value={selected.campaign_id} onChange={(event) => onSelectCampaign(event.currentTarget.value)}>
            {artifact.public_top_priorities.map((row) => (
              <option key={row.campaign_id} value={row.campaign_id}>
                {row.current_trust_grade} to {row.target_trust_grade}: {row.parameter_id}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="evidence-row-grid">
        <article className="evidence-row-detail">
          <p className="eyebrow">Selected Priority</p>
          <dl>
            <div>
              <dt>Parameter</dt>
              <dd>{selected.parameter_id}</dd>
            </div>
            <div>
              <dt>Trust target</dt>
              <dd>{selected.current_trust_grade} to {selected.target_trust_grade}</dd>
            </div>
            <div>
              <dt>Priority score</dt>
              <dd>{formatNumber(selected.priority_score)}</dd>
            </div>
            <div>
              <dt>Source types</dt>
              <dd>{selected.source_types.join(", ")}</dd>
            </div>
          </dl>
        </article>
        <article className="evidence-row-detail">
          <p className="eyebrow">Upgrade Actions</p>
          <ul>
            {selected.recommended_actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </article>
      </section>

      <section className="evidence-table-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Public Top Priorities</p>
            <h3>{artifact.public_top_priorities.length} browser-safe rows</h3>
          </div>
          <code>{artifact.schema_version}</code>
        </div>
        <div className="evidence-priority-list">
          {artifact.public_top_priorities.map((row) => (
            <button
              type="button"
              key={row.campaign_id}
              className={`evidence-priority-row${row.campaign_id === selected.campaign_id ? " active" : ""}`}
              onClick={() => onSelectCampaign(row.campaign_id)}
            >
              <span>{row.parameter_id}</span>
              <strong>{row.current_trust_grade} to {row.target_trust_grade}</strong>
              <small>{formatNumber(row.priority_score)}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="evidence-list-section">
        <article>
          <p className="eyebrow">External Evidence Still Required</p>
          <ul>
            {artifact.external_evidence_gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </article>
        <article>
          <p className="eyebrow">Blocked Claims</p>
          <ul>
            {artifact.blocked_claims.map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
