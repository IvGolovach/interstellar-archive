# Parameter Model

## What counts as a parameter
A parameter record is any tracked numeric value in scope for mission computation or deterministic benchmark governance. The canonical registry intentionally contains two classes of entries:

- public mission/design/environment parameters that belong in browser-facing drilldown and sensitivity outputs
- internal implementation literals and thresholds that stay in canonical audit registries for traceability, but are not part of the public parameter workspace

Current enforced scope:
- `mission/BASELINE_SCENARIO_v1.json`
- `mission/UNCERTAINTY_MODEL_v1.json`
- numeric bound nodes in `mission/MISSION_SCHEMA_v1.json`
- tracked public mission parameters in scenario/schema contracts
- tracked internal literals/constants in `mission/baseline/constants.py`, `mission/baseline/model.py`, `scripts/benchmark_compare.py`, and `scripts/benchmark_drift_guard.py`
- watched-but-not-yet-audited DAG/optimization paths declared in `parameters/registry/parameter_literal_scope.v1.json`

Public scope rule:
- browser-facing drilldown, browser dataset, and optimization artifacts expose only entries with `visibility=public` and the matching `public_surfaces` value
- internal `code_literal.*` entries remain canonical audit records only, with `visibility=internal`, `public_surfaces=[]`, and `audit_scope=code_literal`
- the `code_literal.*` namespace is retained as a safety guard, but the source of truth is registry metadata

## Registry contract
Registry file: `parameters/registry/parameter_registry.v1.json`

Every entry must include:
- `parameter_id`
- `unit`
- `default`
- `bounds`
- `classification`
- `mode`
- `visibility`
- `public_surfaces`
- `audit_scope`
- `code_refs` and/or `json_refs`

Rules:
- `bounds` always required.
- If `type=distribution`, entry must include distribution type/parameters/bounds/evidence source references.
- No parameter may be used without a claim in `parameters/registry/parameter_claims.v1.json`.
- Public entries require `audit_scope=mission_parameter` and at least one declared public surface.
- Internal code-literal entries require `visibility=internal`, no public surfaces, and `audit_scope=code_literal`.
- Python `code_refs` must use stable symbolic refs (`path::scope::literal[index]` or `path::<module>::NAME`), not raw line numbers.
- Code-literal `parameter_id` values must also use stable symbolic naming derived from `code_refs` (for example `code_literal.mission_baseline_model._compute_core_probabilities.literal_3`), not legacy line-based ids.

## How to add a new parameter
1. Add or modify the numeric value in mission code, benchmark code, or JSON.
2. Confirm the file is declared in `parameter_literal_scope.v1.json` as audited or explicitly excluded with rationale.
3. Add corresponding entry in `parameter_registry.v1.json` with exact `code_refs`/`json_refs`.
4. Decide whether the new entry is a public mission/design/environment parameter or an internal audit-only literal and set `visibility`, `public_surfaces`, and `audit_scope`.
5. Add or update claim in `parameter_claims.v1.json` and source in `evidence_sources.v1.json`.
6. If the entry is intended for browser/public drilldown, include `browser` in `public_surfaces`; if it may appear in optimization search-space reporting, include `optimization`.
7. Run:

```bash
python3 scripts/ci/parameter_literal_scan.py --strict
python3 scripts/ci/parameter_registry_validate.py --strict
python3 scripts/ci/parameter_evidence_validate.py --strict
python3 scripts/ci/parameter_sensitivity_report.py --baseline mission/BASELINE_SCENARIO_v1.json
```

## CI enforcement
`evidence.yml` runs strict checks. Any unmatched numeric literal or missing evidence binding is a hard fail.
