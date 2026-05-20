import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import { OptimizationLabPanel } from "../src/ui/drilldown/OptimizationLabPanel";

const dataset = loadParameterDrilldownDataset();

describe("optimization lab panel UI smoke", () => {
  it("renders deterministic objective/frontier summary from tracked artifacts", () => {
    const html = renderToStaticMarkup(
      <OptimizationLabPanel
        contract={dataset.objectiveContract}
        frontier={dataset.optimizationFrontier}
        optimizationV2={dataset.optimizationV2}
        searchSpace={dataset.optimizationSearchSpace}
      />,
    );

    expect(html).toContain("Optimization Lab (v2 decision surface)");
    expect(html).toContain("optimization_frontier_realistic.v1.json");
    expect(html).toContain("optimization_v2_frontier.v1.json");
    expect(html).toContain("optimization_search_space.v1.json");
    expect(html).toContain("Open optimization v2 artifact JSON");
    expect(html).toContain("p_success");
    expect(html).toContain("risk_envelope");
    expect(html).toContain("qualification_gap");
    expect(html).toContain("cost_proxy");
  });

  it("stays derived-only and does not fetch runtime truth", () => {
    const html = renderToStaticMarkup(
      <OptimizationLabPanel
        contract={dataset.objectiveContract}
        frontier={dataset.optimizationFrontier}
        optimizationV2={dataset.optimizationV2}
        searchSpace={dataset.optimizationSearchSpace}
      />,
    );

    expect(html).not.toContain("fetch(");
    expect(html).not.toContain("ops/");
    expect(html).toContain("search space");
    expect(html).toContain("procurement-grade cost estimate");
  });

  it("does not silently replace an unknown candidate deep link", () => {
    const html = renderToStaticMarkup(
      <OptimizationLabPanel
        contract={dataset.objectiveContract}
        frontier={dataset.optimizationFrontier}
        optimizationV2={dataset.optimizationV2}
        searchSpace={dataset.optimizationSearchSpace}
        selectedCandidateId="optv2-pt-missing"
      />,
    );

    expect(html).toContain("candidate id not found");
    expect(html).toContain("optv2-pt-missing");
  });
});
