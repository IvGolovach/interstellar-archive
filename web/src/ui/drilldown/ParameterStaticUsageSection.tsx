import type {
  ParameterManifestEntry,
  ParameterStaticUsageEntry,
} from "../../lib/parameter_drilldown_loader";

interface ParameterStaticUsageSectionProps {
  parameter: ParameterManifestEntry;
  staticUsageEntry: ParameterStaticUsageEntry | null;
}

export function ParameterStaticUsageSection(
  props: ParameterStaticUsageSectionProps,
): JSX.Element {
  const { parameter, staticUsageEntry } = props;

  return (
    <article className="drilldown-section">
      <h3>2. Static Usage (contract)</h3>
      <p className="help-text">contract-backed: {staticUsageEntry ? "true" : "false"}</p>
      {staticUsageEntry ? (
        <>
          <h4>modules</h4>
          <ul className="compact-list mono-cell">
            {staticUsageEntry.modules.map((moduleId) => (
              <li key={moduleId}>{moduleId}</li>
            ))}
          </ul>
          <h4>paths_to_metrics</h4>
          <ul className="compact-list mono-cell">
            {staticUsageEntry.paths_to_metrics.map((metricPath) => (
              <li key={metricPath}>{metricPath}</li>
            ))}
          </ul>
        </>
      ) : (
        <p className="error-text">
          Static usage entry missing for {parameter.parameter_id}.
        </p>
      )}
    </article>
  );
}
