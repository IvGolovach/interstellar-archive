# OPTIMIZATION_V2_SPEC_v1

## 1. Intent

Optimization v2 turns the roadmap item into a generated, validated decision surface.
It wraps the existing deterministic realistic frontier and adds two bounded review axes:

- `qualification_gap`
- `cost_proxy`

The artifact is a screening surface.
It is not a global optimum proof, procurement estimate, hardware qualification result, or mission-readiness claim.

## 2. Artifact Contract

Expected artifact: `artifacts/optimization_v2_frontier.v1.json`

Expected builder: `scripts/build_optimization_v2_artifact.py`

Expected validator: `scripts/ci/optimization_v2_validate.py`

Top-level requirements:

| field | requirement |
| --- | --- |
| `schema_version` | Must equal `optimization_v2_frontier.v1`. |
| `mode` | Must equal `realistic`. |
| `non_certification_notice` | Must be `true`. |
| `source_artifacts` | Must hash the objective, risk, frontier, feasibility, risk-budget, and evidence-campaign inputs. |
| `axis_contract` | Must declare four Pareto axes and their direction. |
| `candidates` | Must map one-to-one to the source realistic frontier candidates. |
| `pareto_frontier_candidate_ids` | Must be recomputable from all four axes. |
| `blocked_claims` | Must block optimum, cost, qualification, and flight-readiness overclaims. |

## 3. Axis Contract

| axis | direction | status | source |
| --- | --- | --- | --- |
| `p_success` | maximize | computed | `artifacts/optimization_frontier_realistic.v1.json` |
| `risk_envelope` | minimize | computed | `mission/objectives/risk_envelope.v1.json` |
| `qualification_gap` | minimize | screening proxy | `parameters/registry/parameter_claims.v1.json` |
| `cost_proxy` | minimize | screening proxy | `artifacts/optimization_search_space.v1.json` |

Aggregation must be `pareto_first_no_hidden_weighted_sum`.
The artifact may use weights inside a single disclosed proxy formula, but it must not collapse all four axes into a hidden scalar utility for candidate ranking.

## 4. Proxy Semantics

`qualification_gap` is a trust/evidence screen.
It combines trust grade penalties with search-space excursion from baseline values.
It does not mean a candidate is qualified or unqualified in hardware terms.

`cost_proxy` is an engineering-resource pressure screen over deterministic mission parameters such as correction delta-v, power, specific impulse, duration, and target distance.
It does not mean launch, procurement, operations, or manufacturing cost has been estimated.

## 5. Required Boundaries

The artifact must not support these claims:

- global optimum proven,
- procurement-grade cost estimate,
- qualification complete,
- flight-ready design selected.

Acceptable language:

- deterministic four-axis decision surface,
- reduced-order screening proxy,
- Pareto-first review aid,
- external evidence still required.
