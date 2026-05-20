import type { ParameterManifestEntry } from "../../lib/parameter_drilldown_loader";

interface ParameterDerivedSectionsProps {
  parameter: ParameterManifestEntry;
}

export function ParameterDerivedSections(
  props: ParameterDerivedSectionsProps,
): JSX.Element {
  const { parameter } = props;

  return (
    <>
      <article className="drilldown-section">
        <h3>4. Sensitivity / Impact (v1 minimal)</h3>
        {parameter.sensitivity_summary ? (
          <p>{parameter.sensitivity_summary}</p>
        ) : (
          <p>N/A (not included in v1 artifacts)</p>
        )}
      </article>

      <article className="drilldown-section">
        <h3>5. Constraints & Failures (derived-only)</h3>
        {parameter.failure_taxonomy_refs && parameter.failure_taxonomy_refs.length > 0 ? (
          <ul className="compact-list mono-cell">
            {parameter.failure_taxonomy_refs.map((failureId) => (
              <li key={failureId}>{failureId}</li>
            ))}
          </ul>
        ) : (
          <p>N/A (not included in v1 artifacts)</p>
        )}
      </article>
    </>
  );
}
