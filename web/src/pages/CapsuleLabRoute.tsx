import { useMemo } from "react";

import type { WorkspacePageProps } from "../app/app_routes";
import { PUBLIC_DATASET_PATHS } from "../lib/artifact_public_contracts";
import { CAPSULE_RISK_BUDGET_ARTIFACT } from "../lib/capsule_risk_budget_contract";
import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_dataset";
import { CapsuleLab } from "../ui/capsule/CapsuleLab";

const EXPECTED_CAPSULE_RISK_BUDGET_PATH = "artifacts/capsule_risk_budget.v1.json";

function readCapsuleRiskBudgetPath(): string {
  const sourcePaths = PUBLIC_DATASET_PATHS as unknown as Record<string, unknown>;
  const path = sourcePaths.capsuleRiskBudget;

  return typeof path === "string" && path !== "" ? path : EXPECTED_CAPSULE_RISK_BUDGET_PATH;
}

export default function CapsuleLabRoute(_: WorkspacePageProps): JSX.Element {
  const { artifact, riskBudgetArtifact, riskBudgetArtifactPath } = useMemo(
    () => {
      const dataset = loadParameterDrilldownDataset();
      return {
        artifact: dataset.capsuleSurvivabilityLab,
        riskBudgetArtifact: CAPSULE_RISK_BUDGET_ARTIFACT,
        riskBudgetArtifactPath: readCapsuleRiskBudgetPath(),
      };
    },
    [],
  );

  return (
    <CapsuleLab
      artifact={artifact}
      artifactPath={PUBLIC_DATASET_PATHS.capsuleSurvivabilityLab}
      riskBudgetArtifact={riskBudgetArtifact}
      riskBudgetArtifactPath={riskBudgetArtifactPath}
    />
  );
}
