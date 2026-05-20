import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import { VisualizationLayerPanel } from "../src/ui/visualization/VisualizationLayerPanel";

const dataset = loadParameterDrilldownDataset();

describe("visualization layer snapshot", () => {
  it("renders deterministic timeline view", () => {
    const html = renderToStaticMarkup(
      <VisualizationLayerPanel
        failureSurfaceBaseline={dataset.failureSurfaceBaseline}
        optimizationFrontier={dataset.optimizationFrontier}
        objectiveScoreBaseline={dataset.objectiveScoreBaseline}
        initialVisualizationEnabled={true}
        initialTab="timeline"
      />,
    );

    expect(html).toContain("Mission Timeline (S0-S3)");
    expect(html).toContain("Dominant drivers (top-3)");
    expect(html).toMatchSnapshot();
  });

  it("renders deterministic frontier view", () => {
    const html = renderToStaticMarkup(
      <VisualizationLayerPanel
        failureSurfaceBaseline={dataset.failureSurfaceBaseline}
        optimizationFrontier={dataset.optimizationFrontier}
        objectiveScoreBaseline={dataset.objectiveScoreBaseline}
        initialVisualizationEnabled={true}
        initialTab="frontier"
      />,
    );

    expect(html).toContain("Optimization Frontier (2D Pareto)");
    expect(html).toContain("x=risk_envelope [0..1], y=p_success [0..1]");
    expect(html).toMatchSnapshot();
  });
});
