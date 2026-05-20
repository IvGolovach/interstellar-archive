import { useMemo } from "react";

import type { WorkspacePageProps } from "../app/app_routes";
import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { UserMissionRunPanel } from "../ui/mission_run/UserMissionRunPanel";

export default function UserMissionRunRoute({ navigate, route }: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);
  const runId = route.kind === "mission-runs" ? route.runId : undefined;

  return (
    <UserMissionRunPanel
      artifact={dataset.userMissionRunCatalog}
      runtimeArtifact={dataset.runtimeScenarioGeneration}
      selectedRunId={runId}
      onSelectRun={(nextRunId) => navigate({ kind: "mission-runs", runId: nextRunId })}
    />
  );
}
