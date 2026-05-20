import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

describe("randomness lock", () => {
  it("forbids Math.random and Date.now usage in sim/core", () => {
    const testDir = path.dirname(fileURLToPath(import.meta.url));
    const coreDir = path.resolve(testDir, "../../sim/core");
    const coreFiles = readdirSync(coreDir).filter((file) => file.endsWith(".ts"));

    for (const file of coreFiles) {
      const content = readFileSync(path.join(coreDir, file), "utf8");
      expect(content).not.toMatch(/\bMath\.random\s*\(/);
      expect(content).not.toMatch(/\bDate\.now\s*\(/);
    }
  });
});
