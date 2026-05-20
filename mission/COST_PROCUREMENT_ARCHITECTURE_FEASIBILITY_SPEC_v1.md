# Cost, Procurement, and Architecture Feasibility Spec v1

This spec turns roadmap item 13 into a deterministic repository-native artifact.

The artifact is a screening contract. It does not claim a procurement-grade estimate, vendor quote, launch-vehicle selection, approved budget, regulatory approval, qualified hardware, mission feasibility, or flight-ready architecture.

## Source Inputs

- `artifacts/mission_feasibility_screen.v1.json`
- `artifacts/optimization_v2_frontier.v1.json`
- `artifacts/optimization_search_space.v1.json`
- `artifacts/capsule_survivability_lab.v1.json`
- `mission/COST_PROCUREMENT_ARCHITECTURE_FEASIBILITY_SPEC_v1.md`
- `docs/FULL_V2_ROADMAP_CLOSURE.md`

## Required Artifact

The builder writes `artifacts/cost_procurement_architecture_feasibility.v1.json`.

The artifact must expose:

- a cost model section with proxy values only,
- procurement gates whose status remains `external_required`,
- 15 architecture rows aligned to the mission feasibility screen,
- an optimization cost-axis summary aligned to Optimization v2,
- rollup booleans that keep procurement, launch selection, qualification, and flight architecture approval false,
- blocked claims and interpretation limits.

## Validator Boundary

The validator must fail if:

- `non_certification_notice` is not true,
- any procurement gate stops being `external_required`,
- a row claims a procurement status other than `external_required`,
- a rollup field claims vendor quotes, launch selection, calibrated cost model, qualification completion, or flight architecture selection,
- blocked claims no longer include procurement-grade estimate and flight-ready architecture boundaries,
- source hashes drift from committed source inputs.

## Browser Boundary

Browser UI may render committed artifact fields.
It must not compute cost, procurement status, launch selection, or architecture feasibility client-side.
