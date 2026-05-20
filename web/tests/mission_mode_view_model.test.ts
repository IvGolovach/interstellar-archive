import { describe, expect, it, vi } from "vitest";

import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import {
  getScenarioRegistry,
  getSchemaFields,
  loadSchema,
} from "../src/lib/schema_loader";
import type { MissionField } from "../src/ui/mission/mission_mode_contract";
import {
  bindMissionFields,
  buildMissionControlPanelModel,
  buildMissionModeOverviewModel,
  buildMissionOptimizationPanelModel,
  buildMissionResultsPanelModel,
} from "../src/ui/mission/mission_mode_view_model";

function firstFieldByCategory(category: string): MissionField {
  const schema = loadSchema();
  const field = getSchemaFields(schema).find((candidate) => candidate.category === category);
  if (!field) {
    throw new Error(`Field with category '${category}' not found.`);
  }
  return { id: field.id, scope: field.scope, spec: field };
}

describe("mission mode view models", () => {
  it("binds mission fields to the correct state buckets and handlers", () => {
    const engineeringField = firstFieldByCategory("safe");
    const speculativeField = firstFieldByCategory("non_physical");
    const onClockChange = vi.fn();
    const onParamsChange = vi.fn();

    const bindings = bindMissionFields({
      baselineClock: { [engineeringField.id]: 10, [speculativeField.id]: 20 },
      baselineParams: { [engineeringField.id]: 30, [speculativeField.id]: 40 },
      clock: { [engineeringField.id]: 11, [speculativeField.id]: 21 },
      fields: [engineeringField, speculativeField],
      onClockChange,
      onParamsChange,
      params: { [engineeringField.id]: 31, [speculativeField.id]: 41 },
    });

    expect(bindings).toHaveLength(2);
    expect(bindings[0]?.currentValue).toBe(
      engineeringField.scope === "params" ? 31 : 11,
    );
    expect(bindings[0]?.baseValue).toBe(
      engineeringField.scope === "params" ? 30 : 10,
    );
    expect(bindings[1]?.currentValue).toBe(
      speculativeField.scope === "params" ? 41 : 21,
    );

    bindings[0]?.onValueChange(bindings[0].field.id, 99);
    bindings[1]?.onValueChange(bindings[1].field.id, 77);

    if (engineeringField.scope === "params") {
      expect(onParamsChange).toHaveBeenCalledWith(engineeringField.id, 99);
    } else {
      expect(onClockChange).toHaveBeenCalledWith(engineeringField.id, 99);
    }
    if (speculativeField.scope === "params") {
      expect(onParamsChange).toHaveBeenCalledWith(speculativeField.id, 77);
    } else {
      expect(onClockChange).toHaveBeenCalledWith(speculativeField.id, 77);
    }
  });

  it("preserves section model values without reshaping behavior", () => {
    const scenario = getScenarioRegistry()[0];
    const drilldown = loadParameterDrilldownDataset();
    const onRunMission = vi.fn();
    const onScenarioChange = vi.fn();
    const onSeedOverrideChange = vi.fn();
    const onToggle = vi.fn();

    const overviewModel = buildMissionModeOverviewModel({
      baselinePSuccess: drilldown.objectiveScoreBaseline.scores.realistic.p_success,
      onRunMission,
    });
    const resultsModel = buildMissionResultsPanelModel({
      lastRun: null,
      projection: {
        dominantDrivers: ["a", "b", "c"],
        failureMode: "TEST_FAILURE",
        failureStage: "S3",
        projectedPSuccess: 0.5,
        projectedRiskEnvelope: 0.25,
        selectedCandidateId: "candidate-1",
        selectedFrontierIndex: 0,
      },
      runError: null,
    });
    const optimizationModel = buildMissionOptimizationPanelModel({
      baselineScore: drilldown.objectiveScoreBaseline,
      expanded: false,
      frontier: drilldown.optimizationFrontier,
      onToggle,
      selectedCandidateId: "candidate-1",
    });
    const controlPanelModel = buildMissionControlPanelModel({
      determinismStatus: drilldown.determinismStatus,
      effectiveSeed: scenario.seed,
      engineeringFields: [],
      onScenarioChange,
      onSeedOverrideChange,
      runCount: 0,
      scenarios: getScenarioRegistry(),
      schemaVersion: loadSchema().schema_version,
      seedOverride: "",
      selectedScenarioId: scenario.scenario_id,
      selectedScenarioSeed: scenario.seed,
      speculativeFields: [],
      speculativeWarning: false,
    });

    overviewModel.onRunMission();
    optimizationModel.onToggle();
    controlPanelModel.onScenarioChange(scenario.scenario_id);
    controlPanelModel.onSeedOverrideChange("7");

    expect(onRunMission).toHaveBeenCalledTimes(1);
    expect(onToggle).toHaveBeenCalledTimes(1);
    expect(onScenarioChange).toHaveBeenCalledWith(scenario.scenario_id);
    expect(onSeedOverrideChange).toHaveBeenCalledWith("7");
    expect(resultsModel.projection.failureMode).toBe("TEST_FAILURE");
    expect(resultsModel.projection.dominantDrivers).toEqual(["a", "b", "c"]);
    expect(optimizationModel.baselineScore.schema_version).toBe("objective_score.v1");
    expect(optimizationModel.frontier.schema_version).toBe("optimization_frontier.v1");
  });
});
