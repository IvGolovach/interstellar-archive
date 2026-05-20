import { describe, expect, it } from "vitest";

import type { SimOutput } from "../../sim/public/types";
import {
  buildMetricCards,
  chartPath,
  formatResultNumber,
} from "../src/ui/result_view_helpers";

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

describe("result view helpers", () => {
  it("formats numbers and chart paths deterministically", () => {
    expect(formatResultNumber(Number.NaN)).toBe("-");
    expect(formatResultNumber(1234.5)).toBe("1235");
    expect(formatResultNumber(123.456)).toBe("123.46");
    expect(formatResultNumber(12.3456)).toBe("12.346");
    expect(formatResultNumber(1.23456)).toBe("1.2346");
    expect(chartPath(buildOutput().series, "encounter_likelihood")).toContain("M");
  });

  it("builds placeholder cards without output and enriched cards with output", () => {
    const placeholderCards = buildMetricCards(null);
    const liveCards = buildMetricCards(buildOutput());

    expect(placeholderCards).toHaveLength(6);
    expect(placeholderCards[0]?.value).toBe("-");
    expect(liveCards).toHaveLength(8);
    expect(liveCards.find((card) => card.id === "invariants_passed")?.value).toBe("pass");
    expect(liveCards.find((card) => card.id === "horizon_encounter")?.value).toBe(0.2);
  });
});
