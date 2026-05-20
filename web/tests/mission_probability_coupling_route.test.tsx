import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import MissionProbabilityCouplingRoute from "../src/pages/MissionProbabilityCouplingRoute";

describe("MissionProbabilityCouplingRoute", () => {
  it("renders the tracked probability coupling without closing full mission probability", () => {
    const html = renderToStaticMarkup(
      <MissionProbabilityCouplingRoute navigate={() => undefined} route={{ kind: "mission-probability" }} />,
    );

    expect(html).toContain("Mission Probability Coupling");
    expect(html).toContain("Full Mission p50");
    expect(html).toContain("not_closed_external_factors_open");
    expect(html).toContain("Factor Budget");
    expect(html).toContain("DAG Snapshot");
  });
});
