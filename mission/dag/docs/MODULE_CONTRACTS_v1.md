# Module Contracts v1

The Mission DAG layer exposes six module contracts:

1. `TrajectoryModule`
2. `EnvironmentModule`
3. `ShieldingModule`
4. `ThermalModule`
5. `ControlWindowModule`
6. `DataIntegrityModule`

Each node emits the same envelope (`mission/dag/schema/module_io.schema.v1.json`) with deterministic hashes, explicit mode (`realistic` or `speculative`), and module-level failure metadata.

v1 is wrapper-based: modules map to deterministic baseline mission computations and derived proxies, not to independent new physics engines.

## Required output fields

- `module_id`, `module_type`, `module_version`
- `mode`
- `inputs_hash`, `outputs_hash`
- `event_clock_domain=event`
- `wall_clock_recorded=true`
- `outputs` (type-specific payload)
- `failure` block with status/taxonomy metadata

## Failure contract

If `failure.status != PASS`, then:

- `failure.failure_mode` must be a known taxonomy ID from `mission/dag/registry/failure_taxonomy.v1.json`.
- `failure.failure_stage` must be one of `S0..S3`.
- `dominant_driver_parameter_ids` must list at least one parameter id.

This is enforced by schema + runtime validation.
