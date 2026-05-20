import { useMemo } from "react";

import type { WorkspacePageProps } from "../app/app_routes";
import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { MissionProbabilityCouplingPanel } from "../ui/probability_coupling/MissionProbabilityCouplingPanel";

export default function MissionProbabilityCouplingRoute({ navigate, route }: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);
  const couplingId = route.kind === "mission-probability" ? route.couplingId : undefined;

  return (
    <MissionProbabilityCouplingPanel
      artifact={dataset.missionProbabilityCoupling}
      selectedCouplingId={couplingId}
      onSelectCoupling={(nextCouplingId) => navigate({ kind: "mission-probability", couplingId: nextCouplingId })}
    />
  );
}
