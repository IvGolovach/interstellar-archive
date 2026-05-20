import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SimOutput } from "../../sim/public/types";
import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import { FailureSurfacePanel } from "../src/ui/drilldown/FailureSurfacePanel";

const dataset = loadParameterDrilldownDataset();

const mockSimulationOutput: SimOutput = {
  output_version: "sim_output.v1",
  engine_version: "v1",
  schema_version: "sim_schema.v2",
  golden_checksum: "bda117f5294cdd3147506d0b3f3f92c99d4113857631230b05bacdd0bd70288c",
  derived_metrics: {
    finite_control_window_year: 10,
    terminal_interaction_radius_au: 100,
    encounter_likelihood_percent: 50,
    expected_mm_tail_hits: 1,
    shield_survival_margin: 0.5,
  },
  series: [],
  warnings: [],
  invariants_passed: true,
  checksum_payload: "{}",
};

describe("failure surface UI smoke", () => {
  it("renders baseline breakdown from committed artifact data", () => {
    const html = renderToStaticMarkup(
      <FailureSurfacePanel baseline={dataset.failureSurfaceBaseline} simulationOutput={null} />,
    );

    expect(html).toContain("Failure Surface &amp; Breakdown (baseline)");
    expect(html).toContain("Outcome");
    expect(html).toContain("Stage timeline (S0–S3)");
    expect(html).toContain("Dominant drivers (top-3)");
    expect(html).toContain("Baseline only. Current run output is not loaded.");
  });

  it("keeps comparison deterministic without runtime fetch", () => {
    const html = renderToStaticMarkup(
      <FailureSurfacePanel baseline={dataset.failureSurfaceBaseline} simulationOutput={mockSimulationOutput} />,
    );

    expect(html).toContain("sim_output.v1");
    expect(html).toContain("delta.p_success: N/A");
    expect(html).not.toContain("fetch(");
  });
});
