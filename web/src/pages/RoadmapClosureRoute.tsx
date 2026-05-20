import { useMemo } from "react";

import type { WorkspacePageProps } from "../app/app_routes";
import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { RoadmapClosurePanel } from "../ui/roadmap/RoadmapClosurePanel";

export default function RoadmapClosureRoute(_: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);

  return <RoadmapClosurePanel artifact={dataset.roadmapClosure} />;
}
