# Reproducibility Guide

## 0) Canonical repository check flow

The canonical full-suite entrypoints are:

```bash
make check
python3 scripts/ci/check_suite.py
```

Both commands run the same repository-wide validation flow.
`make check` is the short local entrypoint.
`python3 scripts/ci/check_suite.py` is the explicit entrypoint when CI or ad-hoc verification needs SHA overrides:

```bash
python3 scripts/ci/check_suite.py --base <BASE_SHA> --head <HEAD_SHA>
```

Remote proof validation is included when CI provides a proof bundle, or locally when you pass `--remote-proof-dir <path>` (or `REMOTE_PROOF_DIR=<path>` with `make check`).

Required documentation and registry files are validated from `docs/required_paths.v1.json`.
Repository navigation and artifact-boundary guidance live in:

- `docs/README.md`
- `docs/ARTIFACT_POLICY.md`

## 1) Python evidence golden run

`golden run` is the canonical deterministic scenario for the evidence pipeline. It regenerates the evidence pack and validates checksums.

### Quick start

```bash
git clone https://github.com/IvGolovach/interstellar-archive.git
cd interstellar-archive
make golden-run
```

Run all commands from repository root (`git rev-parse --show-toplevel`) to avoid path/import ambiguity.

Equivalent command:

```bash
python3 scripts/run_golden.py
```

By default, `run_golden.py` is non-mutating for tracked artifacts and uses a scratch workspace under `.tmp/`.
Use `python3 scripts/run_golden.py --refresh-tracked-artifacts` only when intentionally updating tracked evidence-pack files.

Expected checksum manifest:

`artifacts/evidence-pack-v1/checksums.sha256`

## 2) Web simulation golden run

The web simulation golden run is fixed to `sim/scenarios/default.v1.json` and must remain deterministic.

### Commands

```bash
npm ci --prefix web
npm run validate --prefix web
npm run golden:check --prefix web
```

Golden files:
- `sim/golden/golden_output.v1.json`
- `sim/golden/golden_checksum.txt`

Checksum rule:
- SHA-256 is computed over `SimOutput.checksum_payload` (canonical serialized output basis).
- `SimOutput.golden_checksum` must equal `sim/golden/golden_checksum.txt`.
- CI fails if recomputed checksum differs from committed golden checksum.

Browser-facing dataset contract:

```bash
python3 scripts/build_capsule_survivability_artifact.py
python3 scripts/ci/capsule_survivability_validate.py --strict
python3 scripts/build_browser_dataset_artifact.py
python3 scripts/ci/browser_dataset_validate.py --strict
```

Capsule Lab expected tracked output:
- `artifacts/capsule_survivability_lab.v1.json`

The capsule artifact must stay deterministic, expose a non-certification notice, and keep the default `reference-black-hole` + `conditional-45` + `ballistic-arrival` row near a 10 Myr flight horizon.

## Golden Integrity Contract

Golden checksum may change only when at least one model-evolution trigger is present:
1. Schema version increment (`sim_schema.vN -> sim_schema.vN+1`), OR
2. Engine version increment (`SIM_ENGINE_VERSION`), OR
3. `breaking_change_flag=true` in `sim/schema/sim_schema.v1.json`.

Additionally required for any golden checksum update:
1. `engineering/CHANGELOG.md` update with rationale.
2. `engineering/DECISIONS.md` update with rationale.

CI enforcement:
- if `sim/golden/golden_checksum.txt` changes without a valid trigger, CI fails;
- if governance records are missing, CI fails;
- no silent golden drift is allowed.

## 3) How to intentionally update web golden

Use this only when model evolution is intentional.

1. Update model/schema and increment versions.
2. Regenerate golden:

```bash
npm run golden:update --prefix web
```

3. Re-run enforcement:

```bash
npm run golden:integrity --prefix web -- --base <BASE_SHA> --head <HEAD_SHA>
npm run golden:check --prefix web
npm run golden:negative-proof --prefix web
npm run test --prefix web
npm run build --prefix web
```

4. Update baseline and governance docs:
- `benchmarks/baseline_registry.json`
- `engineering/CHANGELOG.md`
- `engineering/DECISIONS.md`

## 4) Mission baseline reproducibility (Formal Mission Definition v1)

Mission-definition v1 is a deterministic contract located under `mission/`.
The CLI wrapper delegates to the public `mission/baseline/*` library layer.

Validate schema + baseline scenario:

```bash
python3 scripts/mission_baseline_check.py --validate-only
```

Run deterministic mission baseline output check:

```bash
python3 scripts/mission_baseline_check.py --verify-deterministic
```

Optionally persist deterministic output structure:

```bash
python3 scripts/mission_baseline_check.py --verify-deterministic --output /tmp/mission_baseline_output.json
```

## 5) Evidence layer reproducibility

Validate the evidence contract in strict mode:

```bash
python3 scripts/ci/evidence_validate.py --strict --base <BASE_SHA> --head <HEAD_SHA>
```

Run evidence validator coverage gate:

```bash
python3 scripts/ci/evidence_coverage.py --min 95
```

Build evidence status artifact:

```bash
python3 scripts/build_evidence_status.py
```

Expected output file:
- `artifacts/evidence_status_v1.json`

Interpretation:
- `missing_evidence_count` must be `0`.
- `realistic_D_violations` must be `0`.
- `evidence_completeness_ratio` should remain `1.0` for a complete registry.

## 6) Parameter & evidence audit reproducibility

Run the full parameter audit locally:

```bash
make param-audit
```

Equivalent explicit commands:

```bash
python3 scripts/ci/parameter_literal_scan.py --strict
python3 scripts/ci/parameter_registry_validate.py --strict
python3 scripts/ci/parameter_evidence_validate.py --strict
python3 scripts/ci/parameter_sensitivity_report.py --baseline mission/BASELINE_SCENARIO_v1.json
```

Expected outcomes:
- scanner report: `unmatched_count = 0`
- scanner scope contract: no undeclared files under watched DAG/optimization roots
- registry validation: `PASS`
- registry visibility validation: public browser/optimization surfaces are explicit and internal code literals remain audit-only
- no legacy line-based `code_literal` parameter ids remain
- evidence completeness: `1.0`
- realistic `D` violations: `0`
- tracked drilldown sensitivity source in `artifacts/parameter_sensitivity_summary.json`
- optional full sensitivity output files in `ops/reports/parameter-audit-latest/`

## 7) Realistic vs speculative mode reproducibility

Run dual-mode mission baseline with deterministic replay:

```bash
python3 scripts/mission_baseline_check.py --mode dual --verify-deterministic
```

Run strict cross-domain leakage guard:

```bash
python3 scripts/ci/parameter_domain_guard.py --strict --format json
```

Run optimization domain guard:

```bash
python3 scripts/optimization_guard.py --strict
```

Expected outcomes:
- parameter-domain guard reports `status=PASS`.
- `realistic_mode_verified=true`.
- `speculative_mode_enabled=true`.
- realistic output remains invariant under speculative-parameter perturbation.
- optimization guard reports only realistic-domain tuned parameters.

## 8) Optimization Engine v1 reproducibility

Run optimization (realistic-only):

```bash
python3 scripts/run_optimization.py --mode realistic --samples 96 --seed 42
```

Run deterministic verification:

```bash
python3 scripts/run_optimization.py --mode realistic --samples 96 --seed 42 --verify-deterministic
```

Expected outputs under `ops/reports/optimization-v1/<run_id>/`:
- `OPTIMIZATION_CONFIG.json`
- `SEARCH_SPACE_RESOLVED.json`
- `SAMPLE_RESULTS.json`
- `PARETO_FRONTIER.json`
- `TOP_K_SOLUTIONS.json`
- `CONSTRAINT_VIOLATIONS.json`
- `DETERMINISM_CHECK.json`
- `meta.json`
- `FINAL_REPORT.md`

Determinism contract:
- same seed/config => identical pack hash.
- changed seed => different pack hash.

## 8.1) Optimization Lab v1 frontier reproducibility

Build tracked realistic frontier artifacts (contract-bound, no `ops/**` reads):

```bash
python3 scripts/build_optimization_frontier.py
python3 scripts/ci/optimization_frontier_validate.py --strict
python3 scripts/ci/risk_envelope_validate.py --strict
```

Drift guard for committed artifacts:

```bash
git diff --exit-code artifacts/optimization_search_space.v1.json artifacts/optimization_frontier_realistic.v1.json
```

Expected tracked outputs:
- `artifacts/optimization_search_space.v1.json`
- `artifacts/optimization_frontier_realistic.v1.json`

Contract highlights:
- realistic mode only
- trust filter `A|B|C`
- bounds enforced from parameter registry
- 2D objective vector derived from `mission/objectives/objective_contract.v1.json`
- risk envelope method from `mission/objectives/risk_envelope.v1.json`
- deterministic regeneration must be byte-identical

## 9) Mission DAG reproducibility

Validate DAG contracts:

```bash
python3 scripts/ci/mission_dag_validate.py --strict
```

Run deterministic dual-mode DAG:

```bash
python3 scripts/run_mission_dag.py --scenario mission/dag/scenarios/mission_dag_baseline.v1.json --mode dual --seed 1 --verify-deterministic
```

Validate generated DAG artifacts:

```bash
python3 scripts/ci/mission_dag_validate.py --strict --artifacts-dir ops/reports/mission-dag-v1/<run_id>
```

Coverage gate:

```bash
python3 scripts/ci/mission_dag_coverage.py --min 90
```

Expected run outputs in `ops/reports/mission-dag-v1/<run_id>/`:
- `DAG_RUN_SUMMARY.json`
- `MODULE_ARTIFACT_MANIFEST.json`
- `HASHCHAIN_PROOF.json`
- `FAILURE_TAXONOMY_COVERAGE.json`
- `DETERMINISM_PROOF.md`
- `MISSION_DAG_NOTES.md`
- `meta.json`

## Model Evolution Protocol

1. Define scope: schema-only, engine-only, or both.
2. Bump versions before golden regeneration.
3. Regenerate golden and baseline in the same change set.
4. Record rationale in engineering logs.
5. Verify negative proof and drift guard pass before merge.

## Troubleshooting

### `golden checksum mismatch`
- Cause: model/schema/scenario drift without approved versioned update.
- Fix: revert unintended change or run full versioned update protocol.

### `golden integrity contract violated`
- Cause: changed golden without version bump or missing governance updates.
- Fix: update schema/engine versions and append changelog + decision entries.

### `schema/scenario validation failed`
- Cause: out-of-range value, unknown field, or schema mismatch.
- Fix: correct scenario fields to match `sim/schema/sim_schema.v1.json`.

### `mission definition validation failed`
- Cause: mission schema contract mismatch, mode violation (`realistic` with speculative overrides), or invalid uncertainty distribution payload.
- Fix: update `mission/MISSION_SCHEMA_v1.json` and `mission/BASELINE_SCENARIO_v1.json` consistently, then rerun `scripts/mission_baseline_check.py --validate-only`.

### `evidence contract validation failed`
- Cause: missing parameter claim, dangling source reference, realistic parameter with trust `D`, or distribution claim without valid uncertainty bounds.
- Fix: update `mission/EVIDENCE_REGISTRY_v1.json` (and `mission/UNCERTAINTY_MODEL_v1.json` when needed), then rerun `python3 scripts/ci/evidence_validate.py --strict`.

### `required paths validation failed`
- Cause: a repository contract file declared in `docs/required_paths.v1.json` is missing, empty, or malformed.
- Fix: restore the file, regenerate it if it is a tracked generated baseline, or intentionally update the manifest in the same change set.
