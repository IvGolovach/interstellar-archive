import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import { RoadmapClosurePanel } from "../src/ui/roadmap/RoadmapClosurePanel";

const dataset = loadParameterDrilldownDataset();

describe("roadmap closure panel", () => {
  it("renders all 15 roadmap closure rows from the committed artifact", () => {
    const html = renderToStaticMarkup(<RoadmapClosurePanel artifact={dataset.roadmapClosure} />);

    expect(html).toContain("Full V2 Roadmap Closure");
    expect(html).toContain("Open roadmap artifact JSON");
    expect(html).toContain("roadmap_closure.v1");
    expect(html).toContain("Mission Physics v2 screening layer");
    expect(html).toContain("Public narrative hardening");
    expect(html).toContain("repo_native_closure_implemented_external_evidence_open");
  });

  it("keeps external evidence gaps and false-claim blocks visible", () => {
    const html = renderToStaticMarkup(<RoadmapClosurePanel artifact={dataset.roadmapClosure} />);

    expect(html).toContain("External Evidence Still Open");
    expect(html).toContain("False claims blocked");
    expect(html).toContain("certified");
    expect(html).not.toContain("fetch(");
  });
});
