export interface DynamicTraceEvent {
  mode: "realistic" | "speculative";
  node_id: string;
  module_id: string;
  inputs_hash: string;
  outputs_hash: string;
  failure_mode: string | null;
  dominant_driver_parameter_ids: string[];
}

export interface DynamicTraceIndex {
  run_id: string;
  commit_sha: string;
  mode: "realistic" | "speculative" | "dual";
  seed: number;
  scenario_path: string;
  artifact_hash: string;
  hashchain_verified: boolean;
  events: DynamicTraceEvent[];
}

export interface DynamicStaticViolation {
  event_index: number;
  parameter_id: string;
  module_id: string;
  reason: string;
}

export interface DynamicStaticValidationResult {
  status: "PASS" | "FAIL";
  event_count: number;
  checked_parameter_module_pairs: number;
  violation_count: number;
  violations: DynamicStaticViolation[];
  errors: string[];
}
