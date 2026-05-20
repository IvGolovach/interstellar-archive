import type {
  NumericFieldSpec,
  SimScenario,
  SimSchema,
} from "../../../sim/public/types";
import { withClockDefaults, withParameterDefaults } from "./schema_defaults";
import { getScenarioRegistry, loadSchema } from "./schema_registry";

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validateFieldSpec(fieldPath: string, spec: unknown, errors: string[]): void {
  if (!isObject(spec)) {
    errors.push(`${fieldPath}: must be an object.`);
    return;
  }

  const type = spec.type;
  if (type !== "number") {
    errors.push(`${fieldPath}.type must be 'number'.`);
  }

  for (const numericKey of ["minimum", "maximum", "default"]) {
    const value = spec[numericKey];
    if (typeof value !== "number" || !Number.isFinite(value)) {
      errors.push(`${fieldPath}.${numericKey} must be a finite number.`);
    }
  }

  if (typeof spec.unit !== "string" || !spec.unit.trim()) {
    errors.push(`${fieldPath}.unit must be a non-empty string.`);
  }

  if (!["safe", "advanced", "non_physical"].includes(String(spec.category))) {
    errors.push(`${fieldPath}.category must be safe|advanced|non_physical.`);
  }

  if (typeof spec.help !== "string" || !spec.help.trim()) {
    errors.push(`${fieldPath}.help must be a non-empty string.`);
  }

  if (spec.warning !== undefined && (typeof spec.warning !== "string" || !spec.warning.trim())) {
    errors.push(`${fieldPath}.warning must be a non-empty string when provided.`);
  }

  if (
    typeof spec.minimum === "number" &&
    typeof spec.maximum === "number" &&
    typeof spec.default === "number" &&
    !(spec.minimum <= spec.default && spec.default <= spec.maximum)
  ) {
    errors.push(`${fieldPath}.default must be inside [minimum, maximum].`);
  }
}

function validateNumericMap(
  map: unknown,
  specs: Record<string, NumericFieldSpec>,
  label: string,
  errors: string[],
): void {
  if (!isObject(map)) {
    errors.push(`${label} must be an object.`);
    return;
  }

  for (const key of Object.keys(map)) {
    if (!(key in specs)) {
      errors.push(`${label} has unknown field '${key}'.`);
      continue;
    }

    const value = map[key];
    const spec = specs[key];
    if (typeof value !== "number" || !Number.isFinite(value)) {
      errors.push(`${label}.${key} must be a finite number.`);
      continue;
    }
    if (value < spec.minimum || value > spec.maximum) {
      errors.push(
        `${label}.${key} out of range: ${value} not in [${spec.minimum}, ${spec.maximum}].`,
      );
    }
  }
}

export function validateSchema(schema: SimSchema): string[] {
  const errors: string[] = [];
  if (typeof schema.schema_version !== "string" || !schema.schema_version.trim()) {
    errors.push("schema_version must be a non-empty string.");
  }
  if (typeof schema.artifact_schema_version !== "string" || !schema.artifact_schema_version.trim()) {
    errors.push("artifact_schema_version must be a non-empty string.");
  }
  if (typeof schema.breaking_change_flag !== "boolean") {
    errors.push("breaking_change_flag must be a boolean.");
  }
  if (!isObject(schema.parameters)) {
    errors.push("parameters must be an object.");
  }
  if (!isObject(schema.clock)) {
    errors.push("clock must be an object.");
  }
  if (!Array.isArray(schema.required_parameters) || schema.required_parameters.length === 0) {
    errors.push("required_parameters must be a non-empty array.");
  }
  if (!Array.isArray(schema.required_clock) || schema.required_clock.length === 0) {
    errors.push("required_clock must be a non-empty array.");
  }

  for (const [fieldId, spec] of Object.entries(schema.parameters ?? {})) {
    validateFieldSpec(`parameters.${fieldId}`, spec, errors);
  }

  for (const [fieldId, spec] of Object.entries(schema.clock ?? {})) {
    validateFieldSpec(`clock.${fieldId}`, spec, errors);
  }

  for (const requiredField of schema.required_parameters ?? []) {
    if (!(requiredField in (schema.parameters ?? {}))) {
      errors.push(`required_parameters contains unknown field '${requiredField}'.`);
    }
  }

  for (const requiredField of schema.required_clock ?? []) {
    if (!(requiredField in (schema.clock ?? {}))) {
      errors.push(`required_clock contains unknown field '${requiredField}'.`);
    }
  }

  return errors;
}

export function validateScenario(scenario: SimScenario, schema: SimSchema): string[] {
  const errors: string[] = [];
  const allowedTopLevel = new Set(["schema_version", "scenario_id", "seed", "params", "clock", "notes"]);

  const raw = scenario as unknown as Record<string, unknown>;
  for (const key of Object.keys(raw)) {
    if (!allowedTopLevel.has(key)) {
      errors.push(`scenario '${scenario.scenario_id}' has unknown top-level field '${key}'.`);
    }
  }

  if (scenario.schema_version !== schema.schema_version) {
    errors.push(
      `scenario '${scenario.scenario_id}' schema_version '${scenario.schema_version}' != '${schema.schema_version}'.`,
    );
  }

  if (typeof scenario.scenario_id !== "string" || !scenario.scenario_id.trim()) {
    errors.push("scenario_id must be a non-empty string.");
  }

  if (typeof scenario.seed !== "string" || !scenario.seed.trim()) {
    errors.push(`scenario '${scenario.scenario_id}' seed must be a non-empty string.`);
  }

  if (typeof scenario.notes !== "string" || !scenario.notes.trim()) {
    errors.push(`scenario '${scenario.scenario_id}' notes must be a non-empty string.`);
  }

  validateNumericMap(
    scenario.params,
    schema.parameters,
    `scenario '${scenario.scenario_id}' params`,
    errors,
  );
  validateNumericMap(
    scenario.clock,
    schema.clock,
    `scenario '${scenario.scenario_id}' clock`,
    errors,
  );

  const mergedParams = withParameterDefaults(schema, scenario.params);
  const mergedClock = withClockDefaults(schema, scenario.clock);

  for (const requiredField of schema.required_parameters) {
    if (!(requiredField in mergedParams)) {
      errors.push(`scenario '${scenario.scenario_id}' missing required param '${requiredField}'.`);
    }
  }

  for (const requiredField of schema.required_clock) {
    if (!(requiredField in mergedClock)) {
      errors.push(`scenario '${scenario.scenario_id}' missing required clock '${requiredField}'.`);
    }
  }

  return errors;
}

export function validateAllSchemaAndScenarios(): string[] {
  const schema = loadSchema();
  const errors = validateSchema(schema);
  for (const scenario of getScenarioRegistry()) {
    errors.push(...validateScenario(scenario, schema));
  }
  return errors;
}
