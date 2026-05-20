import { PUBLIC_DATASET_PATHS } from "../../lib/artifact_public_contracts";
import type {
  ObjectiveContract,
  ObjectiveScoreBaseline,
} from "../../lib/parameter_drilldown_loader";

interface ObjectiveContractPanelProps {
  contract: ObjectiveContract;
  baselineScore: ObjectiveScoreBaseline;
}

function formatVector(values: number[]): string {
  if (values.length === 0) {
    return "[]";
  }
  return `[${values.map((item) => String(item)).join(", ")}]`;
}

function formatMaybeNumber(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "N/A";
  }
  return value.toFixed(6);
}

export function ObjectiveContractPanel(props: ObjectiveContractPanelProps): JSX.Element {
  const { contract, baselineScore } = props;
  const realistic = baselineScore.scores.realistic;
  const speculative = baselineScore.scores.speculative;

  return (
    <article className="drilldown-section">
      <h3>Objective Contract / Baseline Score</h3>
      <p className="help-text">
        Sources: <code>{PUBLIC_DATASET_PATHS.objectiveContract}</code> and <code>{PUBLIC_DATASET_PATHS.objectiveScoreBaseline}</code>
      </p>

      <h4>Objective Contract</h4>
      <dl className="definition-grid">
        <dt>schema_version</dt>
        <dd className="mono-cell">{contract.schema_version}</dd>
        <dt>modes</dt>
        <dd className="mono-cell">{contract.modes.join(", ")}</dd>
        <dt>realistic primary metric</dt>
        <dd className="mono-cell">{contract.objective_sets.realistic.primary.metric}</dd>
        <dt>realistic aggregation</dt>
        <dd className="mono-cell">{contract.objective_sets.realistic.aggregation.type}</dd>
        <dt>realistic dimensions</dt>
        <dd className="mono-cell">{(contract.objective_sets.realistic.aggregation.dimensions ?? []).join(" x ")}</dd>
        <dt>speculative primary metric</dt>
        <dd className="mono-cell">{contract.objective_sets.speculative.primary.metric}</dd>
      </dl>

      <h4>Constraint status (realistic)</h4>
      <ul className="compact-list mono-cell">
        {baselineScore.constraints_status.realistic.map((item) => (
          <li key={item.id}>
            {item.id}: {item.status}
          </li>
        ))}
      </ul>

      <h4>Baseline score</h4>
      <div className="objective-grid">
        <section className="objective-card">
          <h5>Realistic</h5>
          <ul className="compact-list mono-cell">
            <li>p_success: {realistic.p_success}</li>
            <li>objective_vector: {formatVector(realistic.objective_vector)}</li>
            <li>rank_key: {realistic.rank_key}</li>
            <li>risk_envelope: {formatMaybeNumber(realistic.risk_envelope)}</li>
            <li>
              risk_meta: {realistic.risk_meta?.method ?? "N/A"} q=
              {formatMaybeNumber(realistic.risk_meta?.quantile)}
            </li>
          </ul>
        </section>
        <section className="objective-card">
          <h5>Speculative</h5>
          <ul className="compact-list mono-cell">
            <li>p_success: {speculative.p_success}</li>
            <li>objective_vector: {formatVector(speculative.objective_vector)}</li>
            <li>rank_key: {speculative.rank_key}</li>
          </ul>
        </section>
      </div>
    </article>
  );
}
