import { describe, expect, it } from "vitest";

import {
  loadParameterDrilldownDataset,
  validateDynamicTraceAgainstStatic,
  type DynamicTraceIndex,
} from "../src/lib/parameter_drilldown_loader";

describe("parameter drilldown artifacts", () => {
  it("loads public mission-parameter dataset with static/evidence integrity", () => {
    const dataset = loadParameterDrilldownDataset();

    expect(dataset.errors).toEqual([]);
    expect(dataset.manifest.public_scope).toBe("public_mission_parameters_only");
    expect(dataset.manifest.ui_scope).toBe("mission_design_environment_only");
    expect(dataset.manifest.excluded_internal_parameter_count).toBeGreaterThan(0);
    expect(dataset.manifest.internal_parameter_prefixes_excluded).toContain("code_literal.");
    expect(dataset.pSuccessDefensibility.formula).toBe("p_hit * p_survival * p_data_intact");
    expect(dataset.pSuccessDefensibility.uncertainty_propagation).toBe("MonteCarlo");
    expect(dataset.failureSurfaceBaseline.schema_version).toBe("failure_surface.v1");
    expect(dataset.objectiveContract.schema_version).toBe("objective_contract.v1");
    expect(dataset.objectiveScoreBaseline.schema_version).toBe("objective_score.v1");
    expect(dataset.optimizationSearchSpace.schema_version).toBe("optimization_search_space.v1");
    expect(dataset.optimizationFrontier.schema_version).toBe("optimization_frontier.v1");
    expect(dataset.optimizationV2.schema_version).toBe("optimization_v2_frontier.v1");
    expect(dataset.objectiveScoreBaseline.contract_ref).toBe("mission/objectives/objective_contract.v1.json");
    expect(dataset.optimizationSearchSpace.objective_contract_ref).toBe("mission/objectives/objective_contract.v1.json");
    expect(dataset.optimizationFrontier.objective_contract_ref).toBe("mission/objectives/objective_contract.v1.json");
    expect(dataset.objectiveScoreBaseline.scores.realistic.objective_vector).toHaveLength(2);
    expect(dataset.objectiveScoreBaseline.scores.speculative.objective_vector).toHaveLength(1);
    expect(dataset.optimizationSearchSpace.mode).toBe("realistic");
    expect(dataset.optimizationFrontier.mode).toBe("realistic");
    expect(dataset.optimizationV2.mode).toBe("realistic");
    expect(dataset.optimizationFrontier.evaluation_count).toBe(dataset.optimizationFrontier.points.length);
    expect(dataset.optimizationFrontier.points.length).toBeGreaterThan(0);
    expect(dataset.optimizationV2.rollup.axis_ids).toEqual([
      "p_success",
      "risk_envelope",
      "qualification_gap",
      "cost_proxy",
    ]);
    expect(dataset.optimizationV2.rollup.global_optimum_claimed).toBe(false);
    expect(dataset.optimizationV2.rollup.qualification_complete).toBe(false);
    expect(dataset.optimizationV2.blocked_claims).toContain("procurement-grade cost estimate");
    expect(
      dataset.optimizationV2.candidates.every((candidate) =>
        candidate.dominant_drivers.parameter_ids.every(
          (parameterId) => !parameterId.startsWith("code_literal."),
        ),
      ),
    ).toBe(true);
    expect(dataset.failureSurfaceBaseline.timeline.map((item) => item.stage)).toEqual(["S0", "S1", "S2", "S3"]);
    expect(dataset.failureSurfaceBaseline.dominant_drivers.top3).toHaveLength(3);
    expect(dataset.userMissionRunCatalog.schema_version).toBe("user_mission_run_catalog.v1");
    expect(dataset.userMissionRunCatalog.run_count).toBe(15);
    expect(dataset.userMissionRunCatalog.default_run_id).toContain("reference-black-hole-conditional-45");
    expect(dataset.runtimeScenarioGeneration.schema_version).toBe("runtime_scenario_generation.v1");
    expect(dataset.runtimeScenarioGeneration.generation_row_count).toBe(15);
    expect(dataset.runtimeScenarioGeneration.rollup.rows_writing_tracked_files).toBe(0);
    expect(dataset.evidenceUpgradeCampaign.schema_version).toBe("evidence_upgrade_campaign.v1");
    expect(dataset.evidenceUpgradeCampaign.claim_count).toBe(66);
    expect(dataset.evidenceUpgradeCampaign.public_campaign_count).toBe(31);
    expect(dataset.evidenceUpgradeCampaign.internal_audit_count).toBe(35);
    expect(dataset.evidenceUpgradeCampaign.public_top_priorities.length).toBeGreaterThan(0);
    expect(
      dataset.evidenceUpgradeCampaign.public_top_priorities.every(
        (row) => !row.parameter_id.startsWith("code_literal."),
      ),
    ).toBe(true);
    expect(dataset.evidenceUpgradeCampaign.blocked_claims).toContain("trust grades upgraded automatically");
    expect(dataset.missionDagV2Boundary.schema_version).toBe("mission_dag_v2_boundary.v1");
    expect(dataset.missionDagV2Boundary.module_count).toBe(6);
    expect(dataset.missionDagV2Boundary.rollup.independent_backend_complete).toBe(false);
    expect(dataset.missionDagV2Boundary.blocked_claims).toContain("independent physics backend validated");
    expect(dataset.externalValidationReviewPack.schema_version).toBe("external_validation_review_pack.v1");
    expect(dataset.externalValidationReviewPack.review_case_count).toBe(7);
    expect(dataset.externalValidationReviewPack.rollup.external_validation_claimed).toBe(false);
    expect(dataset.externalValidationReviewPack.blocked_claims).toContain("third-party validated");
    expect(dataset.publicNarrativeHardening.schema_version).toBe("public_narrative_hardening.v1");
    expect(dataset.publicNarrativeHardening.rollup.unsafe_public_overclaim_count).toBe(0);
    expect(dataset.publicNarrativeHardening.rollup.external_wording_audit_completed).toBe(false);
    expect(dataset.publicNarrativeHardening.forbidden_public_claims).toContain("certified");
    expect(dataset.publicNarrativeHardening.forbidden_public_claims).toContain("external validation completed");
    expect(dataset.publicNarrativeHardening.required_public_concepts).toContain("non-certifying");
    expect(dataset.externalValidationExecutionLedger.schema_version).toBe("external_validation_execution_ledger.v1");
    expect(dataset.externalValidationExecutionLedger.execution_record_count).toBe(0);
    expect(dataset.externalValidationExecutionLedger.rollup.external_validation_completed).toBe(false);
    expect(dataset.independentPhysicsBackendComparison.schema_version).toBe("independent_physics_backend_comparison.v1");
    expect(dataset.independentPhysicsBackendComparison.analytic_check_count).toBeGreaterThanOrEqual(4);
    expect(dataset.independentPhysicsBackendComparison.rollup.independent_external_backend_complete).toBe(false);
    expect(dataset.capsuleQualificationEvidencePack.schema_version).toBe("capsule_qualification_evidence_pack.v1");
    expect(dataset.capsuleQualificationEvidencePack.mass_closure.configured_capsule_mass_kg).toBe(206);
    expect(dataset.capsuleQualificationEvidencePack.rollup.qualification_complete).toBe(false);
    expect(dataset.evidenceUpgradeClosure.schema_version).toBe("evidence_upgrade_closure.v1");
    expect(dataset.evidenceUpgradeClosure.rollup.trust_grade_promotion_count).toBe(0);
    expect(dataset.externalReproductionKit.schema_version).toBe("external_reproduction_kit.v1");
    expect(dataset.externalReproductionKit.review_case_count).toBe(7);
    expect(dataset.externalReproductionKit.rollup.export_cli_available).toBe(true);
    expect(dataset.externalReproductionKit.rollup.first_real_external_record_present).toBe(false);
    expect(dataset.externalEvidenceIntake.schema_version).toBe("external_evidence_intake.v1");
    expect(dataset.externalEvidenceIntake.record_count).toBe(0);
    expect(dataset.externalEvidenceIntake.accepted_record_count).toBe(0);
    expect(dataset.externalEvidenceIntake.rollup.first_real_external_record_present).toBe(false);
    expect(dataset.externalEvidenceIntake.validation_policy.reject_self_signed_repo_native_records).toBe(true);
    expect(dataset.externalValidationCampaign.schema_version).toBe("external_validation_campaign.v1");
    expect(dataset.externalValidationCampaign.workstream_count).toBe(6);
    expect(dataset.externalValidationCampaign.rollup.accepted_record_count).toBe(0);
    expect(dataset.externalValidationCampaign.rollup.external_validation_completed).toBe(false);
    expect(dataset.externalValidationCampaign.proof_promotion_review.automatic_claim_promotion_allowed).toBe(false);
    expect(dataset.releaseCandidateReadiness.schema_version).toBe("release_candidate_readiness.v1");
    expect(dataset.releaseCandidateReadiness.rollup.repo_publication_candidate_ready).toBe(true);
    expect(dataset.releaseCandidateReadiness.rollup.certification_go).toBe(false);
    expect(dataset.parameters.length).toBe(dataset.manifest.parameter_count);
    expect(dataset.parameters.length).toBeGreaterThan(0);
    expect(dataset.parameters.every((parameter) => !parameter.parameter_id.startsWith("code_literal."))).toBe(true);
    expect(Object.keys(dataset.staticUsageGraph).every((parameterId) => !parameterId.startsWith("code_literal."))).toBe(true);
    expect(Object.keys(dataset.evidenceIndex).every((parameterId) => !parameterId.startsWith("code_literal."))).toBe(true);
    expect(dataset.optimizationSearchSpace.excluded_internal_parameter_count).toBeGreaterThan(0);
    expect(dataset.optimizationSearchSpace.internal_parameter_prefixes_excluded).toContain("code_literal.");
    expect(
      dataset.optimizationSearchSpace.parameters_considered.every(
        (entry) => !entry.parameter_id.startsWith("code_literal."),
      ),
    ).toBe(true);
    expect(
      dataset.optimizationSearchSpace.excluded_parameters.every(
        (entry) => !entry.parameter_id.startsWith("code_literal."),
      ),
    ).toBe(true);

    for (const parameter of dataset.parameters) {
      expect(dataset.staticUsageGraph[parameter.parameter_id]).toBeTruthy();
      expect(dataset.evidenceIndex[parameter.parameter_id]).toBeTruthy();
      expect(parameter.evidence_status.status).toBe("OK");
      expect(parameter.has_source).toBe(true);
      expect(parameter.has_uncertainty).toBe(true);
      expect(parameter.defensibility_status).toBe("PASS");
    }
  });

  it("flags dynamic/static contract violations deterministically", () => {
    const dataset = loadParameterDrilldownDataset();
    const sampleParameter = dataset.parameters[0]?.parameter_id;
    expect(sampleParameter).toBeTruthy();

    const trace: DynamicTraceIndex = {
      run_id: "fixture-run",
      commit_sha: "abcdef0",
      mode: "realistic",
      seed: 1,
      scenario_path: "fixture",
      artifact_hash: "0".repeat(64),
      hashchain_verified: true,
      events: [
        {
          mode: "realistic",
          node_id: "node0",
          module_id: "unknown.module",
          inputs_hash: "1".repeat(64),
          outputs_hash: "2".repeat(64),
          failure_mode: null,
          dominant_driver_parameter_ids: [sampleParameter as string],
        },
      ],
    };

    const result = validateDynamicTraceAgainstStatic(trace, dataset.staticUsageGraph);
    expect(result.status).toBe("FAIL");
    expect(result.violation_count).toBe(1);
    expect(result.violations[0]?.reason).toContain("dynamic trace module not declared");
  });
});
