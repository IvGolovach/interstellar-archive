import { useMemo, useReducer } from "react";
import type {
  SimInput,
  SimScenario,
  SimSchema,
} from "../../../../sim/public/types";
import { loadParameterDrilldownDataset } from "../../lib/parameter_drilldown_loader";
import { runSimulation } from "../../lib/sim_runner";
import {
  buildInputFromValues,
  getSchemaFields,
  getScenarioRegistry,
  loadSchema,
} from "../../lib/schema_loader";
import type {
  DeterminismStatus,
  MissionControlPanelModel,
  MissionField,
  MissionModeOverviewModel,
  MissionOptimizationPanelModel,
  MissionResultsPanelModel,
} from "./mission_mode_contract";
import {
  baselineClockForScenario,
  baselineParamsForScenario,
  findScenario,
  sortFields,
} from "./mission_mode_helpers";
import { buildMissionProjection, isSpeculativeWarningActive } from "./mission_mode_model";
import {
  bindMissionFields,
  buildMissionControlPanelModel,
  buildMissionModeOverviewModel,
  buildMissionOptimizationPanelModel,
  buildMissionResultsPanelModel,
} from "./mission_mode_view_model";
import {
  createMissionModeInitialState,
  missionModeReducer,
} from "./mission_mode_state";

interface GroupedMissionFields {
  engineering: MissionField[];
  speculative: MissionField[];
}

interface UseMissionModeResult {
  controlPanelModel: MissionControlPanelModel;
  optimizationPanelModel: MissionOptimizationPanelModel;
  overviewModel: MissionModeOverviewModel;
  resultsPanelModel: MissionResultsPanelModel;
  stageTimelineBaseline: ReturnType<typeof loadParameterDrilldownDataset>["failureSurfaceBaseline"];
}

export function useMissionMode(): UseMissionModeResult {
  const schema = useMemo<SimSchema>(() => loadSchema(), []);
  const scenarios = useMemo<SimScenario[]>(() => getScenarioRegistry(), []);
  const drilldown = useMemo(() => loadParameterDrilldownDataset(), []);
  const initialScenario = useMemo(() => {
    if (scenarios.length === 0) {
      throw new Error("No scenarios found.");
    }
    return scenarios[0];
  }, [scenarios]);

  const [state, dispatch] = useReducer(
    missionModeReducer,
    {
      scenarioId: initialScenario.scenario_id,
      params: baselineParamsForScenario(schema, initialScenario),
      clock: baselineClockForScenario(schema, initialScenario),
    },
    createMissionModeInitialState,
  );

  const selectedScenario = useMemo(
    () => findScenario(scenarios, state.selectedScenarioId),
    [scenarios, state.selectedScenarioId],
  );
  const baselineParams = useMemo(
    () => baselineParamsForScenario(schema, selectedScenario),
    [schema, selectedScenario],
  );
  const baselineClock = useMemo(
    () => baselineClockForScenario(schema, selectedScenario),
    [schema, selectedScenario],
  );
  const groupedFields = useMemo<GroupedMissionFields>(() => {
    const fields = getSchemaFields(schema).map(
      (field): MissionField => ({ id: field.id, scope: field.scope, spec: field }),
    );
    return {
      engineering: sortFields(
        fields.filter((field) => field.spec.category === "safe" || field.spec.category === "advanced"),
      ),
      speculative: sortFields(fields.filter((field) => field.spec.category === "non_physical")),
    };
  }, [schema]);

  const determinismStatus = drilldown.determinismStatus as DeterminismStatus;
  const effectiveSeed = state.seedOverride.trim() === ""
    ? selectedScenario.seed
    : state.seedOverride.trim();
  const speculativeWarning = isSpeculativeWarningActive(schema, state.params);
  const projectionParams = state.runState?.input.params ?? baselineParams;
  const projection = useMemo(
    () =>
      buildMissionProjection({
        params: projectionParams as Record<string, number>,
        baselineFailureSurface: drilldown.failureSurfaceBaseline,
        baselineObjectiveScore: drilldown.objectiveScoreBaseline,
        frontier: drilldown.optimizationFrontier,
        searchSpace: drilldown.optimizationSearchSpace,
      }),
    [projectionParams, drilldown, state.runState],
  );

  function resetForScenario(nextScenarioId: string): void {
    const nextScenario = findScenario(scenarios, nextScenarioId);
    dispatch({
      type: "selectScenario",
      payload: {
        scenarioId: nextScenarioId,
        params: baselineParamsForScenario(schema, nextScenario),
        clock: baselineClockForScenario(schema, nextScenario),
      },
    });
  }

  function runMission(): void {
    try {
      const input: SimInput = buildInputFromValues({
        schema,
        scenarioId: selectedScenario.scenario_id,
        seed: effectiveSeed,
        params: state.params,
        clock: state.clock,
      });
      const output = runSimulation(input);
      dispatch({ type: "recordRunSuccess", payload: { input, output } });
    } catch (error) {
      dispatch({
        type: "recordRunFailure",
        payload: error instanceof Error ? error.message : "Mission run failed.",
      });
    }
  }

  const setClockField = (fieldId: string, value: number): void => {
    dispatch({ type: "setClockField", payload: { fieldId, value } });
  };
  const setParamsField = (fieldId: string, value: number): void => {
    dispatch({ type: "setParamField", payload: { fieldId, value } });
  };

  const controlPanelModel = useMemo<MissionControlPanelModel>(
    () => buildMissionControlPanelModel({
      determinismStatus,
      effectiveSeed,
      engineeringFields: bindMissionFields({
        baselineClock,
        baselineParams,
        clock: state.clock,
        fields: groupedFields.engineering,
        onClockChange: setClockField,
        onParamsChange: setParamsField,
        params: state.params,
      }),
      onScenarioChange: resetForScenario,
      onSeedOverrideChange: (value) => dispatch({ type: "setSeedOverride", payload: value }),
      runCount: state.runCount,
      scenarios,
      schemaVersion: schema.schema_version,
      seedOverride: state.seedOverride,
      selectedScenarioId: state.selectedScenarioId,
      selectedScenarioSeed: selectedScenario.seed,
      speculativeFields: bindMissionFields({
        baselineClock,
        baselineParams,
        clock: state.clock,
        fields: groupedFields.speculative,
        onClockChange: setClockField,
        onParamsChange: setParamsField,
        params: state.params,
      }),
      speculativeWarning,
    }),
    [
      baselineClock,
      baselineParams,
      determinismStatus,
      effectiveSeed,
      groupedFields,
      resetForScenario,
      scenarios,
      schema.schema_version,
      state.clock,
      state.params,
      state.runCount,
      state.seedOverride,
      state.selectedScenarioId,
      selectedScenario.seed,
      speculativeWarning,
    ],
  );

  const overviewModel = useMemo<MissionModeOverviewModel>(
    () => buildMissionModeOverviewModel({
      baselinePSuccess: drilldown.objectiveScoreBaseline.scores.realistic.p_success,
      onRunMission: runMission,
    }),
    [drilldown.objectiveScoreBaseline.scores.realistic.p_success, runMission],
  );

  const resultsPanelModel = useMemo<MissionResultsPanelModel>(
    () => buildMissionResultsPanelModel({
      lastRun: state.runState,
      projection,
      runError: state.runError,
    }),
    [projection, state.runError, state.runState],
  );

  const optimizationPanelModel = useMemo<MissionOptimizationPanelModel>(
    () => buildMissionOptimizationPanelModel({
      baselineScore: drilldown.objectiveScoreBaseline,
      expanded: state.optimizationExpanded,
      frontier: drilldown.optimizationFrontier,
      onToggle: () => dispatch({ type: "toggleOptimizationExpanded" }),
      selectedCandidateId: projection.selectedCandidateId,
    }),
    [
      drilldown.objectiveScoreBaseline,
      drilldown.optimizationFrontier,
      projection.selectedCandidateId,
      state.optimizationExpanded,
    ],
  );

  return {
    controlPanelModel,
    optimizationPanelModel,
    overviewModel,
    resultsPanelModel,
    stageTimelineBaseline: drilldown.failureSurfaceBaseline,
  };
}
