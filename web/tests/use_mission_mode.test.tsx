import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { useMissionMode } from "../src/ui/mission/useMissionMode";

describe("useMissionMode", () => {
  it("exposes coherent initial section models through the hook", () => {
    let latest: ReturnType<typeof useMissionMode> | null = null;

    function HookProbe(): null {
      latest = useMissionMode();
      return null;
    }

    renderToStaticMarkup(<HookProbe />);

    if (!latest) {
      throw new Error("Mission mode hook did not produce a value.");
    }

    expect(latest.overviewModel.baselinePSuccess).toBeGreaterThan(0);
    expect(latest.controlPanelModel.scenarios.length).toBeGreaterThan(0);
    expect(latest.controlPanelModel.engineeringFields.length).toBeGreaterThan(0);
    expect(latest.controlPanelModel.speculativeFields.length).toBeGreaterThan(0);
    expect(latest.resultsPanelModel.runError).toBeNull();
    expect(latest.resultsPanelModel.lastRun).toBeNull();
    expect(latest.resultsPanelModel.projection.dominantDrivers).toHaveLength(3);
    expect(latest.optimizationPanelModel.expanded).toBe(false);
    expect(latest.stageTimelineBaseline.timeline).toHaveLength(4);
  });
});
