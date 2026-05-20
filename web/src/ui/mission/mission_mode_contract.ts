import type {
  ObjectiveScoreBaseline,
  OptimizationFrontierArtifact,
} from "../../lib/parameter_drilldown_loader";
import type {
  NumericFieldSpec,
  SimInput,
  SimOutput,
  SimScenario,
} from "../../../../sim/public/types";
import type { MissionProjection } from "./mission_mode_model";

export interface DeterminismStatus {
  last_verified_commit_sha?: string;
  engine_version?: string;
  schema_version?: string;
  golden_checksum?: string;
}

export interface RunState {
  input: SimInput;
  output: SimOutput;
}

export interface MissionField {
  id: string;
  scope: "params" | "clock";
  spec: NumericFieldSpec;
}

export interface MissionFieldBinding {
  baseValue: number;
  currentValue: number;
  field: MissionField;
  onValueChange: (fieldId: string, value: number) => void;
}

export interface MissionControlPanelModel {
  determinismStatus: DeterminismStatus;
  effectiveSeed: string;
  engineeringFields: MissionFieldBinding[];
  onScenarioChange: (scenarioId: string) => void;
  onSeedOverrideChange: (value: string) => void;
  runCount: number;
  scenarios: SimScenario[];
  schemaVersion: string;
  seedOverride: string;
  selectedScenarioId: string;
  selectedScenarioSeed: string;
  speculativeFields: MissionFieldBinding[];
  speculativeWarning: boolean;
}

export interface MissionModeOverviewModel {
  baselinePSuccess: number;
  onRunMission: () => void;
}

export interface MissionResultsPanelModel {
  lastRun: RunState | null;
  projection: MissionProjection;
  runError: string | null;
}

export interface MissionOptimizationPanelModel {
  baselineScore: ObjectiveScoreBaseline;
  expanded: boolean;
  frontier: OptimizationFrontierArtifact;
  onToggle: () => void;
  selectedCandidateId: string | null;
}
