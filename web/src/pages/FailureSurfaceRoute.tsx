import { useMemo } from "react";

import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { FailureSurfacePanel } from "../ui/drilldown/FailureSurfacePanel";
import type { WorkspacePageProps } from "../app/app_routes";

export default function FailureSurfaceRoute(_: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);

  return (
    <FailureSurfacePanel
      baseline={dataset.failureSurfaceBaseline}
      simulationOutput={null}
    />
  );
}
