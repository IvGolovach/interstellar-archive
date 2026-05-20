import type { SimInput, SimOutput } from "../../../sim/public/types";
import * as simRunModule from "../../../sim/public/runtime";

type SimRunExports = {
  runSimulation: (input: SimInput) => SimOutput;
  NON_PHYSICAL_WARNING: string;
};

function resolveSimRunExports(module: Record<string, unknown>): SimRunExports {
  const asAny = module as Record<string, any>;
  const candidates = [asAny, asAny.default, asAny["module.exports"]];

  for (const candidate of candidates) {
    if (!candidate) {
      continue;
    }
    if (typeof candidate.runSimulation === "function" && typeof candidate.NON_PHYSICAL_WARNING === "string") {
      return candidate as SimRunExports;
    }
  }

  throw new Error("Unable to resolve runSimulation export from sim/public/runtime.");
}

const simRun = resolveSimRunExports(simRunModule as unknown as Record<string, unknown>);

export const runSimulation = simRun.runSimulation;
export const NON_PHYSICAL_WARNING = simRun.NON_PHYSICAL_WARNING;
