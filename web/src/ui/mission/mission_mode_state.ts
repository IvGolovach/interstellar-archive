import type { RunState } from "./mission_mode_contract";

export interface MissionModeState {
  selectedScenarioId: string;
  seedOverride: string;
  params: Record<string, number>;
  clock: Record<string, number>;
  runState: RunState | null;
  runError: string | null;
  runCount: number;
  optimizationExpanded: boolean;
}

interface ScenarioSelectionPayload {
  scenarioId: string;
  params: Record<string, number>;
  clock: Record<string, number>;
}

export type MissionModeAction =
  | { type: "selectScenario"; payload: ScenarioSelectionPayload }
  | { type: "setSeedOverride"; payload: string }
  | { type: "setParamField"; payload: { fieldId: string; value: number } }
  | { type: "setClockField"; payload: { fieldId: string; value: number } }
  | { type: "recordRunSuccess"; payload: RunState }
  | { type: "recordRunFailure"; payload: string }
  | { type: "toggleOptimizationExpanded" };

export function createMissionModeInitialState(
  payload: ScenarioSelectionPayload,
): MissionModeState {
  return {
    selectedScenarioId: payload.scenarioId,
    seedOverride: "",
    params: payload.params,
    clock: payload.clock,
    runState: null,
    runError: null,
    runCount: 0,
    optimizationExpanded: false,
  };
}

function updateFieldValue(
  current: Record<string, number>,
  fieldId: string,
  value: number,
): Record<string, number> {
  return { ...current, [fieldId]: value };
}

export function missionModeReducer(
  state: MissionModeState,
  action: MissionModeAction,
): MissionModeState {
  switch (action.type) {
    case "selectScenario":
      return {
        ...state,
        selectedScenarioId: action.payload.scenarioId,
        seedOverride: "",
        params: action.payload.params,
        clock: action.payload.clock,
        runState: null,
        runError: null,
        runCount: 0,
      };
    case "setSeedOverride":
      return {
        ...state,
        seedOverride: action.payload,
      };
    case "setParamField":
      return {
        ...state,
        params: updateFieldValue(state.params, action.payload.fieldId, action.payload.value),
      };
    case "setClockField":
      return {
        ...state,
        clock: updateFieldValue(state.clock, action.payload.fieldId, action.payload.value),
      };
    case "recordRunSuccess":
      return {
        ...state,
        runState: action.payload,
        runError: null,
        runCount: state.runCount + 1,
      };
    case "recordRunFailure":
      return {
        ...state,
        runState: null,
        runError: action.payload,
      };
    case "toggleOptimizationExpanded":
      return {
        ...state,
        optimizationExpanded: !state.optimizationExpanded,
      };
  }

  const exhaustive: never = action;
  throw new Error(`Unhandled mission mode action: ${String(exhaustive)}`);
}
