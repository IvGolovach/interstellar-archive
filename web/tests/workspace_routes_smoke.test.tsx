import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import MissionRoute from "../src/pages/MissionRoute";
import ParameterIndexRoute from "../src/pages/ParameterIndexRoute";
import ParameterDetailRoute from "../src/pages/ParameterDetailRoute";
import FailureSurfaceRoute from "../src/pages/FailureSurfaceRoute";
import OptimizationLabRoute from "../src/pages/OptimizationLabRoute";
import RoadmapClosureRoute from "../src/pages/RoadmapClosureRoute";
import MissionFeasibilityRoute from "../src/pages/MissionFeasibilityRoute";
import UserMissionRunRoute from "../src/pages/UserMissionRunRoute";
import CostFeasibilityRoute from "../src/pages/CostFeasibilityRoute";
import MissionProbabilityCouplingRoute from "../src/pages/MissionProbabilityCouplingRoute";
import UncertaintyInteractionsRoute from "../src/pages/UncertaintyInteractionsRoute";
import EvidenceCampaignRoute from "../src/pages/EvidenceCampaignRoute";
import MissionDagBoundaryRoute from "../src/pages/MissionDagBoundaryRoute";
import ExternalReviewRoute from "../src/pages/ExternalReviewRoute";
import ExternalProofRoute from "../src/pages/ExternalProofRoute";
import PublicNarrativeRoute from "../src/pages/PublicNarrativeRoute";

describe("workspace route pages", () => {
  it("renders the mission route", () => {
    const html = renderToStaticMarkup(
      <MissionRoute navigate={() => undefined} route={{ kind: "mission" }} />,
    );
    expect(html).toContain("Mission Mode");
  });

  it("renders the parameter index route", () => {
    const html = renderToStaticMarkup(
      <ParameterIndexRoute navigate={() => undefined} route={{ kind: "parameters" }} />,
    );
    expect(html).toContain("Parameter Index");
  });

  it("renders the parameter detail route", () => {
    const html = renderToStaticMarkup(
      <ParameterDetailRoute
        navigate={() => undefined}
        route={{ kind: "parameter-detail", parameterId: "trajectory_model.non_physical_capture_bias" }}
      />,
    );
    expect(html).toContain("Parameter Detail");
  });

  it("renders the failure surface route", () => {
    const html = renderToStaticMarkup(
      <FailureSurfaceRoute navigate={() => undefined} route={{ kind: "failure-surface" }} />,
    );
    expect(html).toContain("Failure Surface &amp; Breakdown");
  });

  it("renders the optimization lab route", () => {
    const html = renderToStaticMarkup(
      <OptimizationLabRoute navigate={() => undefined} route={{ kind: "optimization" }} />,
    );
    expect(html).toContain("Optimization Lab");
  });

  it("renders the roadmap closure route", () => {
    const html = renderToStaticMarkup(
      <RoadmapClosureRoute navigate={() => undefined} route={{ kind: "roadmap-closure" }} />,
    );
    expect(html).toContain("Full V2 Roadmap Closure");
    expect(html).toContain("15 repo-native closures");
  });

  it("renders the mission feasibility route", () => {
    const html = renderToStaticMarkup(
      <MissionFeasibilityRoute navigate={() => undefined} route={{ kind: "mission-feasibility" }} />,
    );
    expect(html).toContain("Mission Feasibility Screen");
    expect(html).toContain("External Evidence Still Required");
  });

  it("renders the user mission run route", () => {
    const html = renderToStaticMarkup(
      <UserMissionRunRoute navigate={() => undefined} route={{ kind: "mission-runs" }} />,
    );
    expect(html).toContain("Selected Mission Run");
    expect(html).toContain("Local Review Pack");
  });

  it("renders the cost feasibility route", () => {
    const html = renderToStaticMarkup(
      <CostFeasibilityRoute navigate={() => undefined} route={{ kind: "cost-feasibility" }} />,
    );
    expect(html).toContain("Cost, Procurement &amp; Architecture");
    expect(html).toContain("procurement-grade cost estimate");
  });

  it("renders the mission probability coupling route", () => {
    const html = renderToStaticMarkup(
      <MissionProbabilityCouplingRoute navigate={() => undefined} route={{ kind: "mission-probability" }} />,
    );
    expect(html).toContain("Mission Probability Coupling");
    expect(html).toContain("DAG Snapshot");
  });

  it("renders the uncertainty interactions route", () => {
    const html = renderToStaticMarkup(
      <UncertaintyInteractionsRoute navigate={() => undefined} route={{ kind: "uncertainty-interactions" }} />,
    );
    expect(html).toContain("Uncertainty Interactions");
    expect(html).toContain("Pairwise Stress Screen");
  });

  it("renders the evidence campaign route", () => {
    const html = renderToStaticMarkup(
      <EvidenceCampaignRoute navigate={() => undefined} route={{ kind: "evidence-campaign" }} />,
    );
    expect(html).toContain("Evidence Upgrade Campaign");
    expect(html).toContain("Public Top Priorities");
  });

  it("renders the mission DAG v2 boundary route", () => {
    const html = renderToStaticMarkup(
      <MissionDagBoundaryRoute navigate={() => undefined} route={{ kind: "mission-dag-boundary" }} />,
    );
    expect(html).toContain("Mission DAG v2 boundary");
    expect(html).toContain("independent physics backend validated");
  });

  it("renders the external review route", () => {
    const html = renderToStaticMarkup(
      <ExternalReviewRoute navigate={() => undefined} route={{ kind: "external-review" }} />,
    );
    expect(html).toContain("External Validation Review Pack");
    expect(html).toContain("independent reproduction completed");
  });

  it("renders the external proof route", () => {
    const html = renderToStaticMarkup(
      <ExternalProofRoute navigate={() => undefined} route={{ kind: "external-proof" }} />,
    );
    expect(html).toContain("External Proof Phase");
    expect(html).toContain("repo_publication_candidate_external_evidence_open");
  });

  it("renders the public narrative route", () => {
    const html = renderToStaticMarkup(
      <PublicNarrativeRoute navigate={() => undefined} route={{ kind: "public-narrative" }} />,
    );
    expect(html).toContain("Public Narrative Hardening");
    expect(html).toContain("unsafe public overclaim");
  });
});
