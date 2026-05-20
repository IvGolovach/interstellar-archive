import { describe, expect, it } from "vitest";

import type { RunState } from "../src/ui/mission/mission_mode_contract";
import {
  createMissionModeInitialState,
  missionModeReducer,
} from "../src/ui/mission/mission_mode_state";

function buildRunState(seed: string): RunState {
  return {
    input: {
      schema_version: "sim_schema.v1",
      scenario_id: "baseline",
      seed,
      params: {} as never,
      clock: {} as never,
      units: "arb",
    },
    output: {
      output_version: "sim_output.v1",
      engine_version: "v1",
      schema_version: "sim_schema.v1",
      golden_checksum: "checksum",
      derived_metrics: {
        finite_control_window_year: 1,
        terminal_interaction_radius_au: 2,
        encounter_likelihood_percent: 3,
        expected_mm_tail_hits: 4,
        shield_survival_margin: 5,
      },
      series: [],
      warnings: [],
      invariants_passed: true,
      checksum_payload: "payload",
    },
  };
}

describe("mission mode state", () => {
  it("creates a stable initial state from scenario baselines", () => {
    const state = createMissionModeInitialState({
      scenarioId: "baseline",
      params: { alpha: 1 },
      clock: { horizon_years: 180 },
    });

    expect(state).toEqual({
      selectedScenarioId: "baseline",
      seedOverride: "",
      params: { alpha: 1 },
      clock: { horizon_years: 180 },
      runState: null,
      runError: null,
      runCount: 0,
      optimizationExpanded: false,
    });
  });

  it("resets scenario-specific state while preserving optimization expansion", () => {
    const initial = createMissionModeInitialState({
      scenarioId: "baseline",
      params: { alpha: 1 },
      clock: { horizon_years: 180 },
    });
    const withRun = missionModeReducer(initial, {
      type: "recordRunSuccess",
      payload: buildRunState("seed-1"),
    });
    const expanded = missionModeReducer(withRun, {
      type: "toggleOptimizationExpanded",
    });
    const changed = missionModeReducer(expanded, {
      type: "selectScenario",
      payload: {
        scenarioId: "alternate",
        params: { alpha: 5 },
        clock: { horizon_years: 90 },
      },
    });

    expect(changed.selectedScenarioId).toBe("alternate");
    expect(changed.seedOverride).toBe("");
    expect(changed.params).toEqual({ alpha: 5 });
    expect(changed.clock).toEqual({ horizon_years: 90 });
    expect(changed.runState).toBeNull();
    expect(changed.runError).toBeNull();
    expect(changed.runCount).toBe(0);
    expect(changed.optimizationExpanded).toBe(true);
  });

  it("updates clock and parameter fields independently", () => {
    const initial = createMissionModeInitialState({
      scenarioId: "baseline",
      params: { alpha: 1 },
      clock: { horizon_years: 180 },
    });
    const withParam = missionModeReducer(initial, {
      type: "setParamField",
      payload: { fieldId: "alpha", value: 7 },
    });
    const withClock = missionModeReducer(withParam, {
      type: "setClockField",
      payload: { fieldId: "horizon_years", value: 120 },
    });

    expect(withClock.params).toEqual({ alpha: 7 });
    expect(withClock.clock).toEqual({ horizon_years: 120 });
  });

  it("records successful and failed runs with the expected counters", () => {
    const initial = createMissionModeInitialState({
      scenarioId: "baseline",
      params: { alpha: 1 },
      clock: { horizon_years: 180 },
    });
    const succeeded = missionModeReducer(initial, {
      type: "recordRunSuccess",
      payload: buildRunState("seed-2"),
    });
    const failed = missionModeReducer(succeeded, {
      type: "recordRunFailure",
      payload: "Mission run failed.",
    });

    expect(succeeded.runCount).toBe(1);
    expect(succeeded.runError).toBeNull();
    expect(succeeded.runState?.input.seed).toBe("seed-2");
    expect(failed.runCount).toBe(1);
    expect(failed.runState).toBeNull();
    expect(failed.runError).toBe("Mission run failed.");
  });
});
