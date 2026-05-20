import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const DISALLOWED_SPECIFIER_FRAGMENTS = ["sim/core", "sim/schema", "sim/scenarios"];

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

describe("simulation public boundary", () => {
  it("forbids direct web imports from sim internals", () => {
    const testsDir = path.dirname(fileURLToPath(import.meta.url));
    const webRoot = path.resolve(testsDir, "..");
    const files = [
      ...collectSourceFiles(path.join(webRoot, "src")),
      ...collectSourceFiles(path.join(webRoot, "tests")),
    ];
    const violations: string[] = [];

    for (const file of files) {
      const source = readFileSync(file, "utf8");
      for (const specifier of collectImportSpecifiers(source)) {
        if (DISALLOWED_SPECIFIER_FRAGMENTS.some((fragment) => specifier.includes(fragment))) {
          violations.push(`${path.relative(webRoot, file)} -> ${specifier}`);
        }
      }
    }

    expect(violations).toEqual([]);
  });
});
