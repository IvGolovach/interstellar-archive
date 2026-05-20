import { MissionControlPanel } from "./MissionControlPanel";
import { MissionModeOverview } from "./MissionModeOverview";
import { MissionOptimizationPanel } from "./MissionOptimizationPanel";
import { MissionResultsPanel } from "./MissionResultsPanel";
import { MissionStageTimeline } from "./MissionStageTimeline";
import { useMissionMode } from "./useMissionMode";

export function MissionMode(): JSX.Element {
  const missionMode = useMissionMode();

  return (
    <main className="app-shell mission-mode-shell">
      <MissionModeOverview model={missionMode.overviewModel} />

      <MissionStageTimeline baseline={missionMode.stageTimelineBaseline} />

      <MissionControlPanel model={missionMode.controlPanelModel} />

      <MissionResultsPanel model={missionMode.resultsPanelModel} />

      <MissionOptimizationPanel model={missionMode.optimizationPanelModel} />
    </main>
  );
}
