import { useMemo } from "react";

import type { WorkspacePageProps } from "../app/app_routes";
import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { ExternalReviewPackPanel } from "../ui/review/ExternalReviewPackPanel";

export default function ExternalReviewRoute(_: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);

  return <ExternalReviewPackPanel artifact={dataset.externalValidationReviewPack} />;
}
