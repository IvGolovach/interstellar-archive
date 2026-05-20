import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { NON_PHYSICAL_WARNING, runSimulation } from "../src/lib/sim_runner";
import {
  buildInputFromValues,
  getScenarioRegistry,
  loadSchema,
  withClockDefaults,
  withParameterDefaults,
} from "../src/lib/schema_loader";
import { MissionResultsPanel } from "../src/ui/mission/MissionResultsPanel";
import type {
  MissionResultsPanelModel,
  RunState,
} from "../src/ui/mission/mission_mode_contract";

function buildProjection(): MissionResultsPanelModel["projection"] {
  return {
    dominantDrivers: ["driver.alpha", "driver.beta", "driver.gamma"],
    failureMode: "STATIC_BASELINE_FAILURE",
    failureStage: "S3",
    projectedPSuccess: 0.5,
    projectedRiskEnvelope: 0.25,
    selectedCandidateId: "candidate-1",
    selectedFrontierIndex: 0,
  };
}

function buildLastRun(): RunState {
  const schema = loadSchema();
  const scenario = getScenarioRegistry()[0];
  if (!scenario) {
    throw new Error("No scenario found.");
  }

  const input = buildInputFromValues({
    schema,
    scenarioId: "mission-results-panel-test",
    seed: "mission-results-panel-seed",
    params: {
      ...withParameterDefaults(schema, scenario.params),
      narrative_leverage_multiplier: 1.2,
    },
    clock: { ...withClockDefaults(schema, scenario.clock) },
  });

  return {
    input,
    output: runSimulation(input),
  };
}

describe("mission mode results panel", () => {
  it("renders real last-run metrics, checksum, and warnings alongside static projection", () => {
    const lastRun = buildLastRun();
    expect(lastRun.output.warnings).toContain(NON_PHYSICAL_WARNING);

    const model = {
      lastRun,
      projection: buildProjection(),
      runError: null,
    } satisfies MissionResultsPanelModel;

    const html = renderToStaticMarkup(<MissionResultsPanel model={model} />);

    expect(html).toContain("Projected from static frontier");
    expect(html).toContain("Last run output");
    expect(html).toContain("Encounter likelihood");
    expect(html).toContain(lastRun.output.derived_metrics.encounter_likelihood_percent.toFixed(6));
    expect(html).toContain("Golden checksum");
    expect(html).toContain(lastRun.output.golden_checksum);
    expect(html).toContain(NON_PHYSICAL_WARNING);
  });
});
