import type {
  ParameterEvidenceEntry,
  ParameterManifestEntry,
} from "../../lib/parameter_drilldown_loader";

interface ParameterEvidenceSectionProps {
  parameter: ParameterManifestEntry;
  evidenceEntry: ParameterEvidenceEntry | null;
}

export function ParameterEvidenceSection(
  props: ParameterEvidenceSectionProps,
): JSX.Element {
  const { parameter, evidenceEntry } = props;

  return (
    <article className="drilldown-section">
      <h3>3. Evidence &amp; Assumption Chain</h3>
      <p className="help-text">
        completeness indicator: {parameter.evidence_status.status}
        {parameter.evidence_status.reason ? ` (${parameter.evidence_status.reason})` : ""}
      </p>
      {evidenceEntry ? (
        <>
          <p>{evidenceEntry.justification || "N/A"}</p>
          <p className="help-text mono-cell">
            last_reviewed_commit: {evidenceEntry.last_reviewed_commit || "N/A"}
          </p>
          <h4>Sources</h4>
          <ul className="compact-list">
            {evidenceEntry.evidence_sources.map((source) => (
              <li key={source.source_id}>
                <p className="mono-cell">{source.source_id}</p>
                <p>{source.citation}</p>
                <p className="help-text">type={source.type}; scope={source.claim_scope}</p>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="error-text">Evidence entry missing for this parameter.</p>
      )}
    </article>
  );
}
