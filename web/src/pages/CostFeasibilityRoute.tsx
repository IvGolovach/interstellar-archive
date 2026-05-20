import { useMemo } from "react";

import type { WorkspacePageProps } from "../app/app_routes";
import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { CostFeasibilityPanel } from "../ui/cost/CostFeasibilityPanel";

export default function CostFeasibilityRoute(_: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);

  return <CostFeasibilityPanel artifact={dataset.costProcurementArchitectureFeasibility} />;
}
