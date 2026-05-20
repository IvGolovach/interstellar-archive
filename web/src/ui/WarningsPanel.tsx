interface WarningsPanelProps {
  warnings: string[];
  nonPhysicalActive: boolean;
}

const NON_PHYSICAL_WARNING = "Non-physical knobs break realism; use for sensitivity exploration only.";

export function WarningsPanel(props: WarningsPanelProps): JSX.Element | null {
  const { warnings, nonPhysicalActive } = props;
  const uniqueWarnings = Array.from(new Set(warnings));

  if (!nonPhysicalActive && uniqueWarnings.length === 0) {
    return null;
  }

  return (
    <section className="panel panel-warning">
      <h2>Warnings</h2>
      {nonPhysicalActive ? <p className="warning-banner">{NON_PHYSICAL_WARNING}</p> : null}
      {uniqueWarnings.length > 0 ? (
        <ul>
          {uniqueWarnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
