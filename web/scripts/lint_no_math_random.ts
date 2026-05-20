import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

function collectTsFiles(root: string): string[] {
  const files: string[] = [];

  function walk(current: string): void {
    const entries = readdirSync(current);
    for (const entry of entries) {
      const fullPath = path.join(current, entry);
      const stats = statSync(fullPath);
      if (stats.isDirectory()) {
        walk(fullPath);
        continue;
      }
      if (entry.endsWith(".ts") || entry.endsWith(".tsx")) {
        files.push(fullPath);
      }
    }
  }

  walk(root);
  return files;
}

function main(): void {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(scriptDir, "../..");
  const simCoreDir = path.resolve(repoRoot, "sim/core");

  const offenders: string[] = [];
  for (const filePath of collectTsFiles(simCoreDir)) {
    const content = readFileSync(filePath, "utf8");
    if (/\bMath\.random\s*\(/.test(content) || /\bDate\.now\s*\(/.test(content)) {
      offenders.push(path.relative(repoRoot, filePath));
    }
  }

  if (offenders.length > 0) {
    console.error("FAIL: forbidden non-deterministic APIs used in sim/core:");
    for (const offender of offenders) {
      console.error(`- ${offender}`);
    }
    process.exit(1);
  }

  console.log("PASS: no Math.random/Date.now usage in sim/core");
}

main();
