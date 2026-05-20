import type { ParameterManifestEntry } from "../../lib/parameter_drilldown_loader";
import {
  formatParameterBounds,
  formatParameterDefault,
} from "./parameter_drilldown_helpers";

interface ParameterDefinitionSectionProps {
  parameter: ParameterManifestEntry;
}

export function ParameterDefinitionSection(
  props: ParameterDefinitionSectionProps,
): JSX.Element {
  const { parameter } = props;

  return (
    <article className="drilldown-section">
      <h3>1. Definition (contract view)</h3>
      <dl className="definition-grid">
        <dt>parameter_id</dt>
        <dd className="mono-cell">{parameter.parameter_id}</dd>
        <dt>domain</dt>
        <dd>{parameter.domain}</dd>
        <dt>trust_grade</dt>
        <dd>{parameter.trust_grade}</dd>
        <dt>units</dt>
        <dd>{parameter.units}</dd>
        <dt>bounds</dt>
        <dd className="mono-cell">{formatParameterBounds(parameter)}</dd>
        <dt>default_value</dt>
        <dd className="mono-cell">{formatParameterDefault(parameter.default_value)}</dd>
        <dt>affects_core_probability</dt>
        <dd>{parameter.affects_core_probability ? "true" : "false"}</dd>
        <dt>evidence_source_ids</dt>
        <dd className="mono-cell">{parameter.evidence_source_ids.join(", ") || "N/A"}</dd>
      </dl>
    </article>
  );
}
