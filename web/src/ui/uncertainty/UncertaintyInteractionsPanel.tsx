import type {
  UncertaintyInteractionsArtifact,
  UncertaintyPairInteraction,
} from "../../lib/parameter_drilldown_loader";
import "./UncertaintyInteractionsPanel.css";

interface UncertaintyInteractionsPanelProps {
  artifact: UncertaintyInteractionsArtifact;
  selectedPairId?: string;
  onSelectPair: (pairId: string) => void;
}

function formatProbability(value: number): string {
  return value.toLocaleString("en-US", { maximumSignificantDigits: 5 });
}

function formatSigned(value: number): string {
  return value.toLocaleString("en-US", {
    maximumSignificantDigits: 4,
    signDisplay: value === 0 ? "never" : "always",
  });
}

function displayId(value: string): string {
  return value.replaceAll("_", " ");
}

function pickPair(artifact: UncertaintyInteractionsArtifact, selectedPairId?: string): UncertaintyPairInteraction {
  return (
    artifact.pair_interactions.find((row) => row.pair_id === selectedPairId) ??
    artifact.pair_interactions.find((row) => row.pair_id === artifact.rollup.dominant_pair_id) ??
    artifact.pair_interactions[0]
  );
}

export function UncertaintyInteractionsPanel({
  artifact,
  selectedPairId,
  onSelectPair,
}: UncertaintyInteractionsPanelProps): JSX.Element {
  const selected = pickPair(artifact, selectedPairId);
  const [leftId, rightId] = selected.parameter_ids;

  return (
    <main className="uncertainty-shell">
      <section className="uncertainty-hero">
        <div>
          <p className="eyebrow">Uncertainty Interactions</p>
          <h2>{displayId(leftId)} x {displayId(rightId)}</h2>
          <p className="help-text">{selected.pair_id}</p>
        </div>
        <code>{artifact.schema_version}</code>
      </section>

      <section className="panel uncertainty-selector" aria-label="Selected uncertainty interaction">
        <label>
          <span>Interaction Edge</span>
          <select value={selected.pair_id} onChange={(event) => onSelectPair(event.currentTarget.value)}>
            {artifact.pair_interactions.map((row) => (
              <option key={row.pair_id} value={row.pair_id}>
                {row.parameter_ids.map(displayId).join(" / ")}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="uncertainty-metric-grid" aria-label="Uncertainty interaction metrics">
        <article className="panel uncertainty-metric">
          <p className="eyebrow">Baseline p_success</p>
          <p className="metric-value">{formatProbability(artifact.baseline.p_success)}</p>
          <p className="help-text">{artifact.mode}</p>
        </article>
        <article className="panel uncertainty-metric">
          <p className="eyebrow">Max Residual</p>
          <p className="metric-value">{formatSigned(selected.interaction_residual.max_abs)}</p>
          <p className="help-text">{selected.interaction_residual.classification}</p>
        </article>
        <article className="panel uncertainty-metric">
          <p className="eyebrow">Correlation</p>
          <p className="metric-value small">open</p>
          <p className="help-text">{selected.correlation.status}</p>
        </article>
      </section>

      <section className="uncertainty-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Pairwise Stress Screen</p>
            <h3>{artifact.method.name as string}</h3>
          </div>
          <code>{artifact.rollup.pairs_requiring_external_correlation_evidence} open pairs</code>
        </div>
        <div className="uncertainty-stress-grid">
          {Object.entries(selected.stress_p_success).map(([label, value]) => (
            <article key={label} className="stress-cell">
              <span>{label.replaceAll("_", " / ")}</span>
              <strong>{formatProbability(value)}</strong>
            </article>
          ))}
        </div>
      </section>

      <section className="uncertainty-detail-grid">
        <article className="uncertainty-detail">
          <p className="eyebrow">Main Effects</p>
          <div className="effect-list">
            {artifact.main_effects.map((effect) => (
              <div key={effect.entry_id}>
                <span>{displayId(effect.parameter_id)}</span>
                <strong>{formatSigned(effect.max_abs_effect)}</strong>
              </div>
            ))}
          </div>
        </article>
        <article className="uncertainty-detail">
          <p className="eyebrow">Residual Components</p>
          <div className="effect-list">
            {Object.entries(selected.interaction_residual)
              .filter(([key]) => key !== "classification")
              .map(([label, value]) => (
                <div key={label}>
                  <span>{label.replaceAll("_", " / ")}</span>
                  <strong>{typeof value === "number" ? formatSigned(value) : String(value)}</strong>
                </div>
              ))}
          </div>
        </article>
      </section>

      <section className="uncertainty-list-section">
        <article>
          <p className="eyebrow">External Evidence Still Required</p>
          <ul className="uncertainty-list">
            {artifact.external_evidence_gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </article>
        <article>
          <p className="eyebrow">Blocked Claims</p>
          <ul className="uncertainty-list">
            {artifact.blocked_claims.map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
