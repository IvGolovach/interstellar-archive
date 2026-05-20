import type { SimScenario } from "../../../sim/public/types";

interface ScenarioPickerProps {
  scenarios: SimScenario[];
  selectedScenarioId: string;
  onScenarioChange: (scenarioId: string) => void;
  seedOverride: string;
  onSeedOverrideChange: (seed: string) => void;
  baseScenarioSeed: string;
  onRunScenario: () => void;
  lastRunAtUtc: string | null;
  engineVersion: string;
  schemaVersion: string;
  runError: string | null;
}

export function ScenarioPicker(props: ScenarioPickerProps): JSX.Element {
  const {
    scenarios,
    selectedScenarioId,
    onScenarioChange,
    seedOverride,
    onSeedOverrideChange,
    baseScenarioSeed,
    onRunScenario,
    lastRunAtUtc,
    engineVersion,
    schemaVersion,
    runError,
  } = props;
  const selectedScenario = scenarios.find((item) => item.scenario_id === selectedScenarioId);

  return (
    <section id="run-controls">
      <h2>Run Controls</h2>
      <div className="run-toolbar">
        <label className="field compact-field">
          <span>Scenario</span>
          <select value={selectedScenarioId} onChange={(event) => onScenarioChange(event.target.value)}>
            {scenarios.map((scenario) => (
              <option key={scenario.scenario_id} value={scenario.scenario_id}>
                {scenario.scenario_id}
              </option>
            ))}
          </select>
        </label>
        <label className="field compact-field">
          <span>Seed (numeric override)</span>
          <input
            type="number"
            step="1"
            min={0}
            inputMode="numeric"
            value={seedOverride}
            placeholder="optional"
            onChange={(event) => {
              const raw = event.target.value.trim();
              if (raw === "" || /^[0-9]+$/.test(raw)) {
                onSeedOverrideChange(raw);
              }
            }}
          />
        </label>
        <button className="run-button" type="button" onClick={onRunScenario}>
          Run
        </button>
      </div>
      <div className="run-meta">
        <p className="help-text">Last run: {lastRunAtUtc ? lastRunAtUtc : "not run yet"}</p>
        <div className="badge-row">
          <span className="meta-badge">engine {engineVersion}</span>
          <span className="meta-badge">schema {schemaVersion}</span>
        </div>
      </div>
      {runError ? <p className="error-text">{runError}</p> : null}
      <p className="help-text">Scenario seed token: {baseScenarioSeed}</p>
      {selectedScenario ? <p className="help-text">{selectedScenario.notes}</p> : null}
    </section>
  );
}
