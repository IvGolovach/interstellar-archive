import { describe, expect, it } from "vitest";

import type { DynamicTraceIndex, ParameterManifestEntry } from "../src/lib/parameter_drilldown_loader";
import {
  dynamicEventsForParameter,
  formatParameterBounds,
  formatParameterDefault,
} from "../src/ui/drilldown/parameter_drilldown_helpers";

function buildParameter(partial?: Partial<ParameterManifestEntry>): ParameterManifestEntry {
  return {
    parameter_id: "alpha",
    default_value: 42,
    bounds: {
      minimum: 0,
      maximum: 100,
      is_fixed: false,
      has_bounds: true,
    },
    units: "arb",
    domain: "realistic",
    mode: "realistic",
    category: "safe",
    classification: "input",
    value_mode: "fixed",
    trust_grade: "A",
    affects_core_probability: true,
    modules_touched_count: 1,
    modules: ["mod.alpha"],
    paths_to_metrics: ["p_success"],
    evidence_source_ids: ["src-1"],
    evidence_status: { status: "OK", reason: null },
    has_uncertainty: true,
    has_source: true,
    defensibility_status: "PASS",
    has_dynamic_trace: true,
    static_usage_ref: "static#alpha",
    evidence_ref: "evidence#alpha",
    ...partial,
  };
}

describe("parameter drilldown helpers", () => {
  it("formats defaults and bounds consistently for index and detail views", () => {
    expect(formatParameterDefault(3.5)).toBe("3.5");
    expect(formatParameterDefault(true)).toBe("true");
    expect(formatParameterDefault(null)).toBe("N/A");
    expect(formatParameterBounds(buildParameter())).toBe("[0, 100]");
    expect(
      formatParameterBounds(
        buildParameter({
          bounds: { minimum: 5, maximum: 5, is_fixed: true, has_bounds: true },
        }),
      ),
    ).toBe("[5, 5] fixed");
  });

  it("filters dynamic events to the selected parameter only", () => {
    const trace: DynamicTraceIndex = {
      run_id: "run-1",
      commit_sha: "abc123",
      mode: "realistic",
      seed: 1,
      scenario_path: "fixture",
      artifact_hash: "0".repeat(64),
      hashchain_verified: true,
      events: [
        {
          mode: "realistic",
          node_id: "node-1",
          module_id: "module.alpha",
          inputs_hash: "1".repeat(64),
          outputs_hash: "2".repeat(64),
          failure_mode: null,
          dominant_driver_parameter_ids: ["alpha"],
        },
        {
          mode: "realistic",
          node_id: "node-2",
          module_id: "module.beta",
          inputs_hash: "3".repeat(64),
          outputs_hash: "4".repeat(64),
          failure_mode: null,
          dominant_driver_parameter_ids: ["beta"],
        },
      ],
    };

    expect(dynamicEventsForParameter(trace, "alpha")).toHaveLength(1);
    expect(dynamicEventsForParameter(trace, "alpha")[0]?.module_id).toBe("module.alpha");
    expect(dynamicEventsForParameter(trace, "missing")).toEqual([]);
  });
});
