import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

interface Offender {
  file: string;
  line: number;
  column: number;
  reason: string;
}

interface ManifestParameter {
  parameter_id: string;
}

interface ManifestPayload {
  parameters: ManifestParameter[];
}

const ALLOWED_TRUTH_ARTIFACT_IMPORTS = new Set<string>([
  "artifacts/parameter_drilldown_manifest.json",
  "artifacts/parameter_static_usage_graph.json",
  "artifacts/parameter_evidence_index.json",
  "artifacts/p_success_defensibility.json",
  "artifacts/failure_surface_baseline.v1.json",
  "artifacts/objective_score_baseline.v1.json",
  "artifacts/optimization_search_space.v1.json",
  "artifacts/optimization_frontier_realistic.v1.json",
]);

const ALLOWED_NON_TRUTH_ARTIFACT_IMPORTS = new Set<string>(["artifacts/determinism_status.json"]);
const FORBIDDEN_VISUALIZATION_COMPUTE_IDENTIFIERS = new Set<string>([
  "computePareto",
  "calculateRisk",
  "calculateRiskEnvelope",
]);

function isMissionFile(relativePath: string): boolean {
  return relativePath.startsWith("web/src/ui/mission/") || relativePath.startsWith("web/src/ui/mission_run/");
}

function toPosix(value: string): string {
  return value.split(path.sep).join("/");
}

function collectFiles(root: string): string[] {
  const files: string[] = [];

  function walk(current: string): void {
    for (const entry of readdirSync(current)) {
      const fullPath = path.join(current, entry);
      const stats = statSync(fullPath);
      if (stats.isDirectory()) {
        walk(fullPath);
        continue;
      }
      files.push(fullPath);
    }
  }

  walk(root);
  return files;
}

function collectTsFiles(root: string): string[] {
  return collectFiles(root).filter((filePath) => filePath.endsWith(".ts") || filePath.endsWith(".tsx"));
}

function collectJsonFiles(root: string): string[] {
  return collectFiles(root).filter((filePath) => filePath.endsWith(".json"));
}

function loadManifestParameterIds(repoRoot: string): Set<string> {
  const manifestPath = path.resolve(repoRoot, "artifacts/parameter_drilldown_manifest.json");
  const raw = readFileSync(manifestPath, "utf8");
  const payload = JSON.parse(raw) as ManifestPayload;
  const ids = new Set<string>();
  for (const parameter of payload.parameters ?? []) {
    if (typeof parameter.parameter_id === "string" && parameter.parameter_id.trim() !== "") {
      ids.add(parameter.parameter_id);
    }
  }
  return ids;
}

function sourcePos(source: ts.SourceFile, node: ts.Node): { line: number; column: number } {
  const { line, character } = source.getLineAndCharacterOfPosition(node.getStart(source));
  return { line: line + 1, column: character + 1 };
}

function resolveRelativeImportTarget(repoRoot: string, importerPath: string, specifier: string): string {
  const importerDir = path.dirname(importerPath);
  const resolvedBase = path.resolve(importerDir, specifier);
  const candidates = [resolvedBase];
  if (!path.extname(resolvedBase)) {
    candidates.push(`${resolvedBase}.json`, `${resolvedBase}.ts`, `${resolvedBase}.tsx`, `${resolvedBase}/index.ts`);
  }
  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return toPosix(path.relative(repoRoot, candidate));
    }
  }
  return toPosix(path.relative(repoRoot, resolvedBase));
}

function addOffender(
  offenders: Offender[],
  sourceFile: ts.SourceFile,
  node: ts.Node,
  file: string,
  reason: string,
): void {
  const { line, column } = sourcePos(sourceFile, node);
  offenders.push({ file, line, column, reason });
}

function checkImportSpecifier(
  args: {
    repoRoot: string;
    sourceFile: ts.SourceFile;
    importerPath: string;
    file: string;
    specifier: string;
    node: ts.Node;
    offenders: Offender[];
  },
): void {
  const { repoRoot, sourceFile, importerPath, file, specifier, node, offenders } = args;
  const normalizedSpecifier = specifier.replaceAll("\\", "/");
  if (
    normalizedSpecifier.includes("parameters/registry/") ||
    normalizedSpecifier.includes("mission/EVIDENCE_") ||
    normalizedSpecifier.includes("refs/")
  ) {
    addOffender(
      offenders,
      sourceFile,
      node,
      file,
      `forbidden import target '${normalizedSpecifier}' (registry/evidence/refs are blocked in UI)`,
    );
    return;
  }

  const isJsonImport = normalizedSpecifier.endsWith(".json");
  if (!isJsonImport) {
    return;
  }

  const resolvedImportPath = normalizedSpecifier.startsWith(".")
    ? resolveRelativeImportTarget(repoRoot, importerPath, normalizedSpecifier)
    : normalizedSpecifier;

  const looksLikeTruthJson =
    resolvedImportPath.includes("parameter_") ||
    resolvedImportPath.includes("evidence") ||
    resolvedImportPath.includes("registry") ||
    resolvedImportPath.includes("claim") ||
    resolvedImportPath.includes("source");

  if (!looksLikeTruthJson) {
    return;
  }

  if (!resolvedImportPath.startsWith("artifacts/")) {
    addOffender(
      offenders,
      sourceFile,
      node,
      file,
      `JSON import '${normalizedSpecifier}' resolves to '${resolvedImportPath}' outside artifacts/`,
    );
    return;
  }

  if (
    !ALLOWED_TRUTH_ARTIFACT_IMPORTS.has(resolvedImportPath) &&
    !ALLOWED_NON_TRUTH_ARTIFACT_IMPORTS.has(resolvedImportPath)
  ) {
    addOffender(
      offenders,
      sourceFile,
      node,
      file,
      `artifact JSON import '${resolvedImportPath}' is not in allowlist`,
    );
  }
}

function isAllowedLiteralContext(node: ts.Node): boolean {
  const parent = node.parent;
  if (!parent) {
    return false;
  }
  if (ts.isImportDeclaration(parent) || ts.isExportDeclaration(parent)) {
    return true;
  }
  if (ts.isCaseClause(parent)) {
    return true;
  }
  return false;
}

function isVisualizationFile(relativePath: string): boolean {
  return relativePath.startsWith("web/src/ui/visualization/");
}

function main(): void {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(scriptDir, "../..");
  const srcRoot = path.resolve(repoRoot, "web/src");
  const parameterIds = loadManifestParameterIds(repoRoot);

  const offenders: Offender[] = [];
  const jsonFilesInSrc = collectJsonFiles(srcRoot);
  for (const jsonPath of jsonFilesInSrc) {
    offenders.push({
      file: toPosix(path.relative(repoRoot, jsonPath)),
      line: 1,
      column: 1,
      reason: "local JSON file under web/src is forbidden (no registry/evidence copies in UI source)",
    });
  }

  for (const fullPath of collectTsFiles(srcRoot)) {
    const relativePath = toPosix(path.relative(repoRoot, fullPath));
    const content = readFileSync(fullPath, "utf8");
    const scriptKind = fullPath.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
    const sourceFile = ts.createSourceFile(fullPath, content, ts.ScriptTarget.ES2022, true, scriptKind);

    const visit = (node: ts.Node): void => {
      if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)) {
        if (isMissionFile(relativePath)) {
          const specifier = node.moduleSpecifier.text.replaceAll("\\", "/");
          if (specifier.endsWith(".json")) {
            addOffender(
              offenders,
              sourceFile,
              node.moduleSpecifier,
              relativePath,
              `mission UI must use artifact loaders only; direct JSON import '${specifier}' is forbidden`,
            );
          }
          if (specifier.includes("artifacts/")) {
            addOffender(
              offenders,
              sourceFile,
              node.moduleSpecifier,
              relativePath,
              `mission UI must not import artifacts directly ('${specifier}'); use loader abstractions`,
            );
          }
        }
        checkImportSpecifier({
          repoRoot,
          sourceFile,
          importerPath: fullPath,
          file: relativePath,
          specifier: node.moduleSpecifier.text,
          node: node.moduleSpecifier,
          offenders,
        });
      } else if (ts.isExportDeclaration(node) && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) {
        checkImportSpecifier({
          repoRoot,
          sourceFile,
          importerPath: fullPath,
          file: relativePath,
          specifier: node.moduleSpecifier.text,
          node: node.moduleSpecifier,
          offenders,
        });
      } else if (
        (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) &&
        parameterIds.has(node.text) &&
        !isAllowedLiteralContext(node)
      ) {
        addOffender(
          offenders,
          sourceFile,
          node,
          relativePath,
          `hardcoded parameter_id literal '${node.text}' detected outside artifact-rendering context`,
        );
      } else if (
        isMissionFile(relativePath) &&
        ts.isPropertyAccessExpression(node) &&
        ts.isIdentifier(node.expression) &&
        node.expression.text === "Math"
      ) {
        addOffender(
          offenders,
          sourceFile,
          node,
          relativePath,
          `physics/math compute is forbidden in mission UI layer (${node.getText(sourceFile)})`,
        );
      } else if (
        isVisualizationFile(relativePath) &&
        ts.isCallExpression(node) &&
        ts.isIdentifier(node.expression) &&
        FORBIDDEN_VISUALIZATION_COMPUTE_IDENTIFIERS.has(node.expression.text)
      ) {
        addOffender(
          offenders,
          sourceFile,
          node.expression,
          relativePath,
          `forbidden visualization compute call '${node.expression.text}' (UI must render artifact truth only)`,
        );
      } else if (
        isVisualizationFile(relativePath) &&
        ts.isFunctionDeclaration(node) &&
        node.name &&
        FORBIDDEN_VISUALIZATION_COMPUTE_IDENTIFIERS.has(node.name.text)
      ) {
        addOffender(
          offenders,
          sourceFile,
          node.name,
          relativePath,
          `forbidden visualization compute function '${node.name.text}' (risk/pareto compute belongs to builders)`,
        );
      } else if (
        isVisualizationFile(relativePath) &&
        ts.isVariableDeclaration(node) &&
        ts.isIdentifier(node.name) &&
        FORBIDDEN_VISUALIZATION_COMPUTE_IDENTIFIERS.has(node.name.text)
      ) {
        addOffender(
          offenders,
          sourceFile,
          node.name,
          relativePath,
          `forbidden visualization compute variable '${node.name.text}'`,
        );
      } else if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === "fetch") {
        const [firstArg] = node.arguments;
        if (firstArg && (ts.isStringLiteral(firstArg) || ts.isNoSubstitutionTemplateLiteral(firstArg))) {
          const target = firstArg.text;
          if (
            target.startsWith("http://") ||
            target.startsWith("https://") ||
            target.endsWith(".json") ||
            target.includes("parameter") ||
            target.includes("evidence")
          ) {
            addOffender(
              offenders,
              sourceFile,
              firstArg,
              relativePath,
              `runtime fetch '${target}' is forbidden for UI truth data`,
            );
          }
        }
      }
      ts.forEachChild(node, visit);
    };

    visit(sourceFile);
  }

  if (offenders.length > 0) {
    console.error(`FAIL: UI no-truth guard (${offenders.length} violations)`);
    for (const offender of offenders) {
      console.error(`- ${offender.file}:${offender.line}:${offender.column}: ${offender.reason}`);
    }
    process.exit(1);
  }

  console.log(
    `PASS: UI no-truth guard (files=${collectTsFiles(srcRoot).length}, parameter_ids=${parameterIds.size}, checks=imports+hardcoded+artifact-only+runtime-fetch+visualization-no-compute+mission-no-math)`,
  );
}

main();
