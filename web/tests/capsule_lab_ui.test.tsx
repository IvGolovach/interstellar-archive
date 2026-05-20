import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PUBLIC_DATASET_PATHS } from "../src/lib/artifact_public_contracts";
import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_dataset";
import { CapsuleLab } from "../src/ui/capsule/CapsuleLab";
import {
  buildCapsuleLookup,
  findCapsuleRows,
  getCapsuleRiskBudgetAttackModes,
  pickCapsuleRiskBudgetRow,
  type CapsuleRiskBudgetArtifact,
  pickCapsuleRow,
} from "../src/ui/capsule/capsule_lab_contract";

describe("capsule lab UI", () => {
  const artifact = loadParameterDrilldownDataset().capsuleSurvivabilityLab;
  const capsuleRowId = "cap-row-reference-black-hole-ballistic-arrival-conditional-45-baseline-stack";
  const riskBudgetArtifact: CapsuleRiskBudgetArtifact = {
    schema_version: "capsule_risk_budget.v1",
    non_certification_notice: true,
    source_artifact_ref: PUBLIC_DATASET_PATHS.capsuleSurvivabilityLab,
    sample_count: 12000,
    attack_modes: [
      {
        attack_mode_id: "nominal",
        label: "Nominal evidence",
        description: "Baseline evidence posture from the committed artifact.",
      },
      {
        attack_mode_id: "severe_dust",
        label: "Severe dust",
        description: "Dust-tail stress case for impact and shielding assumptions.",
      },
    ],
    risk_budgets: [
      {
        row_id: capsuleRowId,
        attack_mode_id: "nominal",
        monte_carlo: {
          p05: 0.18,
          p50: 0.44,
          p95: 0.67,
          confidence_level: 0.9,
        },
        risk_budget: {
          status: "inside_budget",
          survival_probability: 0.44,
          data_integrity_probability: 0.73,
          loss_probability: 0.56,
          margin: 0.08,
        },
        uncertainty_drivers: [
          {
            label: "Dust density tail",
            contribution: 0.41,
            direction: "dominates downside",
          },
          {
            label: "Media retention half-life",
            contribution: 0.29,
            direction: "widens data-integrity interval",
          },
        ],
        failure_mode_contributions: [
          {
            label: "Hypervelocity dust penetration",
            contribution: 0.36,
            note: "Largest public-mode loss contributor.",
          },
        ],
        required_improvements: [
          {
            label: "Increase shield margin",
            threshold: "shield_margin >= 1.20",
            rationale: "Moves the selected row into the committed budget band.",
          },
        ],
        qualification_roadmap: [
          {
            label: "Full-stack dust impact coupon campaign",
            status: "required",
            evidence_needed: "Public artifact should cite measured stack-level impact survival.",
          },
        ],
      },
      {
        row_id: capsuleRowId,
        attack_mode_id: "severe_dust",
        monte_carlo: {
          p05: 0.07,
          p50: 0.24,
          p95: 0.49,
          confidence_level: 0.9,
        },
        risk_budget: {
          status: "over_budget",
          survival_probability: 0.24,
          data_integrity_probability: 0.52,
          loss_probability: 0.76,
          margin: -0.12,
        },
        uncertainty_drivers: [
          {
            label: "Interstellar dust flux tail",
            contribution: 0.57,
            direction: "dominates severe mode",
          },
        ],
        failure_mode_contributions: [
          {
            label: "Shield penetration",
            contribution: 0.51,
          },
        ],
        required_improvements: [
          {
            label: "Dust shield qualification",
            threshold: "penetration_loss <= 0.18",
          },
        ],
        qualification_roadmap: [
          {
            label: "Severe dust mode review",
            status: "open",
          },
        ],
      },
    ],
  };

  it("renders controls and artifact-backed survival outputs from the generated contract", () => {
    const html = renderToStaticMarkup(
      <CapsuleLab artifact={artifact} artifactPath={PUBLIC_DATASET_PATHS.capsuleSurvivabilityLab} />,
    );

    expect(html).toContain("Capsule Survivability Lab");
    expect(html).toContain(PUBLIC_DATASET_PATHS.capsuleSurvivabilityLab);
    expect(html).toContain("Target");
    expect(html).toContain("Time");
    expect(html).toContain("Velocity");
    expect(html).toContain("Capsule");
    expect(html).toContain("Survival probability");
    expect(html).toContain("P05 / P95 survival");
    expect(html).toContain("Data intact likelihood");
    expect(html).toContain("Open selected row JSON");
  });

  it("renders attack-mode risk budget panels from an optional v2 artifact fixture", () => {
    const html = renderToStaticMarkup(
      <CapsuleLab
        artifact={artifact}
        artifactPath={PUBLIC_DATASET_PATHS.capsuleSurvivabilityLab}
        riskBudgetArtifact={riskBudgetArtifact}
        riskBudgetArtifactPath="artifacts/capsule_risk_budget.v1.json"
      />,
    );

    expect(html).toContain("artifacts/capsule_risk_budget.v1.json");
    expect(html).toContain("Attack mode");
    expect(html).toContain("Nominal evidence");
    expect(html).toContain("Severe dust");
    expect(html).toContain("Monte Carlo interval");
    expect(html).toContain("P05 / P50 / P95");
    expect(html).toContain("18.0% / 44.0% / 67.0%");
    expect(html).toContain("Risk budget");
    expect(html).toContain("inside_budget");
    expect(html).toContain("Top uncertainty drivers");
    expect(html).toContain("Dust density tail");
    expect(html).toContain("41.0%");
    expect(html).toContain("Failure mode contribution");
    expect(html).toContain("Hypervelocity dust penetration");
    expect(html).toContain("Required improvements");
    expect(html).toContain("shield_margin &gt;= 1.20");
    expect(html).toContain("Qualification roadmap");
    expect(html).toContain("Full-stack dust impact coupon campaign");
  });

  it("builds stable lookups for row and option resolution", () => {
    const lookup = buildCapsuleLookup(artifact);

    expect(
      lookup.rowsById.get("cap-row-reference-black-hole-ballistic-arrival-conditional-45-baseline-stack")
        ?.output.outcomeBand,
    ).toBe("stressed");
    expect(lookup.options.targetsById.get("reference-black-hole")?.label).toBe("Reference black-hole candidate");
    expect(lookup.options.capsuleProfilesById.get("reinforced-media")?.label).toBe("Reinforced media sensitivity stack");
  });

  it("selects an exact committed row when a control patch has a matching artifact row", () => {
    const current = artifact.rows.find(
      (row) => row.rowId === "cap-row-reference-black-hole-ballistic-arrival-conditional-45-baseline-stack",
    );
    expect(current).toBeDefined();

    const next = pickCapsuleRow(artifact.rows, current!, {
      capsuleId: "reinforced-media",
    });

    expect(next.rowId).toBe("cap-row-reference-black-hole-ballistic-arrival-conditional-45-reinforced-media");
    expect(next.output.survivalProbability).toBeGreaterThan(current!.output.survivalProbability);
  });

  it("selects committed rows without computing new values", () => {
    const current = artifact.rows.find(
      (row) => row.rowId === "cap-row-alpha-centauri-scale-ten-myr-oberth-23-baseline-stack",
    );
    expect(current).toBeDefined();

    const next = pickCapsuleRow(artifact.rows, current!, {
      velocityId: "concept-95",
    });

    expect(next.rowId).toBe("cap-row-alpha-centauri-scale-ten-myr-concept-95-baseline-stack");
    expect(findCapsuleRows(artifact.rows, { velocityId: "concept-95" })).toHaveLength(24);
  });

  it("selects attack-mode risk budget rows without recomputing artifact values", () => {
    const modes = getCapsuleRiskBudgetAttackModes(riskBudgetArtifact, capsuleRowId);
    const current = pickCapsuleRiskBudgetRow(riskBudgetArtifact, {
      capsuleRowId,
      attackModeId: "nominal",
    });
    const severe = pickCapsuleRiskBudgetRow(riskBudgetArtifact, {
      capsuleRowId,
      attackModeId: "severe_dust",
    });

    expect(modes.map((mode) => mode.id)).toEqual(["nominal", "severe_dust"]);
    expect(current?.risk_budget?.survival_probability).toBe(0.44);
    expect(severe?.monte_carlo?.p05).toBe(0.07);
    expect(severe?.risk_budget?.status).toBe("over_budget");
  });
});
