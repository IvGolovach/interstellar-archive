import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { buildRouteHash, parseHashRoute, routeTitle } from "../src/app/app_routes";
import CapsuleLabRoute from "../src/pages/CapsuleLabRoute";

describe("capsule lab route", () => {
  it("parses and builds the capsule lab route", () => {
    expect(parseHashRoute("#/capsule-lab")).toEqual({ kind: "capsule-lab" });
    expect(parseHashRoute("#/capsule")).toEqual({ kind: "capsule-lab" });
    expect(buildRouteHash({ kind: "capsule-lab" })).toBe("#/capsule-lab");
    expect(routeTitle({ kind: "capsule-lab" })).toBe("Capsule Lab");
  });

  it("renders the route from the generated artifact contract", () => {
    const html = renderToStaticMarkup(
      <CapsuleLabRoute navigate={() => undefined} route={{ kind: "capsule-lab" }} />,
    );

    expect(html).toContain("Capsule Survivability Lab");
    expect(html).toContain("Artifact contract");
  });

  it("renders the committed risk budget artifact on the route", () => {
    const html = renderToStaticMarkup(
      <CapsuleLabRoute navigate={() => undefined} route={{ kind: "capsule-lab" }} />,
    );

    expect(html).toContain("artifacts/capsule_risk_budget.v1.json");
    expect(html).toContain("Risk budget");
    expect(html).toContain("Attack mode");
  });
});
