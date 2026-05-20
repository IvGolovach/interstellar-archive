import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import EvidenceCampaignRoute from "../src/pages/EvidenceCampaignRoute";

describe("EvidenceCampaignRoute", () => {
  it("renders public evidence-upgrade priorities without claiming trust closure", () => {
    const html = renderToStaticMarkup(
      <EvidenceCampaignRoute navigate={() => undefined} route={{ kind: "evidence-campaign" }} />,
    );

    expect(html).toContain("Evidence Upgrade Campaign");
    expect(html).toContain("Public Top Priorities");
    expect(html).toContain("Open artifact JSON");
    expect(html).toContain("External Evidence Still Required");
    expect(html).toContain("trust grades upgraded automatically");
    expect(html).not.toContain("code_literal.");
  });
});
