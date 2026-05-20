import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import PublicNarrativeRoute from "../src/pages/PublicNarrativeRoute";

describe("public narrative route", () => {
  it("renders the committed public narrative artifact without claiming external audit completion", () => {
    const html = renderToStaticMarkup(
      <PublicNarrativeRoute navigate={() => undefined} route={{ kind: "public-narrative" }} />,
    );

    expect(html).toContain("Public Narrative Hardening");
    expect(html).toContain("unsafe public overclaim");
    expect(html).toContain("certified");
    expect(html).not.toContain("fetch(");
  });
});
