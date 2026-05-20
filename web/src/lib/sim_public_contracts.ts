import * as simContractsModule from "../../../sim/public/contracts";
import * as simTypesModule from "../../../sim/public/types";

import type { SimScenario, SimSchema } from "../../../sim/public/types";

type SimContractsExports = {
  simSchema: SimSchema;
  simScenarioRegistry: SimScenario[];
};

type SimTypesExports = {
  SIM_ENGINE_VERSION: string;
};

function resolveModuleExports<T>(
  module: Record<string, unknown>,
  predicate: (candidate: Record<string, unknown>) => boolean,
  errorMessage: string,
): T {
  const asAny = module as Record<string, any>;
  const candidates = [asAny, asAny.default, asAny["module.exports"]];

  for (const candidate of candidates) {
    if (!candidate) {
      continue;
    }
    if (predicate(candidate as Record<string, unknown>)) {
      return candidate as T;
    }
  }

  throw new Error(errorMessage);
}

const simContracts = resolveModuleExports<SimContractsExports>(
  simContractsModule as unknown as Record<string, unknown>,
  (candidate) =>
    typeof candidate.simSchema === "object" &&
    candidate.simSchema !== null &&
    Array.isArray(candidate.simScenarioRegistry),
  "Unable to resolve sim/public/contracts exports.",
);

const simTypes = resolveModuleExports<SimTypesExports>(
  simTypesModule as unknown as Record<string, unknown>,
  (candidate) => typeof candidate.SIM_ENGINE_VERSION === "string",
  "Unable to resolve sim/public/types exports.",
);

export const simSchema = simContracts.simSchema;
export const simScenarioRegistry = simContracts.simScenarioRegistry;
export const SIM_ENGINE_VERSION = simTypes.SIM_ENGINE_VERSION;
