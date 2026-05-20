import { useMemo } from "react";

import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { MissionDagBoundaryPanel } from "../ui/dag/MissionDagBoundaryPanel";
import type { WorkspacePageProps } from "../app/app_routes";

export default function MissionDagBoundaryRoute({ route }: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);
  const moduleId = route.kind === "mission-dag-boundary" ? route.moduleId : undefined;

  return (
    <MissionDagBoundaryPanel
      boundary={dataset.missionDagV2Boundary}
      selectedModuleId={moduleId}
    />
  );
}
