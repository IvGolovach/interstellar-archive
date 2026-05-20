import type {
  ParameterEvidenceEntry,
  ParameterManifestEntry,
  PSuccessDefensibility,
} from "../../lib/parameter_drilldown_loader";

interface ParameterScientificBasisSectionProps {
  parameter: ParameterManifestEntry;
  evidenceEntry: ParameterEvidenceEntry | null;
  pSuccessDefensibility: PSuccessDefensibility;
}

export function ParameterScientificBasisSection(
  props: ParameterScientificBasisSectionProps,
): JSX.Element {
  const { parameter, evidenceEntry, pSuccessDefensibility } = props;

  return (
    <article className="drilldown-section">
      <h3>Basis &amp; Provenance</h3>
      {evidenceEntry ? (
        <>
          <dl className="definition-grid">
            <dt>Origin type</dt>
            <dd>{evidenceEntry.value_origin_type}</dd>
            <dt>Trust grade</dt>
            <dd>
              {evidenceEntry.trust_grade}
              {evidenceEntry.trust_grade === "D" ? " (speculative)" : ""}
            </dd>
            <dt>Uncertainty model</dt>
            <dd>
              {evidenceEntry.uncertainty_type}
              {evidenceEntry.uncertainty_type === "distribution"
                ? ` (${String(evidenceEntry.uncertainty_spec.distribution ?? "unspecified")})`
                : ""}
            </dd>
            <dt>Influence path</dt>
            <dd className="mono-cell">{evidenceEntry.influence_path.join(", ") || "N/A"}</dd>
            <dt>Defensibility status</dt>
            <dd>{evidenceEntry.defensibility_status}</dd>
          </dl>

          <h4>Derivation chain</h4>
          {evidenceEntry.derivation_chain.length > 0 ? (
            <ul className="compact-list mono-cell">
              {evidenceEntry.derivation_chain.map((item) => (
                <li key={`${item.type}:${item.ref}`}>
                  {item.type}: {item.ref}
                </li>
              ))}
            </ul>
          ) : (
            <p>N/A</p>
          )}

          <h4>Source links</h4>
          {evidenceEntry.evidence_sources.length > 0 ? (
            <ul className="compact-list">
              {evidenceEntry.evidence_sources.map((source) => (
                <li key={source.source_id}>
                  <span className="mono-cell">{source.source_id}</span>{" "}
                  {source.url ? (
                    <a href={source.url} target="_blank" rel="noreferrer">
                      citation
                    </a>
                  ) : (
                    <span>citation (no URL)</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p>N/A</p>
          )}

          {parameter.affects_core_probability ? (
            <>
              <h4>p_success defensibility</h4>
              <p className="mono-cell">{pSuccessDefensibility.formula}</p>
              <p className="help-text">
                uncertainty propagation: {pSuccessDefensibility.uncertainty_propagation}
              </p>
              <ul className="compact-list mono-cell">
                {pSuccessDefensibility.inputs.map((metric) => {
                  const origin = pSuccessDefensibility.input_origins[metric];
                  return (
                    <li key={metric}>
                      {metric}: origin={origin?.origin_type ?? "N/A"}; sources=
                      {(origin?.source_ids ?? []).join(", ") || "N/A"}
                    </li>
                  );
                })}
              </ul>
            </>
          ) : null}

          {evidenceEntry.failure_surface.length > 0 ? (
            <>
              <h4>Failure surface attribution</h4>
              <ul className="compact-list mono-cell">
                {evidenceEntry.failure_surface.map((item) => (
                  <li key={`${item.failure_mode}:${item.dominant_driver_method}`}>
                    {item.failure_mode} | method={item.dominant_driver_method} | confidence=
                    {item.confidence}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </>
      ) : (
        <p className="error-text">
          Provenance summary unavailable because the evidence entry is missing.
        </p>
      )}
    </article>
  );
}
