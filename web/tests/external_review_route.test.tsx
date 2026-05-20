import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import ExternalReviewRoute from "../src/pages/ExternalReviewRoute";

describe("external review route", () => {
  it("renders the committed review-pack contract without claiming external validation", () => {
    const html = renderToStaticMarkup(
      <ExternalReviewRoute navigate={() => undefined} route={{ kind: "external-review" }} />,
    );

    expect(html).toContain("External Validation Review Pack");
    expect(html).toContain("third-party validated");
    expect(html).toContain("external_required");
    expect(html).not.toContain("fetch(");
  });
});
