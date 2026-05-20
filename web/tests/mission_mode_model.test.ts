import { describe, expect, it } from "vitest";

import { loadParameterDrilldownDataset } from "../src/lib/parameter_drilldown_loader";
import type {
  OptimizationFrontierArtifact,
  OptimizationSearchSpaceArtifact,
} from "../src/lib/parameter_drilldown_loader";
import {
  buildMissionProjection,
  selectFrontierPointForParams,
} from "../src/ui/mission/mission_mode_model";

function buildSearchSpace(
  parameters: OptimizationSearchSpaceArtifact["parameters_considered"],
): OptimizationSearchSpaceArtifact {
  return {
    schema_version: "optimization_search_space.v1",
    objective_contract_ref: "mission/objectives/objective_contract.v1.json",
    mode: "realistic",
    seed: 1,
    trust_filter: "A-C",
    parameters_considered: parameters,
    excluded_parameters: [],
  };
}

function buildFrontier(
  points: OptimizationFrontierArtifact["points"],
): OptimizationFrontierArtifact {
  return {
    schema_version: "optimization_frontier.v1",
    objective_contract_ref: "mission/objectives/objective_contract.v1.json",
    engine_commit: "fixture",
    mode: "realistic",
    seed: 1,
    method: "fixture",
    dimensions: ["p_success", "risk_envelope"],
    evaluation_count: points.length,
    points,
    pareto_frontier_indices: points.map((_, index) => index),
    determinism_signature: "fixture-signature",
  };
}

describe("mission mode model", () => {
  it("returns null selection when the frontier or search-space is empty", () => {
    const emptySearchSpace = buildSearchSpace([]);
    const emptyFrontier = buildFrontier([]);

    expect(
      selectFrontierPointForParams({
        params: {},
        frontier: emptyFrontier,
        searchSpace: emptySearchSpace,
      }),
    ).toEqual({
      selectedCandidateId: null,
      selectedFrontierIndex: null,
    });
  });

  it("breaks equal-distance ties by candidate id", () => {
    const searchSpace = buildSearchSpace([
      {
        parameter_id: "alpha",
        bounds: [0, 10],
        baseline_value: 5,
        trust_grade: "A",
        domain: "realistic",
        affects_core_probability: true,
      },
    ]);
    const frontier = buildFrontier([
      {
        candidate_id: "b-candidate",
        parameters: { alpha: 4 },
        scores: {
          p_success: 0.3,
          objective_vector: [0.3, 0.2],
          rank_key: "b",
          risk_envelope: 0.2,
        },
        dominant_drivers: { method: "fixture", parameter_ids: ["alpha"] },
        constraint_status: {},
      },
      {
        candidate_id: "a-candidate",
        parameters: { alpha: 6 },
        scores: {
          p_success: 0.4,
          objective_vector: [0.4, 0.25],
          rank_key: "a",
          risk_envelope: 0.25,
        },
        dominant_drivers: { method: "fixture", parameter_ids: ["alpha"] },
        constraint_status: {},
      },
    ]);

    expect(
      selectFrontierPointForParams({
        params: { alpha: 5 },
        frontier,
        searchSpace,
      }),
    ).toEqual({
      selectedCandidateId: "a-candidate",
      selectedFrontierIndex: 1,
    });
  });

  it("falls back to baseline scores when no frontier selection is available", () => {
    const dataset = loadParameterDrilldownDataset();
    const searchSpace = buildSearchSpace([]);
    const frontier = buildFrontier([]);

    const projection = buildMissionProjection({
      params: {},
      baselineFailureSurface: dataset.failureSurfaceBaseline,
      baselineObjectiveScore: dataset.objectiveScoreBaseline,
      frontier,
      searchSpace,
    });

    expect(projection.selectedCandidateId).toBeNull();
    expect(projection.selectedFrontierIndex).toBeNull();
    expect(projection.projectedPSuccess).toBe(dataset.objectiveScoreBaseline.scores.realistic.p_success);
    expect(projection.projectedRiskEnvelope).toBe(dataset.objectiveScoreBaseline.scores.realistic.risk_envelope);
    expect(projection.dominantDrivers).toEqual(
      dataset.failureSurfaceBaseline.dominant_drivers.top3.map((entry) => entry.parameter_id),
    );
  });

  it("uses the selected frontier point when one is available", () => {
    const dataset = loadParameterDrilldownDataset();
    const searchSpace = buildSearchSpace([
      {
        parameter_id: "alpha",
        bounds: [0, 10],
        baseline_value: 5,
        trust_grade: "A",
        domain: "realistic",
        affects_core_probability: true,
      },
    ]);
    const frontier = buildFrontier([
      {
        candidate_id: "b-candidate",
        parameters: { alpha: 4 },
        scores: {
          p_success: 0.3,
          objective_vector: [0.3, 0.2],
          rank_key: "b",
          risk_envelope: 0.2,
        },
        dominant_drivers: { method: "fixture", parameter_ids: ["alpha"] },
        constraint_status: {},
      },
      {
        candidate_id: "a-candidate",
        parameters: { alpha: 6 },
        scores: {
          p_success: 0.4,
          objective_vector: [0.4, 0.25],
          rank_key: "a",
          risk_envelope: 0.25,
        },
        dominant_drivers: { method: "fixture", parameter_ids: ["alpha"] },
        constraint_status: {},
      },
    ]);

    const projection = buildMissionProjection({
      params: { alpha: 5 },
      baselineFailureSurface: dataset.failureSurfaceBaseline,
      baselineObjectiveScore: dataset.objectiveScoreBaseline,
      frontier,
      searchSpace,
    });

    expect(projection.selectedCandidateId).toBe("a-candidate");
    expect(projection.selectedFrontierIndex).toBe(1);
    expect(projection.projectedPSuccess).toBe(0.4);
    expect(projection.projectedRiskEnvelope).toBe(0.25);
  });
});
