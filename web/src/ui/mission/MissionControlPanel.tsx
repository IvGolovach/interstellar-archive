import { SIM_ENGINE_VERSION } from "../../lib/sim_public_contracts";
import type { MissionControlPanelModel, MissionFieldBinding } from "./mission_mode_contract";
import { inferStep, labelize } from "./mission_mode_helpers";

interface MissionControlPanelProps {
  model: MissionControlPanelModel;
}

interface MissionFieldInputProps {
  binding: MissionFieldBinding;
}

function MissionFieldInput(props: MissionFieldInputProps): JSX.Element {
  const { binding } = props;
  const { baseValue, currentValue, field, onValueChange } = binding;
  const deviates = currentValue !== baseValue;

  return (
    <label
      key={`${field.scope}-${field.id}`}
      className={`field mission-control-field${deviates ? " mission-control-field-deviated" : ""}`}
    >
      <span>
        {labelize(field.id)} ({field.spec.unit})
      </span>
      <input
        type="number"
        value={currentValue}
        min={field.spec.minimum}
        max={field.spec.maximum}
        step={inferStep(field.spec)}
        onChange={(event) => {
          const parsed = Number(event.target.value);
          if (!Number.isFinite(parsed)) {
            return;
          }
          onValueChange(field.id, parsed);
        }}
      />
      <small>
        Bounds: [{field.spec.minimum}, {field.spec.maximum}] | Baseline: {String(baseValue)}
      </small>
    </label>
  );
}

export function MissionControlPanel(props: MissionControlPanelProps): JSX.Element {
  const { model } = props;

  return (
    <section className="panel mission-control-panel">
      <h2>Parameter Control Panel</h2>
      <div className="mission-control-top-row">
        <label className="field compact-field">
          <span>Scenario</span>
          <select value={model.selectedScenarioId} onChange={(event) => model.onScenarioChange(event.target.value)}>
            {model.scenarios.map((scenario) => (
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
            value={model.seedOverride}
            placeholder="optional"
            onChange={(event) => {
              const raw = event.target.value.trim();
              if (raw === "" || /^[0-9]+$/.test(raw)) {
                model.onSeedOverrideChange(raw);
              }
            }}
          />
        </label>
        <div className="mission-control-meta">
          <p>Scenario seed token: {model.selectedScenarioSeed}</p>
          <p>Effective seed: {model.effectiveSeed}</p>
          <p>Last run: {model.runCount === 0 ? "not run yet" : `#${model.runCount}`}</p>
        </div>
      </div>

      <div className="mission-physics-locks">
        <h3>🔒 Physics (Read-only)</h3>
        <p className="help-text">Fundamental physical constraints (not editable).</p>
        <div className="mission-lock-grid">
          <label className="field">
            <span>Engine version</span>
            <input value={model.determinismStatus.engine_version ?? SIM_ENGINE_VERSION} disabled />
          </label>
          <label className="field">
            <span>Schema version</span>
            <input value={model.determinismStatus.schema_version ?? model.schemaVersion} disabled />
          </label>
          <label className="field">
            <span>Golden checksum</span>
            <input value={model.determinismStatus.golden_checksum ?? "unknown"} disabled />
          </label>
          <label className="field">
            <span>Risk envelope method</span>
            <input value="lower_quantile (q=0.05)" disabled />
          </label>
        </div>
      </div>

      <div className="mission-engineering-controls">
        <h3>🧱 Engineering (Editable)</h3>
        <div className="mission-field-grid">
          {model.engineeringFields.map((binding) => (
            <MissionFieldInput
              key={`${binding.field.scope}-${binding.field.id}`}
              binding={binding}
            />
          ))}
        </div>
      </div>

      <div className="mission-spec-controls">
        <h3>🧪 Speculative (Editable)</h3>
        {model.speculativeWarning ? (
          <p className="warning-banner">
            You are operating outside validated physical assumptions.
          </p>
        ) : null}
        <div className="mission-field-grid">
          {model.speculativeFields.map((binding) => (
            <MissionFieldInput
              key={`${binding.field.scope}-${binding.field.id}`}
              binding={binding}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
