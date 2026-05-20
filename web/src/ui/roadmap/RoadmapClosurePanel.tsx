import { PUBLIC_DATASET_PATHS } from "../../lib/artifact_public_contracts";
import type { RoadmapClosureArtifact } from "../../lib/parameter_drilldown_loader";
import "./RoadmapClosurePanel.css";

interface RoadmapClosurePanelProps {
  artifact: RoadmapClosureArtifact;
}

function formatMetric(value: number | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("en-US") : "N/A";
}

function formatStatus(status: string): string {
  return status === "repo_native_closure_implemented_external_evidence_open"
    ? "External evidence open"
    : status;
}

export function RoadmapClosurePanel({ artifact }: RoadmapClosurePanelProps): JSX.Element {
  const metrics = artifact.closure_metrics;
  const topGaps = artifact.roadmap_items
    .flatMap((item) => item.external_evidence_gaps.map((gap) => ({ id: item.id, title: item.title, gap })))
    .slice(0, 8);

  return (
    <main className="roadmap-closure-shell">
      <section className="roadmap-closure-hero">
        <div>
          <p className="eyebrow">Full V2 Roadmap Closure</p>
          <h2>15 repo-native closures, external evidence still open</h2>
          <p className="help-text">
            This surface renders the committed roadmap closure artifact. It tracks implementation contracts,
            validators, false-claim blocks, and qualification gaps without turning them into certification.
          </p>
        </div>
        <a className="ghost-button" href={PUBLIC_DATASET_PATHS.roadmapClosure}>
          Open roadmap artifact JSON
        </a>
      </section>

      <section className="roadmap-metric-grid" aria-label="Roadmap closure metrics">
        <article className="panel roadmap-metric">
          <p className="eyebrow">Closure rows</p>
          <p className="metric-value">{formatMetric(metrics.repo_native_closure_count)}</p>
          <p className="help-text">All 15 items have a repository contract and validator.</p>
        </article>
        <article className="panel roadmap-metric">
          <p className="eyebrow">Evidence gaps</p>
          <p className="metric-value">{formatMetric(metrics.external_evidence_gap_count)}</p>
          <p className="help-text">External physics, qualification, or review work remains visible.</p>
        </article>
        <article className="panel roadmap-metric">
          <p className="eyebrow">Notices</p>
          <p className="metric-value">{formatMetric(metrics.non_certification_notice_count)}</p>
          <p className="help-text">Every row preserves the non-certification boundary.</p>
        </article>
      </section>

      <section className="roadmap-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Closure Ledger</p>
            <h3>Roadmap items</h3>
          </div>
          <code>{artifact.schema_version}</code>
        </div>
        <div className="roadmap-item-grid">
          {artifact.roadmap_items.map((item) => (
            <article key={item.id} className="roadmap-item">
              <div className="roadmap-item-header">
                <code>{item.id}</code>
                <span title={item.status}>{formatStatus(item.status)}</span>
              </div>
              <h4>{item.title}</h4>
              <p>{item.summary}</p>
              <dl>
                <div>
                  <dt>Mode</dt>
                  <dd>{item.implementation_mode}</dd>
                </div>
                <div>
                  <dt>Validators</dt>
                  <dd>{item.validators.length}</dd>
                </div>
                <div>
                  <dt>Evidence gaps</dt>
                  <dd>{item.external_evidence_gaps.length}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className="roadmap-section">
        <p className="eyebrow">External Evidence Still Open</p>
        <h3>Top gaps</h3>
        <ul className="roadmap-gap-list">
          {topGaps.map((entry) => (
            <li key={`${entry.id}-${entry.gap}`}>
              <span>{entry.title}</span>
              <p>{entry.gap}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="roadmap-section">
        <p className="eyebrow">Public Boundary</p>
        <h3>False claims blocked</h3>
        <div className="claim-chip-row">
          {(artifact.public_narrative.forbidden_claims ?? []).map((claim) => (
            <span key={claim} className="claim-chip">
              {claim}
            </span>
          ))}
        </div>
      </section>
    </main>
  );
}
