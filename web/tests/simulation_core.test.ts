import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import type { SimScenario } from "../../sim/public/types";
import {
  buildInputFromValues,
  getScenarioRegistry,
  loadSchema,
  validateScenario,
  withClockDefaults,
  withParameterDefaults,
} from "../src/lib/schema_loader";
import { NON_PHYSICAL_WARNING, runSimulation } from "../src/lib/sim_runner";

describe("simulation core determinism", () => {
  it("produces identical outputs for identical input", () => {
    const schema = loadSchema();
    const defaultScenario = getScenarioRegistry().find((scenario) => scenario.scenario_id === "default.v1");
    expect(defaultScenario).toBeTruthy();

    const input = buildInputFromValues({
      schema,
      scenarioId: defaultScenario!.scenario_id,
      seed: defaultScenario!.seed,
      params: withParameterDefaults(schema, defaultScenario!.params),
      clock: withClockDefaults(schema, defaultScenario!.clock),
    });

    const first = runSimulation(input);
    const second = runSimulation(input);

    expect(first).toEqual(second);
    expect(first.checksum_payload).toBe(second.checksum_payload);
    expect(first.golden_checksum).toBe(second.golden_checksum);
    expect(first.engine_version).toBe("v1");
    expect(first.schema_version).toBe(schema.schema_version);
  });

  it("emits non-physical warning when non-physical knobs differ from defaults", () => {
    const schema = loadSchema();
    const baseScenario = getScenarioRegistry().find((scenario) => scenario.scenario_id === "default.v1");
    expect(baseScenario).toBeTruthy();

    const input = buildInputFromValues({
      schema,
      scenarioId: "non-physical-test",
      seed: "warning-seed",
      params: {
        ...withParameterDefaults(schema, baseScenario!.params),
        narrative_leverage_multiplier: 1.2,
      },
      clock: withClockDefaults(schema, baseScenario!.clock),
    });

    const output = runSimulation(input);
    expect(output.warnings).toContain(NON_PHYSICAL_WARNING);
  });

  it("rejects unknown scenario fields during validation", () => {
    const schema = loadSchema();
    const defaultScenario = getScenarioRegistry().find((scenario) => scenario.scenario_id === "default.v1")!;

    const invalidScenario = {
      ...defaultScenario,
      params: {
        ...defaultScenario.params,
        unknown_knob: 1,
      },
    } as unknown as SimScenario;

    const errors = validateScenario(invalidScenario, schema);
    expect(errors.some((error) => error.includes("unknown field 'unknown_knob'"))).toBe(true);
  });

  it("does not use Math.random or Date.now in simulation core", () => {
    const currentFileDir = path.dirname(fileURLToPath(import.meta.url));
    const coreDir = path.resolve(currentFileDir, "../../sim/core");
    const files = readdirSync(coreDir).filter((file) => file.endsWith(".ts"));

    for (const file of files) {
      const content = readFileSync(path.join(coreDir, file), "utf8");
      expect(content).not.toMatch(/\bMath\.random\s*\(/);
      expect(content).not.toMatch(/\bDate\.now\s*\(/);
    }
  });
});
