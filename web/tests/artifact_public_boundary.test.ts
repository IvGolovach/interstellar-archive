import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const ALLOWED_ARTIFACT_IMPORTERS = new Set([
  "src/lib/artifact_public_contracts.ts",
  "src/lib/capsule_risk_budget_contract.ts",
]);

function collectSourceFiles(directory: string): string[] {
  const entries = readdirSync(directory, { withFileTypes: true });
  const files: string[] = [];

  for (const entry of entries) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectSourceFiles(entryPath));
      continue;
    }
    if (entry.isFile() && (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx"))) {
      files.push(entryPath);
    }
  }

  return files;
}

function collectImportSpecifiers(source: string): string[] {
  const specifiers: string[] = [];
  const pattern = /from\s+["']([^"']+)["']|import\s*\(\s*["']([^"']+)["']\s*\)/g;

  for (const match of source.matchAll(pattern)) {
    const specifier = match[1] ?? match[2];
    if (specifier) {
      specifiers.push(specifier);
    }
  }

  return specifiers;
}

describe("artifact public boundary", () => {
  it("forbids direct web imports from raw artifact paths outside the adapter", () => {
    const testsDir = path.dirname(fileURLToPath(import.meta.url));
    const webRoot = path.resolve(testsDir, "..");
    const files = [
      ...collectSourceFiles(path.join(webRoot, "src")),
      ...collectSourceFiles(path.join(webRoot, "tests")),
    ];
    const violations: string[] = [];

    for (const file of files) {
      const relativeFile = path.relative(webRoot, file).split(path.sep).join("/");
      const source = readFileSync(file, "utf8");
      for (const specifier of collectImportSpecifiers(source)) {
        if (!specifier.includes("artifacts/")) {
          continue;
        }
        if (ALLOWED_ARTIFACT_IMPORTERS.has(relativeFile)) {
          continue;
        }
        violations.push(`${relativeFile} -> ${specifier}`);
      }
    }

    expect(violations).toEqual([]);
  });
});
