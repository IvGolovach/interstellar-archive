import { execSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { buildInputFromValues, getScenarioRegistry, loadSchema, validateAllSchemaAndScenarios } from "../src/lib/schema_loader";
import { runSimulation } from "../src/lib/sim_runner";

function utcStamp(date: Date): string {
  const pad = (value: number): string => String(value).padStart(2, "0");
  return `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(date.getUTCDate())}T${pad(date.getUTCHours())}${pad(
    date.getUTCMinutes(),
  )}${pad(date.getUTCSeconds())}Z`;
}

function readArg(name: string): string | null {
  const idx = process.argv.indexOf(name);
  if (idx === -1 || idx === process.argv.length - 1) {
    return null;
  }
  return process.argv[idx + 1];
}

function gitShortSha(repoRoot: string): string {
  try {
    return execSync("git rev-parse --short HEAD", { cwd: repoRoot, encoding: "utf8" }).trim();
  } catch {
    return "unknown";
  }
}

function main(): void {
  const errors = validateAllSchemaAndScenarios();
  if (errors.length > 0) {
    console.error(`FAIL: schema/scenario validation (${errors.length} errors)`);
    for (const error of errors) {
      console.error(`- ${error}`);
    }
    process.exit(1);
  }

  const scenarioId = readArg("--scenario") ?? "default.v1";
  const schema = loadSchema();
  const scenario = getScenarioRegistry().find((entry) => entry.scenario_id === scenarioId);
  if (!scenario) {
    console.error(`FAIL: unknown scenario '${scenarioId}'.`);
    process.exit(1);
  }

  const input = buildInputFromValues({
    schema,
    scenarioId: scenario.scenario_id,
    seed: scenario.seed,
    params: scenario.params as Record<string, number>,
    clock: scenario.clock as Record<string, number>,
  });

  const output = runSimulation(input);
  const checksum = output.golden_checksum;

  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(scriptDir, "../..");
  const runId = `${utcStamp(new Date())}-${gitShortSha(repoRoot)}`;
  const outputDir = path.resolve(repoRoot, "ops/reports/web-sim-runs", runId);
  mkdirSync(outputDir, { recursive: true });

  writeFileSync(path.join(outputDir, "input.json"), `${JSON.stringify(input, null, 2)}\n`, "utf8");
  writeFileSync(path.join(outputDir, "output.json"), `${JSON.stringify(output, null, 2)}\n`, "utf8");
  writeFileSync(path.join(outputDir, "checksum.txt"), `${checksum}\n`, "utf8");
  writeFileSync(
    path.join(outputDir, "environment.txt"),
    [
      `node_version=${process.version}`,
      `platform=${process.platform}`,
      `arch=${process.arch}`,
      `scenario_id=${scenario.scenario_id}`,
      `schema_version=${schema.schema_version}`,
      `head_sha=${gitShortSha(repoRoot)}`,
    ].join("\n") + "\n",
    "utf8",
  );

  console.log(`PASS: local artifact written to ${outputDir}`);
  console.log(`CHECKSUM: ${checksum}`);
}

main();
