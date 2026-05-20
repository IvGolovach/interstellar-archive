import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SimOutput } from "../../sim/public/types";
import { ResultView } from "../src/ui/ResultView";

function buildOutput(): SimOutput {
  return {
    output_version: "sim_output.v1",
    engine_version: "v1",
    schema_version: "sim_schema.v1",
    golden_checksum: "checksum-123",
    derived_metrics: {
      finite_control_window_year: 12.3456,
      terminal_interaction_radius_au: 0.4321,
      encounter_likelihood_percent: 87.6543,
      expected_mm_tail_hits: 2.5,
      shield_survival_margin: 1.125,
    },
    series: [
      { year: 0, control_leverage: 1, encounter_likelihood: 0.1, lethal_hit_rate: 0.01 },
      { year: 10, control_leverage: 0.9, encounter_likelihood: 0.2, lethal_hit_rate: 0.02 },
    ],
    warnings: [],
    invariants_passed: true,
    checksum_payload: "payload",
  };
}

describe("result view UI smoke", () => {
  it("renders deterministic metrics, reproducibility data, charts, and series table", () => {
    const html = renderToStaticMarkup(
      <ResultView
        output={buildOutput()}
        lastVerifiedCommitSha="abc123"
        deterministicEngineVersion="v1"
        deterministicSchemaVersion="sim_schema.v1"
        deterministicGoldenChecksum="checksum-123"
      />,
    );

    expect(html).toContain("Results");
    expect(html).toContain("Key metrics");
    expect(html).toContain("Integrity");
    expect(html).toContain("Reproducibility");
    expect(html).toContain("Encounter likelihood by year");
    expect(html).toContain("Lethal hit rate by year");
    expect(html).toContain("Last verified commit");
    expect(html).toContain("Year");
    expect(html).toContain("checksum-123");
  });

  it("renders placeholders and empty-state guidance without output", () => {
    const html = renderToStaticMarkup(
      <ResultView
        output={null}
        lastVerifiedCommitSha="abc123"
        deterministicEngineVersion="v1"
        deterministicSchemaVersion="sim_schema.v1"
        deterministicGoldenChecksum={null}
      />,
    );

    expect(html).toContain("run scenario first");
    expect(html).toContain("Run a scenario to render this chart.");
    expect(html).toContain(
      "Run a scenario to generate deterministic output metrics and the full series table.",
    );
  });
});
