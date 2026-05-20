import { useMemo } from "react";

import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { OptimizationLabPanel } from "../ui/drilldown/OptimizationLabPanel";
import type { WorkspacePageProps } from "../app/app_routes";

export default function OptimizationLabRoute({ route }: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);
  const selectedCandidateId = route.kind === "optimization" ? route.candidateId : undefined;

  return (
    <OptimizationLabPanel
      contract={dataset.objectiveContract}
      frontier={dataset.optimizationFrontier}
      optimizationV2={dataset.optimizationV2}
      searchSpace={dataset.optimizationSearchSpace}
      selectedCandidateId={selectedCandidateId}
    />
  );
}
