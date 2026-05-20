import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import { UserMissionRunPanel } from "../src/ui/mission_run/UserMissionRunPanel";

describe("user mission run route", () => {
  it("renders the default selected run from the tracked browser dataset", () => {
    const dataset = loadParameterDrilldownDataset();
    const artifact = dataset.userMissionRunCatalog;
    const defaultRow = artifact.run_rows.find((row) => row.run_id === artifact.default_run_id);

    expect(defaultRow?.selection.target_id).toBe("reference-black-hole");
    expect(defaultRow?.selection.velocity_id).toBe("conditional-45");
    expect(defaultRow?.runtime_pack_template.script).toBe("scripts/run_user_mission_scenario.py");
    expect(defaultRow?.runtime_pack_template.writes_tracked_files).toBe(false);

    const html = renderToStaticMarkup(
      <UserMissionRunPanel
        artifact={artifact}
        runtimeArtifact={dataset.runtimeScenarioGeneration}
        selectedRunId={artifact.default_run_id}
        onSelectRun={() => undefined}
      />,
    );
    expect(html).toContain("Selected Mission Run");
    expect(html).toContain("runtime_scenario_generation.v1");
    expect(html).toContain("Run Recipe");
    expect(html).toContain("--verify-deterministic");
    expect(html).toContain("Compiled Scenario Preview");
    expect(html).toContain("USER_RUN_SUMMARY.json");
    expect(html).toContain("Local Review Pack");
    expect(html).toContain("Selection hash");
    expect(html).toContain("External Evidence Still Required");
    expect(html).toContain("flight ready");
  });

  it("renders an explicit boundary for unknown run deep links", () => {
    const dataset = loadParameterDrilldownDataset();
    const html = renderToStaticMarkup(
      <UserMissionRunPanel
        artifact={dataset.userMissionRunCatalog}
        runtimeArtifact={dataset.runtimeScenarioGeneration}
        selectedRunId="umr-not-in-catalog"
        onSelectRun={() => undefined}
      />,
    );

    expect(html).toContain("Run Not Found");
    expect(html).toContain("not in the committed catalog");
    expect(html).toContain(dataset.userMissionRunCatalog.default_run_id);
  });
});
