import type {
  ClockConfig,
  NumericFieldSpec,
  SimInput,
  SimParams,
  SimSchema,
} from "../../../sim/public/types";

export type FieldScope = "params" | "clock";

export interface SchemaField extends NumericFieldSpec {
  id: string;
  scope: FieldScope;
}

type NumericMap = Record<string, number>;

function defaultsFromSpecs(specs: Record<string, NumericFieldSpec>): NumericMap {
  const defaults: NumericMap = {};
  for (const [fieldId, spec] of Object.entries(specs)) {
    defaults[fieldId] = spec.default;
  }
  return defaults;
}

export function withParameterDefaults(schema: SimSchema, overrides: Partial<SimParams>): SimParams {
  return {
    ...(defaultsFromSpecs(schema.parameters) as SimParams),
    ...overrides,
  };
}

export function withClockDefaults(schema: SimSchema, overrides: Partial<ClockConfig>): ClockConfig {
  return {
    ...(defaultsFromSpecs(schema.clock) as ClockConfig),
    ...overrides,
  };
}

export function getSchemaFields(schema: SimSchema): SchemaField[] {
  const fields: SchemaField[] = [];
  for (const [id, spec] of Object.entries(schema.parameters)) {
    fields.push({ id, scope: "params", ...spec });
  }
  for (const [id, spec] of Object.entries(schema.clock)) {
    fields.push({ id, scope: "clock", ...spec });
  }
  return fields;
}

export function buildInputFromValues(args: {
  schema: SimSchema;
  scenarioId: string;
  seed: string;
  params: NumericMap;
  clock: NumericMap;
}): SimInput {
  const { schema, scenarioId, seed, params, clock } = args;
  const mergedParams = withParameterDefaults(schema, params as Partial<SimParams>);
  const mergedClock = withClockDefaults(schema, clock as Partial<ClockConfig>);

  for (const requiredField of schema.required_parameters) {
    if (!(requiredField in mergedParams)) {
      throw new Error(`Missing required param '${requiredField}'.`);
    }
  }

  for (const requiredField of schema.required_clock) {
    if (!(requiredField in mergedClock)) {
      throw new Error(`Missing required clock field '${requiredField}'.`);
    }
  }

  return {
    schema_version: schema.schema_version,
    scenario_id: scenarioId,
    seed,
    params: mergedParams,
    clock: mergedClock,
    units: schema.units,
  };
}

export function nonPhysicalDifferences(params: NumericMap, schema: SimSchema): string[] {
  const changed: string[] = [];
  for (const [fieldId, spec] of Object.entries(schema.parameters)) {
    if (spec.category !== "non_physical") {
      continue;
    }
    if (params[fieldId] !== spec.default) {
      changed.push(fieldId);
    }
  }
  return changed;
}
