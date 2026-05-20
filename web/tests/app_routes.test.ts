import { describe, expect, it } from "vitest";

import {
  buildRouteHash,
  parseHashRoute,
  routeTitle,
} from "../src/app/app_routes";

describe("app routes", () => {
  it("parses default route and known hashes", () => {
    expect(parseHashRoute("")).toEqual({ kind: "mission" });
    expect(parseHashRoute("#/mission")).toEqual({ kind: "mission" });
    expect(parseHashRoute("#parameters")).toEqual({ kind: "parameters" });
    expect(parseHashRoute("#/parameters/alpha")).toEqual({
      kind: "parameter-detail",
      parameterId: "alpha",
    });
    expect(parseHashRoute("#/failure-surface")).toEqual({ kind: "failure-surface" });
    expect(parseHashRoute("#/optimization")).toEqual({ kind: "optimization", candidateId: undefined });
    expect(parseHashRoute("#/optimization-v2/optv2-pt-000")).toEqual({ kind: "optimization", candidateId: "optv2-pt-000" });
    expect(parseHashRoute("#/mission-feasibility")).toEqual({ kind: "mission-feasibility" });
    expect(parseHashRoute("#/feasibility")).toEqual({ kind: "mission-feasibility" });
    expect(parseHashRoute("#/mission-runs")).toEqual({ kind: "mission-runs", runId: undefined });
    expect(parseHashRoute("#/mission-runs/umr-1")).toEqual({ kind: "mission-runs", runId: "umr-1" });
    expect(parseHashRoute("#/cost-feasibility")).toEqual({ kind: "cost-feasibility" });
    expect(parseHashRoute("#/cost")).toEqual({ kind: "cost-feasibility" });
    expect(parseHashRoute("#/mission-probability")).toEqual({ kind: "mission-probability", couplingId: undefined });
    expect(parseHashRoute("#/probability/mpc-1")).toEqual({ kind: "mission-probability", couplingId: "mpc-1" });
    expect(parseHashRoute("#/uncertainty-interactions")).toEqual({ kind: "uncertainty-interactions", pairId: undefined });
    expect(parseHashRoute("#/uncertainty/ui-pair-1")).toEqual({ kind: "uncertainty-interactions", pairId: "ui-pair-1" });
    expect(parseHashRoute("#/evidence-campaign")).toEqual({ kind: "evidence-campaign", campaignId: undefined });
    expect(parseHashRoute("#/evidence/euc-1")).toEqual({ kind: "evidence-campaign", campaignId: "euc-1" });
    expect(parseHashRoute("#/dag-v2/traj.baseline.v1")).toEqual({ kind: "mission-dag-boundary", moduleId: "traj.baseline.v1" });
    expect(parseHashRoute("#/external-review")).toEqual({ kind: "external-review" });
    expect(parseHashRoute("#/review-pack")).toEqual({ kind: "external-review" });
    expect(parseHashRoute("#/external-proof")).toEqual({ kind: "external-proof" });
    expect(parseHashRoute("#/proof")).toEqual({ kind: "external-proof" });
    expect(parseHashRoute("#/public-narrative")).toEqual({ kind: "public-narrative" });
    expect(parseHashRoute("#/narrative")).toEqual({ kind: "public-narrative" });
    expect(parseHashRoute("#/roadmap-closure")).toEqual({ kind: "roadmap-closure" });
  });

  it("round-trips route hashes", () => {
    const routes = [
      { kind: "mission" as const },
      { kind: "parameters" as const },
      { kind: "parameter-detail" as const, parameterId: "trajectory_model.non_physical_capture_bias" },
      { kind: "failure-surface" as const },
      { kind: "optimization" as const, candidateId: undefined },
      { kind: "optimization" as const, candidateId: "optv2-pt-000" },
      { kind: "mission-feasibility" as const },
      { kind: "mission-runs" as const, runId: "umr-reference-black-hole-conditional-45-fixture" },
      { kind: "cost-feasibility" as const },
      { kind: "mission-probability" as const, couplingId: "mpc-reference-black-hole-conditional-45-fixture" },
      { kind: "uncertainty-interactions" as const, pairId: "ui-pair-fixture" },
      { kind: "evidence-campaign" as const, campaignId: "euc-fixture" },
      { kind: "mission-dag-boundary" as const, moduleId: "traj.baseline.v1" },
      { kind: "external-review" as const },
      { kind: "external-proof" as const },
      { kind: "public-narrative" as const },
      { kind: "roadmap-closure" as const },
    ];

    for (const route of routes) {
      expect(parseHashRoute(buildRouteHash(route))).toEqual(route);
    }
  });

  it("labels routes consistently", () => {
    expect(routeTitle({ kind: "mission" })).toBe("Mission");
    expect(routeTitle({ kind: "parameter-detail", parameterId: "x" })).toBe("Parameter Detail");
    expect(routeTitle({ kind: "mission-feasibility" })).toBe("Mission Feasibility");
    expect(routeTitle({ kind: "mission-runs" })).toBe("Mission Runs");
    expect(routeTitle({ kind: "cost-feasibility" })).toBe("Cost Feasibility");
    expect(routeTitle({ kind: "mission-probability" })).toBe("Mission Probability");
    expect(routeTitle({ kind: "uncertainty-interactions" })).toBe("Uncertainty Interactions");
    expect(routeTitle({ kind: "evidence-campaign" })).toBe("Evidence Campaign");
    expect(routeTitle({ kind: "mission-dag-boundary" })).toBe("DAG Boundary");
    expect(routeTitle({ kind: "external-review" })).toBe("External Review");
    expect(routeTitle({ kind: "external-proof" })).toBe("External Proof");
    expect(routeTitle({ kind: "public-narrative" })).toBe("Public Narrative");
    expect(routeTitle({ kind: "roadmap-closure" })).toBe("V2 Closure");
  });
});
