import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import CostFeasibilityRoute from "../src/pages/CostFeasibilityRoute";

describe("cost feasibility route", () => {
  it("renders the committed screening contract without browser-side truth recompute", () => {
    const html = renderToStaticMarkup(
      <CostFeasibilityRoute navigate={() => undefined} route={{ kind: "cost-feasibility" }} />,
    );

    expect(html).toContain("Cost, Procurement &amp; Architecture");
    expect(html).toContain("screening proxy only");
    expect(html).toContain("external_required");
    expect(html).toContain("procurement-grade cost estimate");
    expect(html).not.toContain("fetch(");
  });
});
