import type {
  SimScenario,
  SimSchema,
} from "../../../sim/public/types";
import { simScenarioRegistry, simSchema } from "./sim_public_contracts";

const SCENARIO_REGISTRY = simScenarioRegistry;

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function loadSchema(): SimSchema {
  return clone(simSchema);
}

export function getScenarioRegistry(): SimScenario[] {
  return clone(SCENARIO_REGISTRY);
}
