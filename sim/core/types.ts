export const SIM_ENGINE_VERSION = "v1";

export type ParamCategory = "safe" | "advanced" | "non_physical";

export interface NumericFieldSpec {
  type: "number";
  minimum: number;
  maximum: number;
  default: number;
  unit: string;
  category: ParamCategory;
  help: string;
  warning?: string;
}

export interface SimSchema {
  schema_version: string;
  artifact_schema_version: string;
  breaking_change_flag: boolean;
  units: string;
  parameters: Record<string, NumericFieldSpec>;
  clock: Record<string, NumericFieldSpec>;
  required_parameters: string[];
  required_clock: string[];
}

export interface SimParams {
  encounter_distance_au: number;
  correction_window_years: number;
  initial_delta_v_mps: number;
  uncertainty_growth_per_year: number;
  dust_flux_scale: number;
  shield_geometry_factor: number;
  narrative_leverage_multiplier: number;
  irreversibility_override: number;
}

export interface ClockConfig {
  step_years: number;
  horizon_years: number;
}

export interface SimInput {
  schema_version: string;
  scenario_id: string;
  seed: string;
  params: SimParams;
  clock: ClockConfig;
  units: string;
}

export interface SimSeriesPoint {
  year: number;
  control_leverage: number;
  encounter_likelihood: number;
  lethal_hit_rate: number;
}

export interface SimDerivedMetrics {
  finite_control_window_year: number;
  terminal_interaction_radius_au: number;
  encounter_likelihood_percent: number;
  expected_mm_tail_hits: number;
  shield_survival_margin: number;
}

export interface SimOutput {
  output_version: string;
  engine_version: string;
  schema_version: string;
  golden_checksum: string;
  derived_metrics: SimDerivedMetrics;
  series: SimSeriesPoint[];
  warnings: string[];
  invariants_passed: boolean;
  checksum_payload: string;
}

export interface SimScenario {
  schema_version: string;
  scenario_id: string;
  seed: string;
  params: Partial<SimParams>;
  clock: Partial<ClockConfig>;
  notes: string;
}
