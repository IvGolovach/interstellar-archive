import { describe, expect, it } from "vitest";

import {
  getScenarioRegistry,
  getSchemaFields,
  loadSchema,
  validateAllSchemaAndScenarios,
} from "../src/lib/schema_loader";

describe("schema loader contract", () => {
  it("exposes schema, scenarios, and flattened fields through the barrel", () => {
    const schema = loadSchema();
    const scenarios = getScenarioRegistry();
    const fields = getSchemaFields(schema);

    expect(schema.schema_version).toBeTruthy();
    expect(scenarios.length).toBeGreaterThan(0);
    expect(fields.length).toBe(
      Object.keys(schema.parameters).length + Object.keys(schema.clock).length,
    );
    expect(fields.some((field) => field.scope === "params")).toBe(true);
    expect(fields.some((field) => field.scope === "clock")).toBe(true);
  });

  it("validates the committed schema and scenario registry without errors", () => {
    expect(validateAllSchemaAndScenarios()).toEqual([]);
  });
});
