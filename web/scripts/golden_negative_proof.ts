import { execSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

function main(): void {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(scriptDir, "../..");
  const webRoot = path.resolve(repoRoot, "web");
  const goldenOutputPath = path.resolve(repoRoot, "sim/golden/golden_output.v1.json");
  const reportPath = path.resolve(repoRoot, "ops/reports/golden-negative-proof.md");

  const original = readFileSync(goldenOutputPath, "utf8");
  const parsed = JSON.parse(original) as Record<string, any>;

  if (!parsed.derived_metrics || typeof parsed.derived_metrics !== "object") {
    throw new Error("golden output missing derived_metrics.");
  }

  const originalMetric = Number(parsed.derived_metrics.expected_mm_tail_hits);
  parsed.derived_metrics.expected_mm_tail_hits = Number((originalMetric + 0.000001).toFixed(6));
  const corrupted = `${JSON.stringify(parsed, null, 2)}\n`;

  mkdirSync(path.dirname(reportPath), { recursive: true });

  try {
    writeFileSync(goldenOutputPath, corrupted, "utf8");

    let failedAsExpected = false;
    let checkOutput = "";
    try {
      execSync("node --import tsx scripts/golden_check.ts", {
        cwd: webRoot,
        encoding: "utf8",
        stdio: "pipe",
      });
    } catch (error) {
      failedAsExpected = true;
      const stderr = (error as { stderr?: string }).stderr ?? "";
      const stdout = (error as { stdout?: string }).stdout ?? "";
      checkOutput = `${stdout}\n${stderr}`;
    }

    if (!failedAsExpected) {
      writeFileSync(
        reportPath,
        "# Golden Negative Proof\n\nFAIL: golden check did not fail after controlled corruption.\n",
        "utf8",
      );
      console.error("FAIL: golden check unexpectedly passed during negative-proof run.");
      process.exit(1);
    }

    if (!/golden checksum mismatch|golden output JSON drift detected/i.test(checkOutput)) {
      writeFileSync(
        reportPath,
        `# Golden Negative Proof\n\nFAIL: corruption triggered failure, but mismatch signal was unclear.\n\nOutput:\n\n\`\`\`\n${checkOutput}\n\`\`\`\n`,
        "utf8",
      );
      console.error("FAIL: negative proof failed, mismatch signature not detected.");
      process.exit(1);
    }

    writeFileSync(
      reportPath,
      `# Golden Negative Proof\n\nPASS: controlled corruption was detected.\n\n- Modified metric: derived_metrics.expected_mm_tail_hits\n- Original value: ${originalMetric}\n- Corrupted value: ${parsed.derived_metrics.expected_mm_tail_hits}\n- Detection signal: checksum/drift mismatch\n`,
      "utf8",
    );
    console.log(`PASS: negative proof completed (${reportPath})`);
  } finally {
    writeFileSync(goldenOutputPath, original, "utf8");
  }
}

main();
