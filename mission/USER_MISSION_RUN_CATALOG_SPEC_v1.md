# User Mission Run Catalog v1

This spec defines `artifacts/user_mission_run_catalog.v1.json`,
`artifacts/runtime_scenario_generation.v1.json`, and the local review-pack
output from `scripts/run_user_mission_scenario.py`.

The catalog is a deterministic run-store contract over reviewed assumptions. It
must not be treated as a launch architecture, procurement estimate, mission
approval, hardware qualification, or guaranteed archive-recovery record.

## Artifact Contract

| Field | Requirement |
|---|---|
| `schema_version` | Must equal `user_mission_run_catalog.v1`. |
| `generator` | Must equal `scripts/build_user_mission_run_catalog_artifact.py`. |
| `public_scope` | Must equal `user_selected_mission_run_catalog`. |
| `non_certification_notice` | Must be `true`. |
| `run_count` | Must equal `15`, matching the Mission Feasibility Screen target/velocity matrix. |
| `default_run_id` | Must reference the reference black-hole / 45.32 km/s row. |
| `run_rows[]` | Must expose stable `run_id`, `selection_hash`, source refs, risk snapshot, blockers, external evidence gaps, blocked claims, and local runtime-pack template. |

## Runtime Generation Contract

`artifacts/runtime_scenario_generation.v1.json` is the review surface for item
12. It must expose the allowed target/velocity/mode/seed/run-id inputs,
artifact-provided command previews, expected pack files, source hashes, and
browser execution policy.

The browser may render the recipe and compiled-scenario preview. It must not
execute mission physics, mutate tracked files, or claim remote execution.

In v1, selected velocity is catalog and review metadata: it shapes the
feasibility row, flight-time row, and linked risk snapshot. The compiled
`MISSION_SCHEMA_v1` scenario only patches the target distance, mission mode,
seed, and dust-flux scale. Any stronger velocity-coupled runtime physics needs a
future schema version.

## Local Review Pack Contract

`scripts/run_user_mission_scenario.py` writes local, ignored-by-default review
packs under `ops/reports/user-mission-runs/<run-id>/`:

- `USER_RUN_SUMMARY.json`
- `COMPILED_MISSION_SCENARIO.json`
- `DAG_RUN_SUMMARY.json`
- `SOURCE_MANIFEST.json`
- `RUN_REPORT.md`
- `meta.json`

The pack must be deterministic for the same target, velocity, commit, and source
artifacts. It compiles the selection into `MISSION_SCHEMA_v1`, runs the existing
Mission DAG v1 wrapper modules, and records the DAG manifest/hashchain status.
It is evidence of the selected repository assumptions only.

`scripts/ci/user_mission_run_pack_validate.py` is the strict pack gate. It builds
the default selected run in an isolated temporary output root and checks the
expected file set, summary schema, source manifest, mission schema compatibility,
DAG status, hashchain status, and deterministic verdict. It must not track the
pack in git.

## Claim Boundary

Valid catalog rows can say: selected target, selected velocity, derived
ballistic flight time, source artifact hashes, capsule-risk snapshot, evidence
gaps, and blocked claims.

They cannot say: mission feasible, flight ready, certified survival, procurement
ready, or guaranteed archive recovery.
