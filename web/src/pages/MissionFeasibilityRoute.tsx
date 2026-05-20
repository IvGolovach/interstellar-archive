import { useMemo } from "react";

import type { WorkspacePageProps } from "../app/app_routes";
import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { MissionFeasibilityPanel } from "../ui/feasibility/MissionFeasibilityPanel";

export default function MissionFeasibilityRoute(_: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);

  return <MissionFeasibilityPanel artifact={dataset.missionFeasibilityScreen} />;
}
