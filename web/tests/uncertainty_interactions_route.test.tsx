import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import UncertaintyInteractionsRoute from "../src/pages/UncertaintyInteractionsRoute";

describe("UncertaintyInteractionsRoute", () => {
  it("renders tracked pairwise interactions without claiming correlation closure", () => {
    const html = renderToStaticMarkup(
      <UncertaintyInteractionsRoute navigate={() => undefined} route={{ kind: "uncertainty-interactions" }} />,
    );

    expect(html).toContain("Uncertainty Interactions");
    expect(html).toContain("Pairwise Stress Screen");
    expect(html).toContain("external_correlation_evidence_required");
    expect(html).toContain("External Evidence Still Required");
    expect(html).toContain("validated uncertainty independence");
  });
});
