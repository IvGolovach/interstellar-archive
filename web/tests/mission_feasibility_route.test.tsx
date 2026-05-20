import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import { MissionFeasibilityPanel } from "../src/ui/feasibility/MissionFeasibilityPanel";

describe("mission feasibility route", () => {
  it("renders the default black-hole feasibility screen from the tracked artifact", () => {
    const dataset = loadParameterDrilldownDataset();
    const artifact = dataset.missionFeasibilityScreen;
    const defaultRow = artifact.scenario_rows.find((row) => row.id === artifact.default_scenario_id);

    expect(defaultRow?.target_id).toBe("reference-black-hole");
    expect(defaultRow?.velocity_id).toBe("conditional-45");
    expect(defaultRow?.flight_years).toBeGreaterThan(10_000_000);
    expect(defaultRow?.flight_years).toBeLessThan(10_700_000);

    const html = renderToStaticMarkup(<MissionFeasibilityPanel artifact={artifact} />);
    expect(html).toContain("Mission Feasibility Screen");
    expect(html).toContain("mission_feasibility_screen.v1");
    expect(html).toContain("Flight Time");
    expect(html).toContain("Dust Sweep");
    expect(html).toContain("Capsule Risk Link");
    expect(html).toContain("External Evidence Still Required");
    expect(html).toContain("Blocked Claims");
    expect(html).toContain("flight ready");
  });
});
