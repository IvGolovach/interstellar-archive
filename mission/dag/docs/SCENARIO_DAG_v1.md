# Scenario DAG v1

`mission/dag/scenarios/mission_dag_baseline.v1.json` defines a topologically ordered mission DAG over module nodes.

## Contract

- DAG nodes reference `module_id` entries from `mission/dag/registry/module_registry.v1.json`.
- `depends_on` references must exist.
- Cycles are forbidden.
- Runner supports scenario mode: `realistic`, `speculative`, or `dual`.
- In `dual` mode, the full DAG is executed twice with strict isolation.

## Determinism

Given identical:

- DAG scenario
- module registry
- taxonomy registry
- seed
- mission baseline inputs

the runner produces identical per-module artifact hashes and identical manifest hash.

## Artifacts

Per run, runner writes:

- `modules/<mode>/<node_id>.json`
- `hashchain.jsonl`
- `manifest.json`
- summary/proof files via `scripts/run_mission_dag.py`
