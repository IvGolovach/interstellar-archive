import { PUBLIC_DATASET_PATHS } from "../../lib/artifact_public_contracts";
import type { ExternalValidationReviewPackArtifact } from "../../lib/parameter_drilldown_loader";
import "./ExternalReviewPackPanel.css";

interface ExternalReviewPackPanelProps {
  artifact: ExternalValidationReviewPackArtifact;
}

function yesNo(value: boolean): string {
  return value ? "yes" : "no";
}

export function ExternalReviewPackPanel({ artifact }: ExternalReviewPackPanelProps): JSX.Element {
  const rollup = artifact.rollup;
  const firstCases = artifact.review_cases.slice(0, 4);

  return (
    <main className="external-review-shell">
      <section className="external-review-hero">
        <div>
          <p className="eyebrow">Roadmap 14</p>
          <h2>External Validation Review Pack</h2>
          <p className="help-text">
            This route renders the committed review-pack artifact for independent reviewers. It prepares review
            cases, required external deliverables, and forbidden claims without claiming that validation is complete.
          </p>
        </div>
        <a className="ghost-button" href={PUBLIC_DATASET_PATHS.externalValidationReviewPack}>
          Open review artifact JSON
        </a>
      </section>

      <section className="external-review-status panel" aria-label="External review status">
        <div>
          <p className="eyebrow">Status</p>
          <p>{artifact.review_pack_status}</p>
        </div>
        <div>
          <p className="eyebrow">Review Cases</p>
          <p>{artifact.review_case_count}</p>
        </div>
        <div>
          <p className="eyebrow">External Required</p>
          <p>{yesNo(rollup.all_cases_require_external_review)}</p>
        </div>
      </section>

      <section className="external-review-metric-grid" aria-label="External validation claim blockers">
        <article className="panel external-review-metric">
          <p className="eyebrow">Third-party review completed</p>
          <p className="metric-value">{yesNo(rollup.third_party_review_completed)}</p>
          <p className="help-text">third-party validated remains a blocked claim</p>
        </article>
        <article className="panel external-review-metric">
          <p className="eyebrow">Independent reproduction completed</p>
          <p className="metric-value">{yesNo(rollup.independent_reproduction_completed)}</p>
          <p className="help-text">independent reproduction completed stays open</p>
        </article>
        <article className="panel external-review-metric">
          <p className="eyebrow">External validation claimed</p>
          <p className="metric-value">{yesNo(rollup.external_validation_claimed)}</p>
          <p className="help-text">non-certifying repository surface</p>
        </article>
      </section>

      <section className="external-review-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Review Cases</p>
            <h3>Independent review queue</h3>
          </div>
          <code>{artifact.schema_version}</code>
        </div>
        <div className="external-review-case-grid">
          {firstCases.map((item) => (
            <article key={item.id} className="external-review-case">
              <div className="external-review-case-header">
                <code>{item.id}</code>
                <span>{item.status}</span>
              </div>
              <h4>{item.title}</h4>
              <p>{item.review_questions[0]}</p>
              <dl>
                <div>
                  <dt>Source inputs</dt>
                  <dd>{item.source_inputs.length}</dd>
                </div>
                <div>
                  <dt>Deliverables</dt>
                  <dd>{item.external_deliverable_ids.length}</dd>
                </div>
                <div>
                  <dt>Independent result</dt>
                  <dd>{yesNo(item.independent_result_available)}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className="external-review-two-column">
        <article>
          <p className="eyebrow">Required Deliverables</p>
          <ul className="external-review-list">
            {artifact.required_external_deliverables.map((item) => (
              <li key={item.id}>
                <span>{item.id}</span>
                <code>{item.status}</code>
              </li>
            ))}
          </ul>
        </article>
        <article>
          <p className="eyebrow">Blocked Claims</p>
          <ul className="external-review-list">
            {artifact.blocked_claims.slice(0, 8).map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
