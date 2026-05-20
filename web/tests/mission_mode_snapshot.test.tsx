import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { NumericFieldSpec } from "../../sim/public/types";
import { runSimulation } from "../src/lib/sim_runner";
import {
  buildInputFromValues,
  getScenarioRegistry,
  loadSchema,
  withClockDefaults,
  withParameterDefaults,
} from "../src/lib/schema_loader";
import { MissionMode } from "../src/ui/mission/MissionMode";
import { isSpeculativeWarningActive } from "../src/ui/mission/mission_mode_model";

function firstEngineeringField(
  specs: Record<string, NumericFieldSpec>,
): { id: string; spec: NumericFieldSpec } {
  const entry = Object.entries(specs).find(
    ([, spec]) => spec.category === "safe" || spec.category === "advanced",
  );
  if (!entry) {
    throw new Error("No engineering field found in schema.");
  }
  return { id: entry[0], spec: entry[1] };
}

function firstSpeculativeField(
  specs: Record<string, NumericFieldSpec>,
): { id: string; spec: NumericFieldSpec } {
  const entry = Object.entries(specs).find(([, spec]) => spec.category === "non_physical");
  if (!entry) {
    throw new Error("No speculative field found in schema.");
  }
  return { id: entry[0], spec: entry[1] };
}

function shiftedValue(spec: NumericFieldSpec): number {
  const candidate = spec.default + (spec.maximum - spec.minimum) * 0.1;
  if (candidate <= spec.maximum) {
    return candidate;
  }
  return spec.default - (spec.maximum - spec.minimum) * 0.1;
}

describe("mission mode UX", () => {
  it("renders mission mode single-screen layout deterministically", () => {
    const html = renderToStaticMarkup(<MissionMode />);

    expect(html).toContain("Mission Mode");
    expect(html).toContain("🚀 Run Mission");
    expect(html).toContain("Mission Stage Timeline (S0-S3)");
    expect(html).toContain("🔒 Physics (Read-only)");
    expect(html).toContain("🧱 Engineering (Editable)");
    expect(html).toContain("🧪 Speculative (Editable)");
    expect(html).toMatchSnapshot();
  });

  it("keeps output deterministic across repeated run command for same edited engineering input", () => {
    const schema = loadSchema();
    const scenario = getScenarioRegistry()[0];
    const params = withParameterDefaults(schema, scenario.params);
    const clock = withClockDefaults(schema, scenario.clock);
    const engineeringField = firstEngineeringField(schema.parameters);
    params[engineeringField.id] = shiftedValue(engineeringField.spec);

    const input = buildInputFromValues({
      schema,
      scenarioId: scenario.scenario_id,
      seed: scenario.seed,
      params,
      clock,
    });

    const first = runSimulation(input);
    const second = runSimulation(input);

    expect(first).toEqual(second);
    expect(first.checksum_payload).toBe(second.checksum_payload);
  });

  it("activates speculative warning when a speculative knob differs from baseline", () => {
    const schema = loadSchema();
    const scenario = getScenarioRegistry()[0];
    const params = withParameterDefaults(schema, scenario.params);
    const speculativeField = firstSpeculativeField(schema.parameters);

    expect(isSpeculativeWarningActive(schema, params)).toBe(false);

    params[speculativeField.id] = shiftedValue(speculativeField.spec);
    expect(isSpeculativeWarningActive(schema, params)).toBe(true);
  });
});
