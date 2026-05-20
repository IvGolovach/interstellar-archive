import { useMemo } from "react";

import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { ParameterDetailPage } from "../ui/drilldown/ParameterDetailPage";
import type { WorkspacePageProps } from "../app/app_routes";

export default function ParameterDetailRoute(props: WorkspacePageProps): JSX.Element {
  const { navigate, route } = props;
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);
  const parameter =
    route.kind === "parameter-detail"
      ? dataset.parameters.find((entry) => entry.parameter_id === route.parameterId) ?? null
      : null;
  const staticUsageEntry =
    parameter !== null ? dataset.staticUsageGraph[parameter.parameter_id] ?? null : null;
  const evidenceEntry =
    parameter !== null ? dataset.evidenceIndex[parameter.parameter_id] ?? null : null;

  return (
    <ParameterDetailPage
      parameter={parameter}
      evidenceEntry={evidenceEntry}
      staticUsageEntry={staticUsageEntry}
      pSuccessDefensibility={dataset.pSuccessDefensibility}
      failureSurfaceBaseline={dataset.failureSurfaceBaseline}
      objectiveContract={dataset.objectiveContract}
      objectiveScoreBaseline={dataset.objectiveScoreBaseline}
      optimizationFrontier={dataset.optimizationFrontier}
      onBack={() => navigate({ kind: "parameters" })}
      devLocalEnabled={import.meta.env.DEV}
      dynamicTrace={null}
      dynamicValidation={null}
      dynamicTraceLoadError={null}
      onLoadDynamicTraceFile={async () => undefined}
    />
  );
}
