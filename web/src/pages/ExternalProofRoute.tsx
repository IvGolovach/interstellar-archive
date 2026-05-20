import { useMemo } from "react";

import type { WorkspacePageProps } from "../app/app_routes";
import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { ExternalProofPanel } from "../ui/proof/ExternalProofPanel";

export default function ExternalProofRoute(_: WorkspacePageProps): JSX.Element {
  const dataset = useMemo(() => loadParameterDrilldownDataset(), []);

  return (
    <ExternalProofPanel
      externalLedger={dataset.externalValidationExecutionLedger}
      physicsComparison={dataset.independentPhysicsBackendComparison}
      capsuleQualification={dataset.capsuleQualificationEvidencePack}
      evidenceClosure={dataset.evidenceUpgradeClosure}
      reproductionKit={dataset.externalReproductionKit}
      evidenceIntake={dataset.externalEvidenceIntake}
      validationCampaign={dataset.externalValidationCampaign}
      releaseCandidate={dataset.releaseCandidateReadiness}
    />
  );
}
