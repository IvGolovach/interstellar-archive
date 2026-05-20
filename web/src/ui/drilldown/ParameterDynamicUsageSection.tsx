import type {
  DynamicStaticValidationResult,
  DynamicTraceIndex,
} from "../../lib/parameter_drilldown_loader";

interface ParameterDynamicUsageSectionProps {
  dynamicEvents: DynamicTraceIndex["events"];
  dynamicTrace: DynamicTraceIndex | null;
  dynamicTraceLoadError: string | null;
  dynamicValidation: DynamicStaticValidationResult | null;
  onLoadDynamicTraceFile: (file: File) => Promise<void>;
}

export function ParameterDynamicUsageSection(
  props: ParameterDynamicUsageSectionProps,
): JSX.Element {
  const {
    dynamicEvents,
    dynamicTrace,
    dynamicTraceLoadError,
    dynamicValidation,
    onLoadDynamicTraceFile,
  } = props;

  return (
    <article className="drilldown-section">
      <h3>Dynamic Usage (dev-local)</h3>
      <p className="help-text">
        Local-only mode. Load a local <code>parameter_dynamic_trace_index.json</code> to inspect
        module-level attribution.
      </p>
      <label className="field compact-field">
        <span>Dynamic trace file</span>
        <input
          type="file"
          accept="application/json,.json"
          onChange={async (event) => {
            const file = event.target.files?.[0];
            if (!file) {
              return;
            }
            await onLoadDynamicTraceFile(file);
          }}
        />
      </label>

      {dynamicTraceLoadError ? <p className="error-text">{dynamicTraceLoadError}</p> : null}

      {dynamicValidation && dynamicValidation.status === "FAIL" ? (
        <div className="panel panel-error">
          <h4>CONTRACT VIOLATION</h4>
          <p>
            Dynamic trace contract check failed. Section rendering is halted until the trace
            satisfies static usage contract.
          </p>
          {dynamicValidation.violations.length > 0 ? (
            <ul className="compact-list mono-cell">
              {dynamicValidation.violations.slice(0, 8).map((violation, index) => (
                <li key={`${violation.parameter_id}-${violation.module_id}-${index}`}>
                  event={violation.event_index} parameter={violation.parameter_id} module=
                  {violation.module_id} reason={violation.reason}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {dynamicTrace && dynamicValidation?.status === "PASS" ? (
        <>
          <h4>Run header</h4>
          <dl className="definition-grid">
            <dt>run_id</dt>
            <dd className="mono-cell">{dynamicTrace.run_id}</dd>
            <dt>commit_sha</dt>
            <dd className="mono-cell">{dynamicTrace.commit_sha}</dd>
            <dt>scenario_path</dt>
            <dd className="mono-cell">{dynamicTrace.scenario_path}</dd>
            <dt>mode</dt>
            <dd>{dynamicTrace.mode}</dd>
            <dt>seed</dt>
            <dd>{dynamicTrace.seed}</dd>
            <dt>artifact_hash</dt>
            <dd className="mono-cell">{dynamicTrace.artifact_hash}</dd>
            <dt>hashchain_verified</dt>
            <dd>{dynamicTrace.hashchain_verified ? "true" : "false"}</dd>
          </dl>

          <h4>Dynamic events for parameter</h4>
          {dynamicEvents.length > 0 ? (
            <ul className="compact-list mono-cell">
              {dynamicEvents.map((event, index) => (
                <li key={`${event.module_id}-${event.node_id}-${index}`}>
                  {event.mode}::{event.node_id}::{event.module_id} failure=
                  {event.failure_mode ?? "none"} in={event.inputs_hash} out={event.outputs_hash}
                </li>
              ))}
            </ul>
          ) : (
            <p>No dynamic events for this parameter in loaded trace.</p>
          )}
        </>
      ) : null}
    </article>
  );
}
