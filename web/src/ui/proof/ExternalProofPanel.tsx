import { PUBLIC_DATASET_PATHS } from "../../lib/artifact_public_contracts";
import type {
  CapsuleQualificationEvidencePackArtifact,
  EvidenceUpgradeClosureArtifact,
  ExternalEvidenceIntakeArtifact,
  ExternalValidationCampaignArtifact,
  ExternalReproductionKitArtifact,
  ExternalValidationExecutionLedgerArtifact,
  IndependentPhysicsBackendComparisonArtifact,
  ReleaseCandidateReadinessArtifact,
} from "../../lib/parameter_drilldown_loader";
import "./ExternalProofPanel.css";

interface ExternalProofPanelProps {
  externalLedger: ExternalValidationExecutionLedgerArtifact;
  physicsComparison: IndependentPhysicsBackendComparisonArtifact;
  capsuleQualification: CapsuleQualificationEvidencePackArtifact;
  evidenceClosure: EvidenceUpgradeClosureArtifact;
  reproductionKit: ExternalReproductionKitArtifact;
  evidenceIntake: ExternalEvidenceIntakeArtifact;
  validationCampaign: ExternalValidationCampaignArtifact;
  releaseCandidate: ReleaseCandidateReadinessArtifact;
}

function yesNo(value: boolean): string {
  return value ? "yes" : "no";
}

function formatNumber(value: number | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("en-US") : "N/A";
}

export function ExternalProofPanel({
  externalLedger,
  physicsComparison,
  capsuleQualification,
  evidenceClosure,
  reproductionKit,
  evidenceIntake,
  validationCampaign,
  releaseCandidate,
}: ExternalProofPanelProps): JSX.Element {
  const blockers = releaseCandidate.blocked_claims.slice(0, 8);
  const firstTests = capsuleQualification.qualification_tests.slice(0, 4);
  const firstChecks = physicsComparison.analytic_checks.slice(0, 5);
  const firstWorkstreams = validationCampaign.workstreams.slice(0, 6);

  return (
    <main className="external-proof-shell">
      <section className="external-proof-hero">
        <div>
          <p className="eyebrow">External Proof Phase</p>
          <h2>Publication candidate, external evidence still open</h2>
          <p className="help-text">
            This route renders the committed proof-phase artifacts: reviewer execution ledger, repo analytic
            cross-checks, capsule qualification matrix, evidence closure cycle, and release-candidate boundary.
          </p>
        </div>
        <div className="external-proof-actions">
          <a className="ghost-button" href={PUBLIC_DATASET_PATHS.externalValidationCampaign}>
            Open campaign JSON
          </a>
          <a className="ghost-button" href={PUBLIC_DATASET_PATHS.releaseCandidateReadiness}>
            Open readiness JSON
          </a>
        </div>
      </section>

      <section className="external-proof-status panel" aria-label="Release candidate status">
        <div>
          <p className="eyebrow">Status</p>
          <p>{releaseCandidate.release_candidate_status}</p>
        </div>
        <div>
          <p className="eyebrow">Certification go</p>
          <p>{yesNo(releaseCandidate.rollup.certification_go)}</p>
        </div>
        <div>
          <p className="eyebrow">External validation completed</p>
          <p>{yesNo(releaseCandidate.rollup.external_validation_completed)}</p>
        </div>
      </section>

      <section className="external-proof-metric-grid" aria-label="Proof-phase metrics">
        <article className="panel external-proof-metric">
          <p className="eyebrow">External records</p>
          <p className="metric-value">{formatNumber(externalLedger.execution_record_count)}</p>
          <p className="help-text">{externalLedger.schema_version}</p>
        </article>
        <article className="panel external-proof-metric">
          <p className="eyebrow">Analytic checks</p>
          <p className="metric-value">{formatNumber(physicsComparison.analytic_check_count)}</p>
          <p className="help-text">{physicsComparison.schema_version}</p>
        </article>
        <article className="panel external-proof-metric">
          <p className="eyebrow">Qualification tests</p>
          <p className="metric-value">{formatNumber(capsuleQualification.qualification_test_count)}</p>
          <p className="help-text">{capsuleQualification.schema_version}</p>
        </article>
        <article className="panel external-proof-metric">
          <p className="eyebrow">Evidence closure rows</p>
          <p className="metric-value">{formatNumber(evidenceClosure.closure_cycle_count)}</p>
          <p className="help-text">{evidenceClosure.schema_version}</p>
        </article>
        <article className="panel external-proof-metric">
          <p className="eyebrow">Reviewer pack cases</p>
          <p className="metric-value">{formatNumber(reproductionKit.review_case_count)}</p>
          <p className="help-text">{reproductionKit.schema_version}</p>
        </article>
        <article className="panel external-proof-metric">
          <p className="eyebrow">Accepted records</p>
          <p className="metric-value">{formatNumber(evidenceIntake.accepted_record_count)}</p>
          <p className="help-text">{evidenceIntake.schema_version}</p>
        </article>
        <article className="panel external-proof-metric">
          <p className="eyebrow">Campaign workstreams</p>
          <p className="metric-value">{formatNumber(validationCampaign.workstream_count)}</p>
          <p className="help-text">{validationCampaign.schema_version}</p>
        </article>
      </section>

      <section className="external-proof-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Validation Campaign</p>
            <h3>{validationCampaign.campaign_status}</h3>
          </div>
          <code>{validationCampaign.public_scope}</code>
        </div>
        <div className="external-proof-gate-grid">
          {firstWorkstreams.map((workstream) => (
            <article key={workstream.workstream_id} className="external-proof-gate">
              <div className="external-proof-gate-header">
                <code>{workstream.workstream_id}</code>
                <span>{workstream.status}</span>
              </div>
              <p>{workstream.evidence_ref}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="external-proof-section">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Readiness Gates</p>
            <h3>{releaseCandidate.schema_version}</h3>
          </div>
          <code>{releaseCandidate.public_scope}</code>
        </div>
        <div className="external-proof-gate-grid">
          {releaseCandidate.repository_gates.map((gate) => (
            <article key={String(gate.gate_id)} className="external-proof-gate">
              <div className="external-proof-gate-header">
                <code>{String(gate.gate_id)}</code>
                <span>{String(gate.status)}</span>
              </div>
              <p>{String(gate.evidence)}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="external-proof-two-column">
        <article>
          <p className="eyebrow">Reproduction Kit</p>
          <h3>{reproductionKit.kit_status}</h3>
          <ul className="external-proof-list">
            <li>
              <span>Export CLI</span>
              <code>{String(reproductionKit.pack_contract.export_cli)}</code>
            </li>
            <li>
              <span>Pack files</span>
              <code>{String(reproductionKit.pack_contract.pack_file_count)}</code>
            </li>
            <li>
              <span>External execution</span>
              <code>{yesNo(reproductionKit.rollup.external_execution_completed)}</code>
            </li>
          </ul>
        </article>
        <article>
          <p className="eyebrow">Evidence Intake</p>
          <h3>{evidenceIntake.intake_status}</h3>
          <ul className="external-proof-list">
            <li>
              <span>External record dir</span>
              <code>{evidenceIntake.external_records_dir}</code>
            </li>
            <li>
              <span>Self-signed accepted</span>
              <code>{yesNo(evidenceIntake.rollup.self_signed_records_accepted)}</code>
            </li>
            <li>
              <span>First real record</span>
              <code>{yesNo(evidenceIntake.rollup.first_real_external_record_present)}</code>
            </li>
          </ul>
        </article>
        <article>
          <p className="eyebrow">Public Evidence Dossier</p>
          <h3>{validationCampaign.public_evidence_dossier.status}</h3>
          <ul className="external-proof-list">
            <li>
              <span>Marketing claim surface</span>
              <code>{yesNo(validationCampaign.public_evidence_dossier.marketing_claim_surface)}</code>
            </li>
            <li>
              <span>Certification language</span>
              <code>{yesNo(validationCampaign.public_evidence_dossier.certification_language_allowed)}</code>
            </li>
            <li>
              <span>Proof promotion auto</span>
              <code>{yesNo(validationCampaign.proof_promotion_review.automatic_claim_promotion_allowed)}</code>
            </li>
          </ul>
        </article>
      </section>

      <section className="external-proof-two-column">
        <article>
          <p className="eyebrow">Capsule Qualification</p>
          <h3>Qualification complete: {yesNo(capsuleQualification.rollup.qualification_complete)}</h3>
          <ul className="external-proof-list">
            {firstTests.map((test) => (
              <li key={String(test.test_id)}>
                <span>{String(test.test_id)}</span>
                <code>{String(test.status)}</code>
              </li>
            ))}
          </ul>
        </article>
        <article>
          <p className="eyebrow">Repo Analytic Cross-checks</p>
          <h3>{physicsComparison.comparison_status}</h3>
          <ul className="external-proof-list">
            {firstChecks.map((check) => (
              <li key={check.check_id}>
                <span>{check.check_id}</span>
                <code>{check.status}</code>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="external-proof-section">
        <p className="eyebrow">Blocked Claims</p>
        <h3>Still not unlocked</h3>
        <div className="claim-chip-row">
          {blockers.map((claim) => (
            <span key={claim} className="claim-chip">
              {claim}
            </span>
          ))}
        </div>
      </section>
    </main>
  );
}
