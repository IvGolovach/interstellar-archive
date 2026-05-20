import { useMemo } from "react";

import type { WorkspacePageProps } from "../app/app_routes";
import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { PublicNarrativePanel } from "../ui/narrative/PublicNarrativePanel";

export default function PublicNarrativeRoute(_: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);

  return <PublicNarrativePanel artifact={dataset.publicNarrativeHardening} />;
}
