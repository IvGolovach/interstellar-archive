import { execSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

interface Violation {
  rule: string;
  details: string;
}

function parseArg(name: string): string | null {
  const index = process.argv.indexOf(name);
  if (index === -1 || index + 1 >= process.argv.length) {
    return null;
  }
  return process.argv[index + 1];
}

function runGit(repoRoot: string, args: string[]): string {
  return execSync(`git ${args.join(" ")}`, { cwd: repoRoot, encoding: "utf8" }).trim();
}

function changedFiles(repoRoot: string, base: string, head: string): string[] {
  const output = runGit(repoRoot, ["diff", "--name-only", `${base}..${head}`]);
  if (!output) {
    return [];
  }
  return output.split("\n").map((line) => line.trim()).filter(Boolean);
}

function fileAtRef(repoRoot: string, ref: string, filePath: string): string | null {
  try {
    return execSync(`git show ${ref}:${filePath}`, {
      cwd: repoRoot,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    });
  } catch {
    return null;
  }
}

function parseSchemaVersion(schemaRaw: string | null): string | null {
  if (!schemaRaw) {
    return null;
  }
  try {
    const parsed = JSON.parse(schemaRaw) as { schema_version?: string };
    return typeof parsed.schema_version === "string" ? parsed.schema_version : null;
  } catch {
    return null;
  }
}

function parseBreakingFlag(schemaRaw: string | null): boolean {
  if (!schemaRaw) {
    return false;
  }
  try {
    const parsed = JSON.parse(schemaRaw) as { breaking_change_flag?: boolean };
    return parsed.breaking_change_flag === true;
  } catch {
    return false;
  }
}

function parseVersionNumber(value: string | null): number {
  if (!value) {
    return 0;
  }
  const match = value.match(/(?:^|\.)v(\d+)$/);
  if (!match) {
    return 0;
  }
  return Number(match[1]);
}

function parseEngineVersion(typesRaw: string | null): string {
  if (!typesRaw) {
    return "v0";
  }
  const match = typesRaw.match(/SIM_ENGINE_VERSION\s*=\s*"(v\d+)"/);
  if (!match) {
    return "v0";
  }
  return match[1];
}

function loadJson(repoRoot: string, filePath: string): any {
  const fullPath = path.resolve(repoRoot, filePath);
  return JSON.parse(readFileSync(fullPath, "utf8"));
}

function requiredFieldsPresent(entry: Record<string, unknown>, fields: string[]): string[] {
  return fields.filter((field) => !(field in entry));
}

function writeViolationReport(repoRoot: string, base: string, head: string, violations: Violation[]): string {
  const reportPath = path.resolve(repoRoot, "ops/reports/golden-integrity-violation.md");
  mkdirSync(path.dirname(reportPath), { recursive: true });

  const lines = [
    "# Golden Integrity Violation",
    "",
    `Base: ${base}`,
    `Head: ${head}`,
    `Violations: ${violations.length}`,
    "",
  ];

  for (const violation of violations) {
    lines.push(`- Rule: ${violation.rule}`);
    lines.push(`  Details: ${violation.details}`);
  }

  writeFileSync(reportPath, `${lines.join("\n")}\n`, "utf8");
  return reportPath;
}

function main(): void {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(scriptDir, "../..");
  const head = parseArg("--head") ?? process.env.GITHUB_SHA ?? runGit(repoRoot, ["rev-parse", "HEAD"]);
  const base = parseArg("--base") ?? process.env.GITHUB_BASE_SHA ?? runGit(repoRoot, ["rev-parse", `${head}^`]);

  const changed = changedFiles(repoRoot, base, head);
  const changedSet = new Set(changed);

  const changelogPath = "engineering/CHANGELOG.md";
  const decisionsPath = "engineering/DECISIONS.md";
  const schemaPath = "sim/schema/sim_schema.v1.json";
  const typesPath = "sim/core/types.ts";
  const goldenChecksumPath = "sim/golden/golden_checksum.txt";
  const goldenOutputPath = "sim/golden/golden_output.v1.json";
  const baselinePath = "benchmarks/baseline_registry.json";

  const schemaHeadRaw = fileAtRef(repoRoot, head, schemaPath);
  const schemaBaseRaw = fileAtRef(repoRoot, base, schemaPath);
  const goldenBaseRaw = fileAtRef(repoRoot, base, goldenChecksumPath);
  const schemaHeadVersion = parseSchemaVersion(schemaHeadRaw);
  const schemaBaseVersion = parseSchemaVersion(schemaBaseRaw);
  const schemaBumped = parseVersionNumber(schemaHeadVersion) === parseVersionNumber(schemaBaseVersion) + 1;

  const engineHeadVersion = parseEngineVersion(fileAtRef(repoRoot, head, typesPath));
  const engineBaseVersion = parseEngineVersion(fileAtRef(repoRoot, base, typesPath));
  const engineBumped = parseVersionNumber(engineHeadVersion) === parseVersionNumber(engineBaseVersion) + 1;

  const goldenChecksumChanged = changedSet.has(goldenChecksumPath);
  const changelogChanged = changedSet.has(changelogPath);
  const decisionsChanged = changedSet.has(decisionsPath);
  const baselineChanged = changedSet.has(baselinePath);
  const breakingFlag = parseBreakingFlag(schemaHeadRaw);
  const initializesGoldenBaseline = goldenChecksumChanged && goldenBaseRaw === null;

  const violations: Violation[] = [];

  if (goldenChecksumChanged && !initializesGoldenBaseline) {
    if (!(schemaBumped || engineBumped || breakingFlag)) {
      violations.push({
        rule: "golden_requires_version_or_breaking_flag",
        details:
          "golden checksum changed without schema bump, engine bump, or breaking_change_flag=true.",
      });
    }
    if (!changelogChanged) {
      violations.push({
        rule: "golden_requires_changelog",
        details: "golden checksum changed but engineering/CHANGELOG.md was not updated.",
      });
    }
    if (!decisionsChanged) {
      violations.push({
        rule: "golden_requires_decisions",
        details: "golden checksum changed but engineering/DECISIONS.md was not updated.",
      });
    }
  }

  if (engineBumped && !goldenChecksumChanged) {
    violations.push({
      rule: "engine_bump_requires_golden_refresh",
      details: "SIM_ENGINE_VERSION changed without updating sim/golden/golden_checksum.txt.",
    });
  }

  if (schemaBumped && !goldenChecksumChanged) {
    violations.push({
      rule: "schema_bump_requires_golden_refresh",
      details: "schema_version changed without updating sim/golden/golden_checksum.txt.",
    });
  }

  if (breakingFlag) {
    if (!baselineChanged) {
      violations.push({
        rule: "breaking_change_requires_baseline_update",
        details: "breaking_change_flag=true requires benchmarks/baseline_registry.json update.",
      });
    }
    if (!changelogChanged) {
      violations.push({
        rule: "breaking_change_requires_changelog",
        details: "breaking_change_flag=true requires engineering/CHANGELOG.md update.",
      });
    }
    if (!decisionsChanged) {
      violations.push({
        rule: "breaking_change_requires_decisions",
        details: "breaking_change_flag=true requires engineering/DECISIONS.md update.",
      });
    }
  }

  const baseline = loadJson(repoRoot, baselinePath) as {
    entries?: Record<string, unknown>[];
  };
  const entries = Array.isArray(baseline.entries) ? baseline.entries : [];
  if (entries.length === 0) {
    violations.push({
      rule: "baseline_entries_required",
      details: "benchmarks/baseline_registry.json must contain non-empty entries list.",
    });
  }

  const requiredFields = [
    "baseline_id",
    "metric_name",
    "metric_value",
    "date",
    "engine_version",
    "schema_version",
    "golden_checksum",
    "timestamp_utc",
    "commit_sha",
  ];

  for (const entry of entries) {
    const missing = requiredFieldsPresent(entry, requiredFields);
    if (missing.length > 0) {
      violations.push({
        rule: "baseline_required_fields",
        details: `baseline entry missing fields: ${missing.join(", ")}`,
      });
    }
  }

  const goldenChecksum = readFileSync(path.resolve(repoRoot, goldenChecksumPath), "utf8").trim();
  const goldenOutput = loadJson(repoRoot, goldenOutputPath) as { golden_checksum?: string };
  if (goldenOutput.golden_checksum !== goldenChecksum) {
    violations.push({
      rule: "golden_output_checksum_sync",
      details: `golden_output.v1.json golden_checksum (${goldenOutput.golden_checksum}) does not match golden_checksum.txt (${goldenChecksum}).`,
    });
  }

  if (entries.length > 0) {
    const sorted = [...entries].sort((left, right) => {
      const leftTs = String(left.timestamp_utc ?? "");
      const rightTs = String(right.timestamp_utc ?? "");
      return leftTs.localeCompare(rightTs);
    });
    const latest = sorted[sorted.length - 1] as Record<string, unknown>;

    if (String(latest.golden_checksum ?? "") !== goldenChecksum) {
      violations.push({
        rule: "baseline_checksum_sync",
        details: `latest baseline golden_checksum (${latest.golden_checksum}) must match ${goldenChecksum}.`,
      });
    }

    if (String(latest.engine_version ?? "") !== engineHeadVersion) {
      violations.push({
        rule: "baseline_engine_version_sync",
        details: `latest baseline engine_version (${latest.engine_version}) must match ${engineHeadVersion}.`,
      });
    }

    if (String(latest.schema_version ?? "") !== schemaHeadVersion) {
      violations.push({
        rule: "baseline_schema_version_sync",
        details: `latest baseline schema_version (${latest.schema_version}) must match ${schemaHeadVersion}.`,
      });
    }

    if (baselineChanged || breakingFlag || goldenChecksumChanged) {
      const baselineCommit = String(latest.commit_sha ?? "");
      if (baselineCommit !== head && baselineCommit !== "HEAD") {
        violations.push({
          rule: "baseline_commit_head_sync",
          details: `latest baseline commit_sha (${baselineCommit}) must equal HEAD (${head}) or literal HEAD token.`,
        });
      }
    }
  }

  if (violations.length > 0) {
    const reportPath = writeViolationReport(repoRoot, base, head, violations);
    console.error(`FAIL: golden integrity contract violated (${violations.length} rules).`);
    console.error(`Report: ${reportPath}`);
    for (const violation of violations) {
      console.error(`- ${violation.rule}: ${violation.details}`);
    }
    process.exit(2);
  }

  console.log(`PASS: golden integrity contract checks passed (base=${base}, head=${head})`);
}

main();
