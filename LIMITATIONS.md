# Limitations

## 1. Known limitations

1. The model is deterministic and reduced-order; it is not a flight dynamics or mission certification engine.
2. Dust/tail, thermal, and uncertainty environments are simplified to bounded surrogate terms.
3. Cost anchors are order-of-magnitude placeholders, not procurement-grade estimates.
4. Artifact and checksum validation prove internal consistency, not physical truth.
5. The browser demo is designed for transparent sensitivity exploration, not predictive mission design.

## 2. Non-goals

1. This project does not produce operational spacecraft software.
2. This project does not resolve the black-hole information paradox.
3. This project does not provide legal, regulatory, or launch authorization outcomes.

## 3. Failure modes

1. Assumption drift: constants/assumptions change without synchronized claim updates.
2. Artifact drift: manual edits to generated outputs break checksum and audit lineage.
3. Baseline misuse: stale baselines can hide regressions.
4. Schema misuse: adding scenario fields not defined in schema invalidates deterministic contract.

## 4. What this project does NOT guarantee

1. It does not guarantee physical feasibility of a complete mission architecture.
2. It does not guarantee survivability in all unmodeled edge environments.
3. It does not guarantee realism when non-physical knobs are changed from defaults.
4. It does not guarantee invariance under arbitrary toolchain/runtime changes outside documented versions.

## 5. Web simulation-specific simplifications

1. Equations are intentionally compact and pedagogical; they are not high-fidelity multiphysics equations.
2. Non-physical knobs (`narrative_leverage_multiplier`, `irreversibility_override`) are explicitly for sensitivity exploration.
3. Time integration is fixed-step and deterministic, optimized for reproducibility over physical completeness.

## 6. Open risks

1. CI environment drift can change behavior if dependency versions are not maintained.
2. Future schema growth can increase complexity and validation burden.
3. Public readers can over-interpret bounded outputs as mission-ready predictions.

## 7. Model Evolution Protocol (limitations-aware)

1. Any intentional golden change requires explicit schema/engine version bumps and governance rationale.
2. Cross-platform checksum parity is tested in CI (Node 18/20 on Linux/macOS), but future runtime/compiler changes can still introduce edge cases and require new baselines.
3. A version bump does not imply physical realism improvement; it only marks a deterministic contract change.

## 8. Mission-definition v1 proxy caveats

1. The black-hole environment acceptance rule is a threshold proxy (`radiative flux`, `plasma density proxy`, `dust scale`) and not a full relativistic plasma model.
2. `P_survive` and `P_data_intact` are reduced-order surrogate probabilities; they are intended for comparative sensitivity, not certification-grade survivability prediction.
3. Realistic/speculative separation is schema-enforced, but speculative mode can still produce numerically plausible outputs that should not be interpreted as physically validated outcomes.

## 9. Evidence-layer limitations

1. Trust grades (`A/B/C/D`) are governance annotations and do not prove external scientific consensus by themselves.
2. Several realistic parameters remain assumption-backed (`type=assumption`) with grade `C`; this is explicit but still a limitation.
3. Speculative parameters are intentionally present for sensitivity experiments:
   - `trajectory_model.non_physical_capture_bias`
   - `environment_model.non_physical_safety_multiplier`
4. Evidence registry validates linkage and consistency, but cannot detect citation quality drift without periodic human review.

## 10. Parameter-audit limitations

1. The parameter scanner enforces declared mission/benchmark scope plus the watched DAG/optimization manifest, not all numeric values in narrative markdown documents.
2. Many parameters are currently trust-grade `C`; this is explicit, but it means model confidence is dominated by bounded assumptions rather than high-trust measurements.
3. Sensitivity ranking is deterministic one-at-a-time (OAT) in v1; it does not capture higher-order interaction effects between parameters.
4. Code-literal inventory includes implementation constants for drift control, but these do not imply independent physical significance; registry visibility metadata keeps them out of public browser and optimization surfaces.

## 11. Dual-mode trust limitations

1. `trust_weighted_score` is a governance-weighted heuristic, not a Bayesian posterior probability.
2. Cross-domain divergence threshold is an operational guardrail (`parameter_domain_guard`), not a physical law.
3. Speculative mode remains useful for exploration, but its outputs are explicitly non-policy and non-certification evidence.

## 12. Optimization v1 limitations

1. Search strategy is deterministic coarse scan + local refinement; it is not guaranteed global optimum.
2. Pareto frontier is computed on three reduced objectives (`core_probability`, `trust_weighted_score`, `risk_metric`) and may omit other mission tradeoffs.
3. Soft-constraint penalties are proxy formulations and should be interpreted as ranking aids, not hard physical feasibility proofs.
4. Optimization is intentionally restricted to realistic-domain parameters; speculative exploration remains out of scope for policy-facing results.

## 13. Mission DAG v1 limitations

1. DAG modules are contract wrappers over existing deterministic mission baseline logic; they are not independent physics solvers in v1.
2. Module failure taxonomy is explicit and machine-enforced, but it is not a complete root-cause ontology for all astrophysical or materials failure mechanisms.
3. Hashchain integrity proves artifact tamper evidence, not physical correctness of module outputs.
4. Per-module payloads are compact proxy summaries; deeper state traces are deferred to future physics model versions.
5. The DAG v2 boundary artifact proves that module-boundary requirements are explicit and hashable; it does not prove independent physics backends, high-fidelity state traces, external reproduction, or flight-ready module approval.

## 14. Optimization Lab v2 limitations

1. The v2 artifact adds four Pareto axes (`p_success`, `risk_envelope`, `qualification_gap`, `cost_proxy`), but it is still a reduced-order decision surface, not full mission utility.
2. `risk_envelope` uses a lower-quantile Monte Carlo proxy (`1 - Q0.05`) from the current uncertainty model; it is not a high-fidelity probabilistic risk assessment.
3. `qualification_gap` is a trust/evidence screen, not a stack-level qualification result.
4. `cost_proxy` is an engineering-resource pressure screen, not launch, manufacturing, operations, or procurement pricing.
5. Deterministic latin-hypercube-style sampling is coverage-oriented, not a guarantee of global optimum.

## 15. Capsule Survivability Lab v1 limitations

1. Capsule Lab is a deterministic reduced-order scenario artifact, not a materials qualification, ballistic-limit test, or mission certification system.
2. Source-backed environment anchors such as local interstellar hydrogen, Voyager plasma density, Ulysses dust density, and NASA HVIT test ranges do not by themselves validate a 10 Myr capsule.
3. Deep-time material hazard, archive-media persistence, shield effectiveness, and hazard coefficients remain explicit grade-C assumptions until upgraded by stack-level tests or stronger public evidence.
4. Time of flight is a scenario variable derived from target distance and selected cruise velocity for the `ballistic-arrival` horizon; it does not prove navigation authority, launch feasibility, or target reachability.
5. Browser controls select committed artifact rows. The UI does not compute new capsule probabilities at runtime.

## 16. Capsule Risk Budget v2 limitations

1. Risk Budget v2 is a Monte Carlo review artifact over the capsule survivability layer; it is not an empirical reliability study or high-fidelity probabilistic risk assessment.
2. Attack-mode contributions are reduced-order accounting outputs. They help reviewers locate dominant assumptions, but they do not prove physical root cause or qualification closure.
3. p05/p50/p95 bands reflect the encoded uncertainty dimensions and priors. They do not include every unknown unknown, omitted correlation, or model-form error.
4. Source-backed anchors, heritage proxies, and assumption-bound priors must remain visibly separate. A source-backed local environment value does not certify a deep-time target-region mission row.
5. Capsule risk-budget survival numbers do not replace `P_hit`, target reachability, launch feasibility, archive recovery, regulatory review, or operational certification.

## 17. Full V2 Roadmap Closure limitations

1. `roadmap_closure.v1` closes the 15-item roadmap as repository-native contracts, artifacts, validators, and public summaries; it does not close the external physical evidence.
2. `repo_native_closure_implemented_external_evidence_open` means the review surface exists and is validated, not that hardware qualification, launch approval, procurement validation, or third-party physics benchmarking is complete.
3. The closure artifact deliberately keeps external evidence gaps visible, so a green validator must not be read as a certified mission design.

## 18. Mission Feasibility Screen v1 limitations

1. `mission_feasibility_screen.v1` is a deterministic review surface, not a trajectory optimizer, launch architecture, procurement quote, or mission-readiness decision.
2. Ballistic time of flight is derived from Capsule Lab target distance and velocity rows; it ignores acceleration phase, navigation authority, active maintenance, and operations.
3. Dust and gas exposure screens use local source-backed anchors plus explicit assumptions; they do not close whole-path ISM variation or target-region environments.
4. Cost fields are kinetic-energy proxies only and must not be read as launch price, procurement feasibility, or project budget.

## 19. User Mission Run Catalog v1 limitations

1. `user_mission_run_catalog.v1` assigns deterministic run ids and source hashes to selected rows; it does not create a persistent production run service.
2. `runtime_scenario_generation.v1` exposes local run recipes and compiled-scenario deltas; it is not a browser-side runner, remote execution service, or persistent reviewed archive.
3. In v1, selected velocity is review metadata tied to feasibility, flight time, and risk rows; the compiled `MISSION_SCHEMA_v1` runtime scenario does not introduce a velocity-specific physics field.
4. `scripts/run_user_mission_scenario.py` writes local review packs under `ops/reports/user-mission-runs/`; those packs are evidence outputs, not tracked repository truth.
5. The compiled mission scenario feeds the existing Mission DAG v1 wrapper modules, not independent high-fidelity physics backends.
6. A passing selected-run pack proves deterministic linkage to the selected assumptions and DAG hashchain, not mission feasibility, flight readiness, procurement readiness, or archive recovery.

## 20. Mission Probability Coupling v1 limitations

1. `mission_probability_coupling.v1` is a factorized review artifact, not a closed full-mission reliability model.
2. Target delivery, whole-path environment probability, and recovery/readout probability remain open external factors with null full-mission p05/p50/p95 values.
3. The closed capsule/data probability is a review proxy derived from Capsule Risk Budget rows, not `P_archive_recoverable`.
4. Compact DAG snapshots prove deterministic linkage and hashchain status for selected assumptions; they do not turn DAG wrapper outputs into independent physics validation.

## 21. Uncertainty Interactions v1 limitations

1. `uncertainty_interactions.v1` is a pairwise endpoint residual screen, not a calibrated covariance model, Sobol decomposition, or certified probability interval.
2. Correlation coefficients remain `null` until external covariance evidence exists.
3. The screen ranks current baseline interaction risk; it does not update full mission probability or close external target, path, or recovery factors.
4. Higher-order interactions, path-conditioned distributions, and model-form validation remain explicit external evidence gaps.

## 22. Evidence Upgrade Campaign v1 limitations

1. `evidence_upgrade_campaign.v1` ranks source-review work; it does not promote any trust grade by itself.
2. Public route rows are limited to browser-safe parameter claims; internal audit claims are summarized as counts and stay out of detail views.
3. Priority scores are repository triage aids based on current trust, source type, visibility, and sensitivity metadata, not scientific truth scores.
4. Source correctness, external validation, and hardware or mission qualification remain open until independent evidence replaces the current gaps.
