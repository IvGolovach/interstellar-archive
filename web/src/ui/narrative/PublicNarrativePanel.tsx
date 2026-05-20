import { PUBLIC_DATASET_PATHS } from "../../lib/artifact_public_contracts";
import type { PublicNarrativeHardeningArtifact } from "../../lib/parameter_drilldown_loader";
import "./PublicNarrativePanel.css";

interface PublicNarrativePanelProps {
  artifact: PublicNarrativeHardeningArtifact;
}

function yesNo(value: boolean): string {
  return value ? "yes" : "no";
}

export function PublicNarrativePanel({ artifact }: PublicNarrativePanelProps): JSX.Element {
  const rollup = artifact.rollup;
  const boundary = artifact.browser_boundary;
  const primaryRules = artifact.claim_rules.slice(0, 6);
  const firstSurfaces = artifact.public_surfaces.slice(0, 6);

  return (
    <main className="public-narrative-shell">
      <section className="public-narrative-hero">
        <div>
          <p className="eyebrow">Roadmap 15</p>
          <h2>Public Narrative Hardening</h2>
          <p className="help-text">
            This route renders the committed public-claim boundary artifact. It shows blocked wording,
            required qualifiers, and open evidence gaps for the browser surface without recomputing claims.
          </p>
        </div>
        <a className="ghost-button" href={PUBLIC_DATASET_PATHS.publicNarrativeHardening}>
          Open narrative artifact JSON
        </a>
      </section>

      <section className="public-narrative-status panel" aria-label="Public narrative artifact status">
        <div>
          <p className="eyebrow">Status</p>
          <p>{artifact.review_status}</p>
        </div>
        <div>
          <p className="eyebrow">Claim Rules</p>
          <p>{artifact.claim_rule_count}</p>
        </div>
        <div>
          <p className="eyebrow">Public Surfaces</p>
          <p>{artifact.public_surface_count}</p>
        </div>
      </section>

      <section className="public-narrative-metric-grid" aria-label="Public claim boundaries">
        <article className="panel public-narrative-metric">
          <p className="eyebrow">unsafe public overclaim</p>
          <p className="metric-value">{rollup.unsafe_public_overclaim_count}</p>
          <p className="help-text">public release fails if this rises above zero</p>
        </article>
        <article className="panel public-narrative-metric">
          <p className="eyebrow">External wording audit</p>
          <p className="metric-value">{yesNo(rollup.external_wording_audit_completed)}</p>
          <p className="help-text">external evidence gaps remain visible</p>
        </article>
        <article className="panel public-narrative-metric">
          <p className="eyebrow">Browser artifact-only</p>
          <p className="metric-value">{yesNo(boundary.artifact_only_rendering)}</p>
          <p className="help-text">client-side recomputation is disabled by contract</p>
        </article>
      </section>

      <section className="public-narrative-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Claim Rules</p>
            <h3>Blocking public wording boundaries</h3>
          </div>
          <code>{artifact.schema_version}</code>
        </div>
        <div className="public-narrative-rule-grid">
          {primaryRules.map((rule) => (
            <article key={rule.id} className="public-narrative-rule">
              <div className="public-narrative-rule-header">
                <code>{rule.id}</code>
                <span>{rule.claim_domain}</span>
              </div>
              <p>{rule.rationale}</p>
              <dl>
                <div>
                  <dt>Forbidden terms</dt>
                  <dd>{rule.forbidden_terms.length}</dd>
                </div>
                <div>
                  <dt>Required qualifiers</dt>
                  <dd>{rule.required_qualifiers.join(", ")}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className="public-narrative-two-column">
        <article>
          <p className="eyebrow">Blocked Claims</p>
          <ul className="public-narrative-list">
            {artifact.forbidden_public_claims.slice(0, 10).map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </article>
        <article>
          <p className="eyebrow">Required Concepts</p>
          <ul className="public-narrative-list">
            {artifact.required_public_concepts.map((concept) => (
              <li key={concept}>{concept}</li>
            ))}
          </ul>
        </article>
      </section>

      <section className="public-narrative-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Surfaces</p>
            <h3>Public route coverage</h3>
          </div>
          <code>{PUBLIC_DATASET_PATHS.publicNarrativeHardening}</code>
        </div>
        <div className="public-narrative-surface-grid">
          {firstSurfaces.map((surface) => (
            <article key={surface.surface_id} className="public-narrative-surface">
              <code>{surface.source_ref}</code>
              <p>{surface.surface_id}</p>
              <span>{surface.covered_rule_ids.length} rules</span>
            </article>
          ))}
        </div>
      </section>

      <section className="public-narrative-two-column">
        <article>
          <p className="eyebrow">Allowed Phrasing</p>
          <ul className="public-narrative-list">
            {artifact.allowed_phrasing.slice(0, 8).map((phrase) => (
              <li key={phrase}>{phrase}</li>
            ))}
          </ul>
        </article>
        <article>
          <p className="eyebrow">External Gaps</p>
          <ul className="public-narrative-list">
            {artifact.external_evidence_gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
