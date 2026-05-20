import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import { MissionDagBoundaryPanel } from "../src/ui/dag/MissionDagBoundaryPanel";

const dataset = loadParameterDrilldownDataset();

describe("mission DAG v2 boundary panel", () => {
  it("renders module boundary rows from tracked artifact", () => {
    const html = renderToStaticMarkup(
      <MissionDagBoundaryPanel boundary={dataset.missionDagV2Boundary} />,
    );

    expect(html).toContain("Mission DAG v2 boundary");
    expect(html).toContain("mission_dag_v2_boundary.v1.json");
    expect(html).toContain("state trace hash");
    expect(html).toContain("traj.baseline.v1");
    expect(html).toContain("flight-ready module approved");
  });

  it("does not silently replace an unknown module deep link", () => {
    const html = renderToStaticMarkup(
      <MissionDagBoundaryPanel boundary={dataset.missionDagV2Boundary} selectedModuleId="missing.module" />,
    );

    expect(html).toContain("module id not found");
    expect(html).toContain("missing.module");
  });
});
