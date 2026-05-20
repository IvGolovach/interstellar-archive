import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import { ExternalProofPanel } from "../src/ui/proof/ExternalProofPanel";

const dataset = loadParameterDrilldownDataset();

describe("external proof panel", () => {
  it("renders proof-phase artifacts without claiming external completion", () => {
    const html = renderToStaticMarkup(
      <ExternalProofPanel
        externalLedger={dataset.externalValidationExecutionLedger}
        physicsComparison={dataset.independentPhysicsBackendComparison}
        capsuleQualification={dataset.capsuleQualificationEvidencePack}
        evidenceClosure={dataset.evidenceUpgradeClosure}
        reproductionKit={dataset.externalReproductionKit}
        evidenceIntake={dataset.externalEvidenceIntake}
        validationCampaign={dataset.externalValidationCampaign}
        releaseCandidate={dataset.releaseCandidateReadiness}
      />,
    );

    expect(html).toContain("External Proof Phase");
    expect(html).toContain("external_validation_execution_ledger.v1");
    expect(html).toContain("independent_physics_backend_comparison.v1");
    expect(html).toContain("capsule_qualification_evidence_pack.v1");
    expect(html).toContain("external_reproduction_kit.v1");
    expect(html).toContain("external_evidence_intake.v1");
    expect(html).toContain("external_validation_campaign.v1");
    expect(html).toContain("repo_campaign_ready_external_execution_required");
    expect(html).toContain("release_candidate_readiness.v1");
    expect(html).toContain("repo_publication_candidate_external_evidence_open");
    expect(html).toContain("External validation completed");
    expect(html).toContain("no");
    expect(html).not.toContain("fetch(");
  });

  it("keeps qualification and certification blockers visible", () => {
    const html = renderToStaticMarkup(
      <ExternalProofPanel
        externalLedger={dataset.externalValidationExecutionLedger}
        physicsComparison={dataset.independentPhysicsBackendComparison}
        capsuleQualification={dataset.capsuleQualificationEvidencePack}
        evidenceClosure={dataset.evidenceUpgradeClosure}
        reproductionKit={dataset.externalReproductionKit}
        evidenceIntake={dataset.externalEvidenceIntake}
        validationCampaign={dataset.externalValidationCampaign}
        releaseCandidate={dataset.releaseCandidateReadiness}
      />,
    );

    expect(html).toContain("Qualification complete");
    expect(html).toContain("Certification go");
    expect(html).toContain("Self-signed accepted");
    expect(html).toContain("First real record");
    expect(html).toContain("Certification language");
    expect(html).toContain("Proof promotion auto");
    expect(html).toContain("qualified");
    expect(html).toContain("certified");
  });
});
