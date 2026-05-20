import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PUBLIC_DATASET_PATHS } from "../src/lib/artifact_public_contracts";
import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import { ObjectiveContractPanel } from "../src/ui/drilldown/ObjectiveContractPanel";

const dataset = loadParameterDrilldownDataset();

describe("objective contract UI smoke", () => {
  it("renders contract and baseline score from tracked artifacts", () => {
    const html = renderToStaticMarkup(
      <ObjectiveContractPanel
        contract={dataset.objectiveContract}
        baselineScore={dataset.objectiveScoreBaseline}
      />,
    );

    expect(html).toContain("Objective Contract / Baseline Score");
    expect(html).toContain(PUBLIC_DATASET_PATHS.objectiveContract);
    expect(html).toContain(PUBLIC_DATASET_PATHS.objectiveScoreBaseline);
    expect(html).toContain("no_D_grade_influence");
    expect(html).toContain("evidence_completeness_1.0");
    expect(html).toContain("p_success");
  });

  it("stays derived-only and does not fetch runtime truth", () => {
    const html = renderToStaticMarkup(
      <ObjectiveContractPanel
        contract={dataset.objectiveContract}
        baselineScore={dataset.objectiveScoreBaseline}
      />,
    );

    expect(html).not.toContain("fetch(");
    expect(html).toContain("rank_key");
    expect(html).toContain("lower_quantile");
  });
});
