import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { buildInputFromValues, getScenarioRegistry, loadSchema, validateAllSchemaAndScenarios } from "../src/lib/schema_loader";
import { canonicalStringify } from "../src/lib/serialize";
import { runSimulation } from "../src/lib/sim_runner";

function sha256Hex(value: string): string {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

function fail(message: string): never {
  console.error(`FAIL: ${message}`);
  process.exit(1);
}

function main(): void {
  const update = process.argv.includes("--update");
  const validationErrors = validateAllSchemaAndScenarios();
  if (validationErrors.length > 0) {
    fail(`schema/scenario validation failed before golden check: ${validationErrors.join(" | ")}`);
  }

  const schema = loadSchema();
  const scenarios = getScenarioRegistry();
  const defaultScenario = scenarios.find((scenario) => scenario.scenario_id === "default.v1");
  if (!defaultScenario) {
    fail("default.v1 scenario not found.");
  }

  const input = buildInputFromValues({
    schema,
    scenarioId: defaultScenario.scenario_id,
    seed: defaultScenario.seed,
    params: defaultScenario.params as Record<string, number>,
    clock: defaultScenario.clock as Record<string, number>,
  });

  const output = runSimulation(input);
  const rerun = runSimulation(input);
  if (canonicalStringify(output) !== canonicalStringify(rerun)) {
    fail("simulation output is not deterministic for repeated identical input.");
  }

  const checksum = sha256Hex(output.checksum_payload);
  if (output.golden_checksum !== checksum) {
    fail(
      `output golden_checksum mismatch. output=${output.golden_checksum} recomputed=${checksum}.`,
    );
  }

  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(scriptDir, "../..");
  const goldenOutputPath = path.resolve(repoRoot, "sim/golden/golden_output.v1.json");
  const goldenChecksumPath = path.resolve(repoRoot, "sim/golden/golden_checksum.txt");

  if (update) {
    writeFileSync(goldenOutputPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");
    writeFileSync(goldenChecksumPath, `${output.golden_checksum}\n`, "utf8");
    console.log(`UPDATED: ${goldenOutputPath}`);
    console.log(`UPDATED: ${goldenChecksumPath}`);
    console.log(`CHECKSUM: ${output.golden_checksum}`);
    return;
  }

  let expectedChecksum = "";
  try {
    expectedChecksum = readFileSync(goldenChecksumPath, "utf8").trim();
  } catch {
    fail(`missing ${goldenChecksumPath}; run npm run golden:update.`);
  }

  if (output.golden_checksum !== expectedChecksum) {
    fail(
      `golden checksum mismatch. expected=${expectedChecksum} actual=${output.golden_checksum}. Bump schema_version and update golden intentionally.`,
    );
  }

  let expectedOutputRaw = "";
  try {
    expectedOutputRaw = readFileSync(goldenOutputPath, "utf8");
  } catch {
    fail(`missing ${goldenOutputPath}; run npm run golden:update.`);
  }

  const expectedOutput = JSON.parse(expectedOutputRaw) as unknown;
  if (canonicalStringify(expectedOutput) !== canonicalStringify(output)) {
    fail("golden output JSON drift detected despite matching checksum file.");
  }

  console.log(`PASS: golden checksum stable (${output.golden_checksum})`);
}

main();
