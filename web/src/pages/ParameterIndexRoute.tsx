import { useMemo } from "react";

import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { ParameterIndexPage } from "../ui/drilldown/ParameterIndexPage";
import { type WorkspacePageProps } from "../app/app_routes";

export default function ParameterIndexRoute(props: WorkspacePageProps): JSX.Element {
  const { navigate } = props;
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);
  const dynamicTraceParameterIds = useMemo(() => new Set<string>(), []);

  return (
    <ParameterIndexPage
      parameters={dataset.parameters}
      onOpenDetail={(parameterId) => navigate({ kind: "parameter-detail", parameterId })}
      dynamicTraceParameterIds={dynamicTraceParameterIds}
      devLocalEnabled={import.meta.env.DEV}
    />
  );
}
