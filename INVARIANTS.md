# Invariants

## Safety Invariants

### Invariant ID
`S-001`

### Description
All registered numeric checks must remain inside declared min/max bounds.

### Formal statement
For every claim `c` and every check `k` in `c.checks`, `min_k <= value(c, k.path) <= max_k`.

### Why it matters
Prevents silent publication of out-of-envelope numeric claims.

### How it is enforced
`models/claim_calculations.py` computes deterministic values and `tests/test_claim_calculations.py` verifies range constraints.

### How it is tested
`tests/test_claim_calculations.py::ClaimCalculationTests.test_registry_ranges_match_calculated_values`

### What would break it
Changing a model equation or constant without updating claim bounds.

### Negative example
If `delta_v_1000_au_min_m_s` is recalculated below its configured minimum, test fails and CI blocks.

---

### Invariant ID
`S-002`

### Description
Physics primitives must reject invalid domains.

### Formal statement
For domain-restricted functions `f`, invalid inputs trigger `ValueError` and do not produce numeric outputs.

### Why it matters
Prevents invalid states from contaminating downstream metrics.

### How it is enforced
Input validation guards in `models/core_physics.py`.

### How it is tested
`tests/test_core_physics.py::CorePhysicsTests.test_invalid_inputs_raise`

### What would break it
Removing input guards or broad exception swallowing.

### Negative example
Calling `solar_flux_w_m2(0.0)` must raise; if not, safety invariant is violated.

---

### Invariant ID
`S-003`

### Description
Realistic mission mode must not include speculative parameter overrides.

### Formal statement
If `mission_mode = realistic`, then `len(speculative_overrides) = 0`.

### Why it matters
Prevents mixing non-physical assumptions into realistic reporting.

### How it is enforced
`scripts/mission_baseline_check.py` validates mission-mode rules against `mission/MISSION_SCHEMA_v1.json`.

### How it is tested
`tests/test_mission_definition_layer.py::MissionDefinitionLayerTests.test_realistic_mode_rejects_speculative_override`

### What would break it
Allowing speculative overrides in realistic mode would collapse mode separation guarantees.

### Negative example
Setting `mission_mode=realistic` and overriding `trajectory_model.non_physical_capture_bias` must fail validation.

## Liveness Invariants

### Invariant ID
`L-001`

### Description
Golden run must terminate and produce a complete evidence pack.

### Formal statement
`scripts/run_golden.py` exits `0` and required files exist:
- `metadata.json`
- `input_parameters.json`
- `output_metrics.json`
- `checksums.sha256`

### Why it matters
Without termination and full outputs, no reproducible baseline exists.

### How it is enforced
Golden run performs build then hard validation over required files.

### How it is tested
`tests/test_public_foundation_layer.py::PublicFoundationLayerTests.test_run_golden_emits_required_artifact_files`

### What would break it
Builder failure, missing JSON generation, or malformed artifact pack.

### Negative example
Deleting `output_metrics.json` after build causes golden run validation to fail.

---

### Invariant ID
`L-002`

### Description
Benchmark compare must always return a deterministic PASS/REGRESSION decision for defined metrics.

### Formal statement
For every metric definition `m`, compare emits exactly one status in `{PASS, REGRESSION}`.

### Why it matters
Prevents ambiguous baseline interpretation.

### How it is enforced
`scripts/benchmark_compare.py` enforces required definition fields and explicit threshold logic.

### How it is tested
`tests/test_public_foundation_layer.py::PublicFoundationLayerTests.test_benchmark_compare_passes_on_current_baseline`

### What would break it
Missing baseline entries or unsupported threshold schema.

### Negative example
Removing baseline entry for `checks_pass_rate` triggers compare failure.

---

### Invariant ID
`L-003`

### Description
Mission baseline checker must deterministically produce the same output structure for identical input files.

### Formal statement
For fixed `MISSION_SCHEMA_v1.json` and `BASELINE_SCENARIO_v1.json`:
`run_1 == run_2` under canonical serialization.

### Why it matters
Mission-level claims must be reproducible and diffable across CI runs.

### How it is enforced
`scripts/mission_baseline_check.py --verify-deterministic` computes output twice and hard-fails on mismatch.

### How it is tested
`tests/test_mission_definition_layer.py::MissionDefinitionLayerTests.test_baseline_check_is_deterministic`

### What would break it
Non-deterministic time/random dependencies in mission-check computation.

### Negative example
Injecting wall-clock timestamps into mission output would make deterministic check fail.

## Data Integrity Invariants

### Invariant ID
`D-001`

### Description
Claim traceability links must resolve to existing assumptions and sources.

### Formal statement
For every claim `c`, `c.assumption_ids ⊆ assumptions.keys` and `c.source_ids ⊆ sources.keys`.

### Why it matters
Ensures every published claim is auditable to concrete assumptions and sources.

### How it is enforced
Registry loading and link validation in traceability tests.

### How it is tested
`tests/test_traceability_chain.py::TraceabilityChainTests.test_all_links_resolve_in_registry`

### What would break it
Deleting registry entries referenced by claims.

### Negative example
Removing one source entry while claims still reference it must fail tests.

---

### Invariant ID
`D-002`

### Description
Checksummed artifact outputs must match their declared digests.

### Formal statement
For each line `(digest, path)` in `checksums.sha256`, `sha256(path) == digest`.

### Why it matters
Guarantees tamper-evident artifact reproducibility.

### How it is enforced
Checksum verification inside golden run and traceability tests.

### How it is tested
`tests/test_traceability_chain.py::TraceabilityChainTests.test_artifact_pack_checksums_match`

### What would break it
Manual edits to outputs without regenerating checksum manifest.

### Negative example
Editing `artifacts/claim_values.json` directly causes checksum mismatch and hard failure.

---

### Invariant ID
`D-003`

### Description
Web simulation golden output must be version-coupled to schema and engine version.

### Formal statement
If `sim/golden/golden_checksum.txt` changes, at least one trigger must hold: schema version bump OR engine version bump OR `breaking_change_flag=true`; governance logs must also be updated.

### Why it matters
Prevents silent model drift and preserves auditability of public deterministic claims.

### How it is enforced
`web/scripts/golden_integrity_enforce.ts` checks diff range, version bumps, and governance file updates.

### How it is tested
`npm run golden:integrity --prefix web -- --base <BASE_SHA> --head <HEAD_SHA>`

### What would break it
Updating golden checksum directly without updating schema/engine versions and decision/changelog rationale.

### Negative example
Editing `sim/golden/golden_checksum.txt` alone causes CI hard fail with `golden_requires_version_or_breaking_flag`.

---

### Invariant ID
`D-004`

### Description
Mission baseline scenario must provide explicit uncertainty distributions with numeric parameters.

### Formal statement
For every `u` in `uncertainty_model`, `u.distribution` is in `{normal, lognormal, uniform, triangular}` and `u.parameters` is a non-empty numeric map.

### Why it matters
Prevents undefined uncertainty placeholders in mission-level outputs.

### How it is enforced
`scripts/mission_baseline_check.py` validates all uncertainty entries before any mission output is produced.

### How it is tested
`tests/test_mission_definition_layer.py::MissionDefinitionLayerTests.test_schema_and_baseline_validate`

### What would break it
Leaving uncertainty entries empty or replacing distributions with free-text placeholders.

### Negative example
Setting `uncertainty_model[0].parameters = {}` must fail validation.

---

### Invariant ID
`D-006`

### Description
All scoped numeric literals must be registered in the parameter registry.

### Formal statement
For scanner scope `S`, `unmatched_literals(S, parameter_registry) = 0` and `stale_registry_refs = 0`.

### Why it matters
Prevents silent drift from undocumented numeric constants in mission/benchmark computation paths.

### How it is enforced
`scripts/ci/parameter_literal_scan.py --strict` is executed in CI and local evidence checks.

### How it is tested
`tests/test_parameter_literal_scan.py::ParameterLiteralScanTests.test_missing_registry_ref_fails`

### What would break it
Adding a new numeric literal in scoped files without updating `parameters/registry/parameter_registry.v1.json`.

### Negative example
A new constant in `scripts/mission_baseline_check.py` without a matching `code_ref` causes strict scan failure.

---

### Invariant ID
`D-007`

### Description
Parameter evidence binding must remain complete and trust-policy compliant.

### Formal statement
1. Every `parameter_id` in `parameter_registry.v1.json` has exactly one claim.
2. `evidence_completeness_ratio = 1.0`.
3. `realistic_D_violations = 0`.

### Why it matters
Public numeric claims require explicit provenance and mode-aware trust constraints.

### How it is enforced
`scripts/ci/parameter_evidence_validate.py --strict` validates claim coverage, source resolution, and trust rules.

### How it is tested
`tests/test_parameter_evidence_contract.py::ParameterEvidenceContractTests.test_realistic_d_violation_fails`

### What would break it
Removing claims, dangling source IDs, or assigning trust `D` to realistic parameters.

### Negative example
Setting `trust_grade=D` for realistic `bh_parameters.mass_kg` must fail.

---

### Invariant ID
`D-008`

### Description
Realistic-mode mission outputs must be invariant to speculative-parameter perturbations.

### Formal statement
For baseline scenario `s` and speculative perturbation operator `P_spec`,
`run(realistic, s).p_success = run(realistic, P_spec(s)).p_success` and same for `p_hit`, `p_survive`, `p_data_intact`, `core_probability`.

### Why it matters
Guarantees policy-facing results are not contaminated by non-physical controls.

### How it is enforced
`scripts/ci/parameter_domain_guard.py --strict` mutates speculative parameters to high values and checks realistic output equality.

### How it is tested
`tests/test_parameter_domain_guard.py::ParameterDomainGuardTests.test_current_domain_guard_passes`

### What would break it
Using speculative paths directly inside realistic computation path or implicit fallback logic.

### Negative example
If `trajectory_model.non_physical_capture_bias` changes `p_success` in realistic mode, domain guard must fail.

---

### Invariant ID
`D-009`

### Description
Optimization plans may tune only realistic-domain, non-`D`, core-probability parameters.

### Formal statement
For each `parameter_id` in `optimization_plan.tuned_parameters`:
`domain=realistic ∧ trust_grade∈{A,B,C} ∧ affects_core_probability=true`.

### Why it matters
Prevents producing attractive but non-credible optimized solutions by tuning speculative levers.

### How it is enforced
`scripts/optimization_guard.py --strict` validates optimization plan against registry and claims.

### How it is tested
`tests/test_optimization_guard.py::OptimizationGuardTests.test_speculative_parameter_in_plan_fails`

### What would break it
Allowing speculative or trust-`D` parameters into optimization search space.

### Negative example
Including `trajectory_model.non_physical_capture_bias` in `tuned_parameters` must fail.

---

### Invariant ID
`D-010`

### Description
Realistic optimization search space must contain no speculative or trust-`D` parameters.

### Formal statement
For every `p` in resolved search space:
`domain(p)=realistic ∧ trust(p)∈{A,B,C} ∧ affects_core_probability(p)=true`.

### Why it matters
Prevents optimization from producing policy-facing results through speculative controls.

### How it is enforced
`mission/optimization/search_space.py` and `scripts/optimization_guard.py --strict`.

### How it is tested
`tests/test_optimization_engine_v1.py::OptimizationEngineV1Tests.test_speculative_parameter_in_plan_is_rejected`
and
`tests/test_optimization_engine_v1.py::OptimizationEngineV1Tests.test_d_grade_parameter_is_rejected`

### What would break it
Allowing non-physical or trust-`D` entries into `tuned_parameters` without rejection.

### Negative example
Adding `trajectory_model.non_physical_capture_bias` to optimization plan must fail.

---

### Invariant ID
`D-011`

### Description
Optimization artifacts must be deterministic for identical seed/config and diverge for changed seed.

### Formal statement
If `(scenario, search_space, constraints, seed)` are equal, then `hash(pack_a)=hash(pack_b)`.
If only seed changes, then `hash(pack_a) != hash(pack_c)`.

### Why it matters
Deterministic optimization is required for reproducibility and regression auditing.

### How it is enforced
`scripts/run_optimization.py --verify-deterministic` writes `DETERMINISM_CHECK.json` and fails on mismatch.

### How it is tested
`tests/test_optimization_engine_v1.py::OptimizationEngineV1Tests.test_same_seed_produces_identical_hash`
and
`tests/test_optimization_engine_v1.py::OptimizationEngineV1Tests.test_different_seed_changes_hash`

### What would break it
Non-deterministic sampling/order or time-dependent serialization in artifact generation.

### Negative example
Using unordered iteration over candidate params would create non-reproducible hashes.

---

### Invariant ID
`D-005`

### Description
Evidence registry must fully cover mission parameter IDs and enforce trust-mode constraints.

### Formal statement
1. For every mission parameter ID `p` declared in `MISSION_SCHEMA_v1.json`, there exists exactly one `ParameterClaim(p)` in `EVIDENCE_REGISTRY_v1.json`.
2. If `ParameterClaim.mode = realistic`, then `trust_grade != D`.
3. If `ParameterClaim.value_mode = distribution`, corresponding uncertainty bounds satisfy `min < max`.

### Why it matters
Prevents hidden assumptions and preserves auditability of realistic versus speculative claims.

### How it is enforced
`scripts/ci/evidence_validate.py --strict` validates schema coverage, source linkage, trust constraints, and bounds; drift guard requires changelog updates on claim/trust/source edits.

### How it is tested
`tests/test_evidence_contract.py::EvidenceContractTests.test_current_repo_contract_passes`  
`tests/test_evidence_negative_cases.py::EvidenceNegativeCasesTests.test_realistic_parameter_with_trust_d_fails`  
`tests/test_evidence_negative_cases.py::EvidenceNegativeCasesTests.test_dangling_evidence_source_id_fails`

### What would break it
Adding a new mission parameter without a claim binding, downgrading a realistic claim to trust `D`, or removing source references.

### Negative example
Setting `trust_grade=D` for a realistic claim must fail strict validation.

---

### Invariant ID
`D-012`

### Description
Mission DAG scenario must remain acyclic and fully resolvable.

### Formal statement
For DAG `G=(V,E)` loaded from `mission_dag_baseline.v1.json`: every dependency endpoint is in `V` and `G` has no directed cycle.

### Why it matters
Cycle-free dependency graphs are required for deterministic topological execution and reproducible per-module artifact order.

### How it is enforced
`mission/dag/contracts.py` validates dependency existence and performs cycle detection.

### How it is tested
`tests/test_mission_dag_schema.py::MissionDagSchemaTests.test_cycle_is_rejected`

### What would break it
Any scenario edit introducing a back-edge or missing dependency reference.

### Negative example
Setting `traj.depends_on=[\"data\"]` in the baseline graph must fail validation.

---

### Invariant ID
`D-013`

### Description
Every non-PASS module output must reference a known taxonomy ID with matching stage.

### Formal statement
If `module.failure.status != PASS`, then:
1. `module.failure.failure_mode ∈ failure_taxonomy.ids`
2. `module.failure.failure_stage = failure_taxonomy[failure_mode].stage`

### Why it matters
Prevents ad-hoc failure labels and keeps module-level risk reporting machine-checkable.

### How it is enforced
`mission/dag/contracts.py::validate_module_output` and `scripts/ci/mission_dag_validate.py --strict`.

### How it is tested
`tests/test_module_failure_taxonomy.py::ModuleFailureTaxonomyTests.test_forced_failure_uses_known_taxonomy_id`

### What would break it
Unknown taxonomy IDs, stage mismatch, or missing failure metadata.

### Negative example
Using `failure_mode=\"CUSTOM_FAIL\"` outside taxonomy must fail.

---

### Invariant ID
`D-014`

### Description
Mission DAG hashchain must detect post-run tampering.

### Formal statement
For each hashchain entry `h_i`: `h_i.prev_hash = h_{i-1}.chain_hash` and `h_i.chain_hash = sha256(canonical(h_i \\ chain_hash))`; additionally `sha256(artifact_path) = h_i.artifact_hash`.

### Why it matters
Guarantees artifact integrity and audit traceability across module outputs.

### How it is enforced
`mission/dag/hashchain.py` during run and `scripts/ci/mission_dag_validate.py --strict --artifacts-dir ...` during verification.

### How it is tested
`tests/test_mission_dag_determinism.py::MissionDagDeterminismTests.test_hashchain_tamper_is_detected`

### What would break it
Manual edits to module artifacts or hashchain entries after generation.

### Negative example
Mutating one module output JSON after run must cause validation FAIL.

---

### Invariant ID
`D-015`

### Description
Dual-mode DAG execution must preserve realistic/speculative isolation.

### Formal statement
Under speculative knob perturbation: realistic-mode `p_success` remains invariant; speculative-mode `p_success` may vary.

### Why it matters
Ensures policy-facing realistic outputs are not contaminated by speculative controls in moduleized execution.

### How it is enforced
`mission/dag/runner_v1.py` executes dual mode with isolated mission baseline calls and reuses `parameter_domain_guard`.

### How it is tested
`tests/test_mission_dag_realistic_speculative_isolation.py::MissionDagModeIsolationTests.test_realistic_result_is_isolated_from_speculative_knobs`

### What would break it
Any module path reading speculative controls while running realistic mode.

### Negative example
If realistic `p_success` changes when `non_physical_*` values change, this invariant is violated.

---

### Invariant ID
`D-016`

### Description
Tracked Optimization Lab frontier artifacts must be realistic-only, bounded, and deterministic.

### Formal statement
For each point `x` in `artifacts/optimization_frontier_realistic.v1.json`:
1. `mode=realistic`
2. `∀p∈x.parameters: p∈optimization_search_space.parameters_considered`
3. `bounds_min(p) <= value(p) <= bounds_max(p)`
4. `objective_vector=[p_success, risk_envelope]` in v1.1 objective contract
5. `risk_envelope = 1 - Q_0.05(p_success_distribution)` and `0 <= risk_envelope <= 1`
6. Rebuild with same seed/config yields byte-identical frontier JSON.

### Why it matters
Prevents hidden optimizer drift and keeps public frontier comparisons reproducible and audit-safe.

### How it is enforced
`scripts/build_optimization_frontier.py` + `scripts/ci/optimization_frontier_validate.py --strict` + `scripts/ci/risk_envelope_validate.py --strict` and CI drift guard on committed optimization artifacts.

### How it is tested
`tests/test_optimization_frontier_validate.py::OptimizationFrontierValidateTests.test_valid_frontier_passes`  
`tests/test_optimization_frontier_validate.py::OptimizationFrontierValidateTests.test_d_grade_parameter_in_realistic_search_space_fails`  
`tests/test_optimization_frontier_validate.py::OptimizationFrontierValidateTests.test_parameter_outside_bounds_fails`  
`tests/test_optimization_frontier_validate.py::OptimizationFrontierValidateTests.test_frontier_order_tamper_fails_determinism_check`  
`tests/test_risk_envelope_validate.py::RiskEnvelopeValidateTests.test_missing_risk_envelope_fails`

### What would break it
Including trust-`D` parameters, violating bounds, or committing a frontier that differs from deterministic regeneration.

### Negative example
Reordering frontier points by hand without rebuilding must fail strict validation.

## Model Evolution Protocol

1. Increment schema and engine version before regenerating golden output.
2. Regenerate `sim/golden/*` and baseline registry atomically.
3. Append rationale entries to `engineering/CHANGELOG.md` and `engineering/DECISIONS.md`.
4. Require passing positive checks and controlled negative proof before merge.
