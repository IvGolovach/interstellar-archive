# DAG_V2_BOUNDARY_SPEC_v1

## 1. Intent

Mission DAG v2 boundary turns roadmap item 11 into a generated, validated module-boundary artifact.
It does not replace the v1 DAG runner.
It documents the exact upgrade contract needed before any module can be described as an independent physics backend.

The artifact is a review surface.
It is not an independent-backend validation, high-fidelity state trace, flight-readiness claim, or external reproduction result.

## 2. Artifact Contract

Expected artifact: `artifacts/mission_dag_v2_boundary.v1.json`

Expected builder: `scripts/build_mission_dag_v2_boundary_artifact.py`

Expected validator: `scripts/ci/mission_dag_v2_boundary_validate.py`

Top-level requirements:

| field | requirement |
| --- | --- |
| `schema_version` | Must equal `mission_dag_v2_boundary.v1`. |
| `non_certification_notice` | Must be `true`. |
| `source_artifacts` | Must hash the DAG registry, scenario, taxonomy, schema, runner, and validator inputs. |
| `module_count` | Must equal the module registry module count. |
| `module_boundaries` | Must include one row for every module in `mission/dag/registry/module_registry.v1.json`. |
| `rollup` | Must expose v1 wrapper status and v2 readiness booleans without claiming independent backend closure. |
| `blocked_claims` | Must block independent-backend, high-fidelity-trace, flight-ready, and external-reproduction overclaims. |

## 3. Per-Module Boundary Fields

Each `module_boundaries[]` row must include:

- `module_id`, `module_type`, `module_version`, `domain`
- `entrypoint`
- `input_schema_ref`, `output_schema_ref`
- `scenario_node_ids`
- `failure_taxonomy_ids`
- `current_v1_support`
- `v2_boundary_requirements`
- `open_external_evidence_gaps`
- `blocked_claims`

## 4. Required v2 Boundary Requirements

Every module must carry these requirements:

- independent backend id
- state trace hash
- input/output schema version
- failure taxonomy mapping
- replayable module fixture
- cross-backend comparison report

## 5. Required Boundaries

The artifact must not support these claims:

- independent physics backend validated,
- high-fidelity state trace complete,
- flight-ready module approved,
- external backend reproduction completed.

Acceptable language:

- module-boundary contract,
- v1 wrapper with v2 readiness gaps,
- hashchained artifact expectations,
- external evidence still required.
