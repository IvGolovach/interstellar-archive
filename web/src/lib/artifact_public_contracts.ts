import * as artifactContractModule from "../../../artifacts/public/browser_dataset_contract";

type PublicDatasetPaths = {
  capsuleRiskBudget: string;
  missionFeasibilityScreen: string;
  userMissionRunCatalog: string;
  runtimeScenarioGeneration: string;
  costProcurementArchitectureFeasibility: string;
  externalValidationReviewPack: string;
  publicNarrativeHardening: string;
  externalValidationExecutionLedger: string;
  independentPhysicsBackendComparison: string;
  capsuleQualificationEvidencePack: string;
  evidenceUpgradeClosure: string;
  externalReproductionKit: string;
  externalEvidenceIntake: string;
  externalValidationCampaign: string;
  releaseCandidateReadiness: string;
  missionProbabilityCoupling: string;
  uncertaintyInteractions: string;
  evidenceUpgradeCampaign: string;
  missionDagV2Boundary: string;
  roadmapClosure: string;
  determinismStatus: string;
  failureSurfaceBaseline: string;
  parameterDrilldownManifest: string;
  parameterEvidenceIndex: string;
  objectiveContract: string;
  objectiveScoreBaseline: string;
  optimizationFrontier: string;
  optimizationV2: string;
  optimizationSearchSpace: string;
  capsuleSurvivabilityLab: string;
  pSuccessDefensibility: string;
  parameterStaticUsageGraph: string;
};

type ArtifactContractExports = {
  PUBLIC_DATASET_PATHS: PublicDatasetPaths;
  browserDataset: unknown;
};

function resolveModuleExports<T>(
  module: Record<string, unknown>,
  predicate: (candidate: Record<string, unknown>) => boolean,
  errorMessage: string,
): T {
  const asAny = module as Record<string, any>;
  const candidates = [asAny, asAny.default, asAny["module.exports"]];

  for (const candidate of candidates) {
    if (!candidate) {
      continue;
    }
    if (predicate(candidate as Record<string, unknown>)) {
      return candidate as T;
    }
  }

  throw new Error(errorMessage);
}

const artifactContract = resolveModuleExports<ArtifactContractExports>(
  artifactContractModule as unknown as Record<string, unknown>,
  (candidate) =>
    typeof candidate.PUBLIC_DATASET_PATHS === "object" &&
    candidate.PUBLIC_DATASET_PATHS !== null &&
    typeof candidate.browserDataset === "object" &&
    candidate.browserDataset !== null,
  "Unable to resolve artifacts/public/browser_dataset_contract exports.",
);

export const PUBLIC_DATASET_PATHS = artifactContract.PUBLIC_DATASET_PATHS;
export const BROWSER_DATASET = artifactContract.browserDataset;
