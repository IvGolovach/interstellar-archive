import { getScenarioRegistry, loadSchema, validateScenario, validateSchema } from "../src/lib/schema_loader";

function main(): void {
  const schema = loadSchema();
  const errors: string[] = [];

  errors.push(...validateSchema(schema));
  for (const scenario of getScenarioRegistry()) {
    errors.push(...validateScenario(scenario, schema));
  }

  if (errors.length > 0) {
    console.error(`FAIL: schema/scenario validation (${errors.length} errors)`);
    for (const error of errors) {
      console.error(`- ${error}`);
    }
    process.exit(1);
  }

  console.log(`PASS: schema/scenario validation (${getScenarioRegistry().length} scenarios)`);
}

main();
