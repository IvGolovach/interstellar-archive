import defaultScenarioJson from "../scenarios/default.v1.json";
import extremeScenarioJson from "../scenarios/extreme.v1.json";
import optimisticScenarioJson from "../scenarios/optimistic.v1.json";
import pessimisticScenarioJson from "../scenarios/pessimistic.v1.json";
import schemaJson from "../schema/sim_schema.v1.json";

import type { SimScenario, SimSchema } from "./types";

export const simSchema = schemaJson as SimSchema;

export const simScenarioRegistry = [
  defaultScenarioJson,
  optimisticScenarioJson,
  pessimisticScenarioJson,
  extremeScenarioJson,
] as SimScenario[];
