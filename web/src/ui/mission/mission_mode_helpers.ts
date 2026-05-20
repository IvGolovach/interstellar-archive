import type {
  NumericFieldSpec,
  SimScenario,
  SimSchema,
} from "../../../../sim/public/types";
import {
  withClockDefaults,
  withParameterDefaults,
} from "../../lib/schema_loader";
import type { MissionField } from "./mission_mode_contract";

function toParamsRecord(value: object): Record<string, number> {
  return value as Record<string, number>;
}

function toClockRecord(value: object): Record<string, number> {
  return value as Record<string, number>;
}

export function labelize(fieldId: string): string {
  return fieldId
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function inferStep(spec: NumericFieldSpec): number {
  const span = spec.maximum - spec.minimum;
  if (span <= 1) {
    return 0.001;
  }
  if (span <= 20) {
    return 0.01;
  }
  return 0.1;
}

export function formatScore(value: number | null): string {
  if (value === null || Number.isNaN(value) || !Number.isFinite(value)) {
    return "N/A";
  }
  return value.toFixed(6);
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(3)}%`;
}

export function sortFields(fields: MissionField[]): MissionField[] {
  return [...fields].sort((left, right) => {
    if (left.scope !== right.scope) {
      return left.scope < right.scope ? -1 : 1;
    }
    return left.id < right.id ? -1 : left.id > right.id ? 1 : 0;
  });
}

export function findScenario(scenarios: SimScenario[], scenarioId: string): SimScenario {
  const scenario = scenarios.find((candidate) => candidate.scenario_id === scenarioId);
  if (!scenario) {
    throw new Error(`Scenario '${scenarioId}' not found.`);
  }
  return scenario;
}

export function baselineParamsForScenario(schema: SimSchema, scenario: SimScenario): Record<string, number> {
  return toParamsRecord(withParameterDefaults(schema, scenario.params));
}

export function baselineClockForScenario(schema: SimSchema, scenario: SimScenario): Record<string, number> {
  return toClockRecord(withClockDefaults(schema, scenario.clock));
}
