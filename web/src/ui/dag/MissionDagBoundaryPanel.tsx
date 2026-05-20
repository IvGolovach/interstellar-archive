import { useMemo } from "react";

import { PUBLIC_DATASET_PATHS } from "../../lib/artifact_public_contracts";
import type { MissionDagV2BoundaryArtifact } from "../../lib/parameter_drilldown_loader";

interface MissionDagBoundaryPanelProps {
  boundary: MissionDagV2BoundaryArtifact;
  selectedModuleId?: string;
}

export function MissionDagBoundaryPanel({
  boundary,
  selectedModuleId,
}: MissionDagBoundaryPanelProps): JSX.Element {
  const selectedModule = useMemo(() => {
    if (!selectedModuleId) {
      return boundary.module_boundaries[0];
    }
    return boundary.module_boundaries.find((row) => row.module_id === selectedModuleId);
  }, [boundary.module_boundaries, selectedModuleId]);
  const artifactHref = useMemo(
    () =>
      `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(boundary, null, 2))}`,
    [boundary],
  );

  return (
    <article className="drilldown-section">
      <h3>Mission DAG v2 boundary</h3>
      <p className="help-text">
        Source: <code>{PUBLIC_DATASET_PATHS.missionDagV2Boundary}</code>
      </p>

      <h4>Boundary rollup</h4>
      <ul className="compact-list mono-cell">
        <li>schema: {boundary.schema_version}</li>
        <li>modules: {boundary.module_count}</li>
        <li>state_trace_contract_complete: {String(boundary.rollup.state_trace_contract_complete)}</li>
        <li>module_io_schema_contract_available: {String(boundary.rollup.module_io_schema_contract_available)}</li>
        <li>hashchain_contract_available: {String(boundary.rollup.hashchain_contract_available)}</li>
        <li>independent_backend_complete: {String(boundary.rollup.independent_backend_complete)}</li>
        <li>high_fidelity_state_traces_available: {String(boundary.rollup.high_fidelity_state_traces_available)}</li>
      </ul>

      <h4>Module rows</h4>
      <ol className="compact-list mono-cell">
        {boundary.module_boundaries.map((row) => (
          <li key={row.module_id}>
            {row.module_id} | {row.module_type} | node={row.scenario_node_ids.join(",")} | taxonomy=
            {row.failure_taxonomy_ids.length} | v1_wrapper=
            {String(row.current_v1_support.wrapper_over_reduced_order_baseline)}
          </li>
        ))}
      </ol>

      {selectedModuleId && !selectedModule ? (
        <>
          <h4>Selected module</h4>
          <p className="help-text mono-cell">
            module id not found in mission_dag_v2_boundary.v1: {selectedModuleId}
          </p>
        </>
      ) : null}

      {selectedModule ? (
        <>
          <h4>Selected module</h4>
          <ul className="compact-list mono-cell">
            <li>{selectedModule.module_id}</li>
            <li>entrypoint: {selectedModule.entrypoint}</li>
            <li>schema: {selectedModule.input_schema_ref} {"->"} {selectedModule.output_schema_ref}</li>
            <li>scenario nodes: {selectedModule.scenario_node_ids.join(", ")}</li>
            <li>failure taxonomy: {selectedModule.failure_taxonomy_ids.join(", ")}</li>
            <li>independent_backend_id_declared: {String(selectedModule.current_v1_support.independent_backend_id_declared)}</li>
            <li>high_fidelity_state_trace_available: {String(selectedModule.current_v1_support.high_fidelity_state_trace_available)}</li>
          </ul>
        </>
      ) : null}

      <h4>Required v2 boundary fields</h4>
      <ul className="compact-list">
        {(selectedModule?.v2_boundary_requirements ?? boundary.module_boundaries[0]?.v2_boundary_requirements ?? []).map(
          (requirement) => (
            <li key={requirement}>{requirement}</li>
          ),
        )}
      </ul>

      <h4>External evidence still required</h4>
      <ul className="compact-list">
        {boundary.external_evidence_gaps.map((gap) => (
          <li key={gap}>{gap}</li>
        ))}
      </ul>

      <h4>Blocked claims</h4>
      <ul className="compact-list">
        {boundary.blocked_claims.map((claim) => (
          <li key={claim}>{claim}</li>
        ))}
      </ul>

      <h4>Artifact link</h4>
      <p className="compact-list">
        <a href={artifactHref} download="mission_dag_v2_boundary.v1.json">
          Open Mission DAG v2 boundary JSON
        </a>
      </p>
    </article>
  );
}
