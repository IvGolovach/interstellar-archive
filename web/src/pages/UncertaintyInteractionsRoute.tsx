import { useMemo } from "react";

import type { WorkspacePageProps } from "../app/app_routes";
import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { UncertaintyInteractionsPanel } from "../ui/uncertainty/UncertaintyInteractionsPanel";

export default function UncertaintyInteractionsRoute({ navigate, route }: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);
  const pairId = route.kind === "uncertainty-interactions" ? route.pairId : undefined;

  return (
    <UncertaintyInteractionsPanel
      artifact={dataset.uncertaintyInteractions}
      selectedPairId={pairId}
      onSelectPair={(nextPairId) => navigate({ kind: "uncertainty-interactions", pairId: nextPairId })}
    />
  );
}
