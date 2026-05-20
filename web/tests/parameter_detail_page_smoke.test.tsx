import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { DynamicTraceIndex } from "../src/lib/parameter_drilldown_loader";
import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import { ParameterDetailPage } from "../src/ui/drilldown/ParameterDetailPage";

const dataset = loadParameterDrilldownDataset();
const parameter = dataset.parameters[0];

if (!parameter) {
  throw new Error("Expected parameter drilldown dataset to include at least one parameter.");
}

const staticUsageEntry = dataset.staticUsageGraph[parameter.parameter_id];
const evidenceEntry = dataset.evidenceIndex[parameter.parameter_id];

if (!staticUsageEntry || !evidenceEntry) {
  throw new Error(`Expected drilldown support entries for ${parameter.parameter_id}.`);
}

function buildDynamicTrace(): DynamicTraceIndex {
  return {
    run_id: "fixture-run",
    commit_sha: "abc1234",
    mode: "realistic",
    seed: 1,
    scenario_path: "fixture/scenario.json",
    artifact_hash: "0".repeat(64),
    hashchain_verified: true,
    events: [
      {
        mode: "realistic",
        node_id: "node-1",
        module_id: staticUsageEntry.modules[0] ?? "module.unknown",
        inputs_hash: "1".repeat(64),
        outputs_hash: "2".repeat(64),
        failure_mode: null,
        dominant_driver_parameter_ids: [parameter.parameter_id],
      },
    ],
  };
}

describe("parameter detail page UI smoke", () => {
  it("renders contract, evidence, scientific basis, and dynamic sections deterministically", () => {
    const html = renderToStaticMarkup(
      <ParameterDetailPage
        parameter={parameter}
        evidenceEntry={evidenceEntry}
        staticUsageEntry={staticUsageEntry}
        pSuccessDefensibility={dataset.pSuccessDefensibility}
        failureSurfaceBaseline={dataset.failureSurfaceBaseline}
        objectiveContract={dataset.objectiveContract}
        objectiveScoreBaseline={dataset.objectiveScoreBaseline}
        optimizationFrontier={dataset.optimizationFrontier}
        onBack={vi.fn()}
        devLocalEnabled
        dynamicTrace={buildDynamicTrace()}
        dynamicValidation={{
          status: "PASS",
          event_count: 1,
          checked_parameter_module_pairs: 1,
          violation_count: 0,
          violations: [],
          errors: [],
        }}
        dynamicTraceLoadError={null}
        onLoadDynamicTraceFile={vi.fn(async () => undefined)}
      />,
    );

    expect(html).toContain("Parameter Detail");
    expect(html).toContain(parameter.parameter_id);
    expect(html).toContain("1. Definition (contract view)");
    expect(html).toContain("2. Static Usage (contract)");
    expect(html).toContain("3. Evidence &amp; Assumption Chain");
    expect(html).toContain("Basis &amp; Provenance");
    expect(html).toContain("Dynamic Usage (dev-local)");
    expect(html).toContain("Run header");
    expect(html).toContain("Dynamic events for parameter");
  });

  it("renders missing-parameter fallback deterministically", () => {
    const html = renderToStaticMarkup(
      <ParameterDetailPage
        parameter={null}
        evidenceEntry={null}
        staticUsageEntry={null}
        pSuccessDefensibility={dataset.pSuccessDefensibility}
        failureSurfaceBaseline={dataset.failureSurfaceBaseline}
        objectiveContract={dataset.objectiveContract}
        objectiveScoreBaseline={dataset.objectiveScoreBaseline}
        optimizationFrontier={dataset.optimizationFrontier}
        onBack={vi.fn()}
        devLocalEnabled={false}
        dynamicTrace={null}
        dynamicValidation={null}
        dynamicTraceLoadError={null}
        onLoadDynamicTraceFile={vi.fn(async () => undefined)}
      />,
    );

    expect(html).toContain("Parameter not found in manifest.");
    expect(html).toContain("Back to Parameter Index");
  });
});
