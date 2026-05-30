# Deep-Time Archive Feasibility Technical Specification

Version: 0.1 draft
Status: technical work specification
Scope: convert the current publication artifact into a stronger engineering feasibility program for a passive interstellar archive capsule.

## 1. Purpose

This specification defines what must be added, changed, measured, and validated for the repository to support the stronger thesis from `paper/whitepaper.md`:

> A passive physical archive capsule, built from present-day material classes and verified during a finite early control window, may be able to preserve recoverable information over a roughly 10 million year interstellar cruise under explicitly bounded dust, gas, radiation, material-aging, and readability assumptions.

This is not a mission proposal, flight-readiness claim, hardware certification claim, or proof of black-hole targeting. It is a boundary study of deep-time engineering: early control is finite, late control becomes unavailable, and terminal outcomes become statistical outcome classes.

## 2. Reframing Required From The Notes

The repository should move from "mission feasibility model" to "deep-time passive archive boundary study".

Required public frame:

- The first-order object is a passive archive capsule, not the black hole.
- The black hole is an extreme terminal outcome class used to stress-test controllability, not a promised target.
- The central phenomenon is the finite control window: early verification and limited correction are possible; million-year actuation, repair, and telemetry are not assumed.
- The hard proof target is S2 passive survivability and recoverable information, not S3 terminal interaction.
- The repository's deterministic checks prove traceability and drift control, not physical truth.

## 3. Claim Hierarchy

Public claims must be arranged in this order:

| Claim | Meaning | Current status | Required gate |
| --- | --- | --- | --- |
| C0: repository auditability | Inputs, scripts, artifacts, checksums, and validators are reproducible. | Mostly implemented. | `make check` and release artifact remain green. |
| C1: passive archive study | The repo studies whether a passive capsule can preserve recoverable information over Myr horizons. | Partially present in `paper/whitepaper.md`. | README and mission specs adopt this as the primary frame. |
| C2: capsule survivability | S2 is model-based survivability over deep time with p05/p50/p95 and evidence mix. | Reduced-order proxy only. | Shield, material aging, media/readability, and environment packs exist. |
| C3: terminal outcome classes | S3 is probabilistic by `R_int`, split into Case A and Case B. | Conceptual in whitepaper. | Trajectory/control/Oberth artifact quantifies `b_max`, `delta_v_perp`, and uncertainty growth. |
| C4: proof promotion | Stronger public claims require external records and reviewed promotion. | Blocked. | External evidence intake and promotion validators accept records without auto-upgrading claims. |

Blocked public claims until gates close:

- mission feasible
- flight-ready
- certified
- qualified
- third-party validated
- independent reproduction completed
- black-hole capture targetable
- archive recovery guaranteed
- procurement-grade cost estimate
- launch vehicle selected

## 4. Success Metrics

Create a first-class success metric contract instead of treating one `P_success` as the umbrella outcome.

Required levels:

| Level | Definition | Evidence type |
| --- | --- | --- |
| S0 | Survive launch, Jupiter gravity assist, perihelion, SRM/Oberth event if used, and achieve solar escape with capsule intact. | Mission architecture, TPS/SRM qualification, launch/trajectory review. |
| S1 | Verify capsule and archive integrity via telemetry during nominal 10-20 year early phase. | Early operations, OD, telemetry, checkout, archive-integrity report. |
| S2 | Passive survivability over Myr horizons. | Model-based p05/p50/p95 for structure, vault, media, readability, and decoding. |
| S3 | Terminal outcome class defined by `R_int`. | Probabilistic Case A/Case B encounter model; no guarantee. |

Required file work:

- Create `mission/SUCCESS_METRICS_SPEC_v1.md`.
- Update `mission/MISSION_SPEC_v1.md`.
- Update `mission/MISSION_PROBABILITY_COUPLING_SPEC_v1.md` so any full `P_archive_recoverable` remains null until target delivery, whole-path environment, and recovery/readout factors are closed.
- Update public wording rules in `mission/PUBLIC_NARRATIVE_HARDENING_SPEC_v1.md`.

Acceptance criteria:

- `P_success = P_hit * P_survive * P_data_intact` is described as a factorized proxy, not a complete mission-success statement.
- S2 capsule survivability can be discussed without implying S3 targetability.
- S3 Case A cannot be described as operationally controllable.

## 5. Workstream A: Public Frame And Reader Path

### Current Gap

The whitepaper contains the right intellectual frame, but the public entrypoints still over-emphasize repository machinery and mission-feasibility language.

### Apply From Notes

- "Boundary Study, Not a Mission Proposal"
- finite early control window
- passive ballistic drift
- S0-S3 success metrics
- Case A horizon/capture vs Case B astronomical encounter
- black hole as boundary condition, not target promise

### File Targets

- `README.md`
- `docs/README.md`
- `RESEARCH_POSITIONING.md`
- `LIMITATIONS.md`
- `paper/whitepaper.md`
- `mission/PUBLIC_NARRATIVE_HARDENING_SPEC_v1.md`

### Acceptance Criteria

- First README viewport states passive archive, early control window, passive drift, S0-S3, Case A/Case B, and non-certification.
- "Black hole" appears as an extreme outcome class or stress-test, not the primary product identity.
- Public text says green CI proves internal consistency, not capsule survivability.
- Public narrative hardening forbids "mission feasible", "proven feasible", "qualified", "certified", and "flight-ready" before external gates close.

## 6. Workstream B: Capsule Architecture And Shield Stack

### Current Gap

`mission/capsule/capsule_design.v1.json` is a mass allocation and bounded design proxy. It is not yet a physical shield model.

Current v1 stack to preserve as the baseline design:

| Layer | Current allocation |
| --- | ---: |
| C/C-SiC TPS | 46 kg, 24 mm |
| Al-Li bumper | 24 kg, 7 mm |
| stand-off gap | 0.25 m |
| B4C/Ta rear wall | 38 kg, 14 mm |
| Ti vault | 52 kg, 12 mm |
| data media package | 28 kg |
| redundancy margin | 18 kg |

### Data To Find

- Ballistic-limit curves for Whipple and graded shield stacks.
- Projectile radius, mass, density, material, velocity, and angle distributions.
- NASA JSC HVIT direct lab capability limits: https://hvit.jsc.nasa.gov/hypervelocity-testing/
- NASA/ESA hypervelocity impact context: https://www.esa.int/Space_Safety/Space_Debris/Hypervelocity_impacts_and_protecting_spacecraft
- NASA White Sands RHTL facility context: https://www.nasa.gov/centers-and-facilities/white-sands/remote-hypervelocity-test-laboratory/
- Hydrocode or validated BLE references for extrapolating beyond the direct test envelope.

### Calculations To Add

- `P_no_penetration(t) = exp(-integral flux(size, velocity, angle) * area * P_fail(size, velocity, angle, stack) dt)`.
- Impact energy and momentum bins for micron, 100 micron, millimeter, and centimeter particles at 23, 34, 45, and 60 km/s.
- Separate penetration, spall, shock, rear-wall impulse, vault shock, and media transmitted acceleration terms.
- Shield model uncertainty when the requested velocity/mass/angle envelope exceeds direct lab evidence.

### New Artifacts

- `mission/CAPSULE_SHIELD_STACK_SPEC_v1.md`
- `artifacts/capsule_shield_stack_ballistic.v1.json`
- `scripts/build_capsule_shield_stack_ballistic_artifact.py`
- `scripts/ci/capsule_shield_stack_ballistic_validate.py`
- `tests/test_capsule_shield_stack_ballistic.py`

Required artifact fields:

- `stack_layers`
- `projectile_distribution`
- `velocity_bins`
- `angle_bins`
- `ballistic_limit_model`
- `test_records`
- `hydrocode_records`
- `extrapolation_bounds`
- `p_no_penetration_quantiles`
- `blocked_claims`

### Acceptance Criteria

- The artifact exposes p05/p50/p95 for shield penetration and catastrophic damage.
- Direct lab-tested velocity ranges are separate from hydrocode or extrapolated ranges.
- A severe dust-tail case exists and is not hidden behind the nominal row.
- If stack evidence does not cover the claimed velocity/mass/angle envelope, `qualification_status` remains `external_required`.

## 7. Workstream C: Material Aging And Passive Survivability

### Current Gap

`material_degradation_mu_1_per_year` is a single assumption-bound coefficient. It must become a material-specific model.

### Data To Find

For each material:

- C/C-SiC: oxidation, sublimation, radiation damage, thermal cycling, microcracking.
- Al-Li bumper: embrittlement, sputtering, thermal/radiation stability.
- B4C/Ta rear wall: radiation attenuation, swelling, activation, brittleness, interface failure.
- Ti vault: creep, embrittlement, displacement damage, shock survival.
- Fused silica, sapphire, or etched inert media: optical darkening, fracture, radiation-induced absorption, annealing behavior.
- NASA space environmental effects and materials degradation references: https://www.nasa.gov/science-research/for-researchers/a-researchers-guide-to-space-environmental-effects/
- NASA LDEF/MISSE materials exposure context: https://space.jpl.nasa.gov/msl/QuickLooks/ldefQL.html

### Calculations To Add

- `hazard_material(layer, t, dose, temperature, impacts)` per layer.
- Layer-specific degradation laws with source ids and validity bounds.
- GCR and particle dose hooks using named radiation transport references, not `radiative_flux_w_m2`.
- Sensitivity table for the degradation rate required to preserve p05/p50/p95 over 10 Myr.

### New Artifacts

- `mission/CAPSULE_MATERIAL_AGING_SPEC_v1.md`
- `artifacts/capsule_material_aging.v1.json`
- `scripts/build_capsule_material_aging_artifact.py`
- `scripts/ci/capsule_material_aging_validate.py`
- `tests/test_capsule_material_aging.py`

Required artifact fields:

- `material_id`
- `failure_modes`
- `dose_model`
- `thermal_model`
- `aging_law`
- `source_ids`
- `validity_bounds`
- `hazard_quantiles_10myr`
- `evidence_grade`

### Acceptance Criteria

- Material degradation is no longer represented only by one global scalar.
- Each material has failure modes and evidence status.
- If material-specific evidence is missing, the public claim remains "bounded assumption", not "validated".

## 8. Workstream D: Archive Media And Readability

### Current Gap

The current repository models data-media survival margin but does not prove that information remains recoverable after damage and deep-time exposure.

### Data To Find

- Candidate medium: fused silica 5D laser-written, sapphire etched analog/digital, ceramic, or metal engraving.
- Nature Project Silica glass-storage paper: https://www.nature.com/articles/s41586-025-10042-w
- Southampton 5D optical storage work: https://eprints.soton.ac.uk/454852/ and https://eprints.soton.ac.uk/396809/
- Bit density, feature size, optical contrast, expected radiation darkening, thermal shock tolerance, and fracture tolerance.
- Passive readout requirements: no onboard power, firmware, cryptographic keys, file-system dependency, active alignment, clock, beacon, processor, or heater.

### Calculations To Add

- `P_media_physical_intact`.
- `P_readable_given_intact`.
- `P_decode_given_partial_damage`.
- Correlated copy-loss model across physically separated media copies.
- ECC/interleaving recovery threshold.
- Minimum surviving readable area required to recover bootstrap manifest and payload.

### New Artifacts

- `mission/CAPSULE_DATA_MEDIUM_READABILITY_SPEC_v1.md`
- `artifacts/capsule_data_medium_readability.v1.json`
- `scripts/build_capsule_data_medium_readability_artifact.py`
- `scripts/ci/capsule_data_medium_readability_validate.py`
- `tests/test_capsule_data_medium_readability.py`

Required artifact fields:

- `medium_type`
- `encoding_scheme`
- `feature_size`
- `copies`
- `physical_separation`
- `ecc_scheme`
- `readout_method`
- `passive_index`
- `damage_model`
- `p_readable_quantiles`

### Acceptance Criteria

- Physical survival and readable recovery are separate probabilities.
- End-to-end encode -> damage -> readout -> ECC -> decode exists as a modeled or externally evidenced chain.
- "Hundreds of TB" is not used as the primary strength; recoverability and passive readability are.

## 9. Workstream E: Environment Corridor Evidence Pack

### Current Gap

The 1560 ly reference target is project-owned and does not yet have a fixed sky corridor. Without RA/Dec or Galactic `l,b`, no line-of-sight gas/dust integral can be defended.

### Data To Find

- Target corridor geometry for `reference-black-hole`: RA/Dec or Galactic `l,b`.
- Two or three bracketing corridors if the target is intentionally abstract.
- Local neutral H anchor from New Horizons/SWAP/NASA: https://www.nasa.gov/solar-system/new-evidence-our-neighborhood-in-space-is-stuffed-with-hydrogen/
- Voyager plasma density paper record: https://iro.uiowa.edu/esploro/outputs/journalArticle/In-Situ-Observations-of-Interstellar-Plasma/9984455269002771
- Ulysses 16-year dust source: https://arxiv.org/abs/1510.06180
- HI4PI H I survey: https://arxiv.org/abs/1610.06175
- Bayestar dust maps: https://argonaut.skymaps.info/
- NASA BON2020 / OLTARIS hooks: https://software.nasa.gov/software/MSC-26835-1
- NIST stopping-power tables: https://www.nist.gov/pml/stopping-power-range-tables-electrons-protons-and-helium-ions
- Starshot/ISM interaction paper as stress context: https://arxiv.org/abs/1608.05284

### Distributions To Add

- `corridor_dust_column_distribution`
- `dust_size_distribution_mrn`
- `dust_large_grain_tail`
- `catastrophic_mm_cm_tail`
- `gas_density_distribution`
- `gcr_solar_modulation_distribution`
- `shield_ballistic_limit_uncertainty`
- `correlation_model`

### Calculations To Add

- `N_H = integral n_H(s) ds` for gas column.
- Dust mass column and gas-to-dust sanity checks.
- `lambda(a) = A_frontal * integral n(a,s) ds` by size bin.
- `P(hit >= 1) = 1 - exp(-lambda)`.
- `P_cat = 1 - exp(-sum(lambda_i * P_penetrate_i))`.
- GCR input-deck metadata and dose/fluence bands per material layer.
- Correlated Monte Carlo policy instead of hidden independence.

### New Artifacts

- `mission/ENVIRONMENT_CORRIDOR_PACK_SPEC_v1.md`
- `artifacts/environment_corridor_pack.v1.json`
- `scripts/build_environment_corridor_pack_artifact.py`
- `scripts/ci/environment_corridor_pack_validate.py`
- `tests/test_environment_corridor_pack.py`

Required artifact fields:

- `target_corridor`
- `gas_column`
- `dust_column`
- `dust_size_regimes`
- `catastrophic_tail`
- `gcr_model`
- `plasma_model`
- `source_records`
- `correlation_policy`
- `grade_rollup`

### Acceptance Criteria

- Validator rejects any 1560 ly corridor claim without target direction or declared abstract bracketing corridors.
- Validator rejects GCR values stored as `W/m2`; radiation must be dose, fluence, particle, or model metadata.
- MRN extinction grains and Ulysses large-grain evidence remain separate regimes.
- Local VLISM values cannot be promoted to whole-path averages without map/model evidence.
- Catastrophic-tail sensitivity includes tail off, nominal tail, severe tail, p99, and p999.

## 10. Workstream F: Trajectory, Control Window, And Oberth Boundary

### Current Gap

The repository has primitive formulas for Oberth speed, ballistic time, and transverse delta-v scaling, but does not yet provide a full bounded trajectory/control artifact with Case A/Case B, `b_max`, and uncertainty growth.

### Data To Find

- Jupiter gravity assist and inbound-energy sources for nonzero `v_infinity,in`.
- Target compact-object mass consistency for Case A.
- OD/tracking assumptions for 10-50 year early correction window.
- Stretch 100-1000 year actuator, valve, seal, hibernation, attitude, and RTG/electrical degradation assumptions.
- Perturbation model: stellar encounters, Galactic tide, ISM drag, and target worldline uncertainty.
- NASA/JHUAPL interstellar-probe/Oberth references where applicable.
- NASA Parker Solar Probe TPS context for solar-proximity precedent: https://science.nasa.gov/mission/parker-solar-probe/

### Calculations To Add

- Baseline near-parabolic Sun-Oberth table for `q_au = 0.05-0.10`, SRM delta-v `2-3 km/s`, `v_infinity,in = 0`.
- Conditional speed table for `v_infinity,in > 0`.
- `b_max(R_int) = R_int * sqrt(1 + 2GM / (R_int * v_inf^2))` for Newtonian focusing, with separate GR/capture boundary for Case A.
- `delta_v_perp_req = v_inf * R_int / D`.
- `sigma_cross_track(t)` from initial state covariance, burn execution error, guidance error, and perturbation floor.
- Probability of outcome class as a distribution, not a single target hit.

### New Artifacts

- `mission/TRAJECTORY_CONTROL_OBERTH_SPEC_v1.md`
- `artifacts/trajectory_control_oberth.v1.json`
- `scripts/build_trajectory_control_oberth_artifact.py`
- `scripts/ci/trajectory_control_oberth_validate.py`
- `mission/trajectory/oberth.py`
- `tests/test_trajectory_control_oberth.py`

Required artifact fields:

- `velocity_band`
- `q_au`
- `srm_delta_v_m_s`
- `inbound_vinf_m_s`
- `outbound_vinf_km_s`
- `case_id`
- `R_int_au`
- `b_max_au`
- `delta_v_perp_req_m_s`
- `sigma_cross_track_au`
- `control_interpretation`
- `claim_boundary`

### Acceptance Criteria

- `baseline_23_34_km_s` and `conditional_35_45_km_s` are separate.
- Conditional rows include explicit inbound-energy assumptions.
- Baseline correction window is 10-50 years; 100-1000 years remains stretch and reliability-limited.
- Validator fails if Case A is described as controllable.
- Validator fails if 35-45 km/s appears without conditional assumptions.
- Validator fails if stretch corrections are presented as baseline.

## 11. Workstream G: Thermal, TPS, SRM, And Perihelion Gate

### Current Gap

The whitepaper names the TPS/SRM hot-vacuum gate, but the repo does not yet make it a structured artifact.

### Data To Find

- Parker Solar Probe TPS material and temperature precedent.
- Solar flux at 0.10 and 0.05 AU from the repo solar constant.
- C/C-SiC, carbon-carbon, insulation, adhesive, and thermal-structural behavior data.
- SRM ignition under hot vacuum after thermal soak.
- Full-scale or subscale test facility requirements.

### Calculations To Add

- Perihelion radiative load table.
- TPS thermal margin under `0.14-0.54 MW/m2`.
- SRM/TPS integration risk matrix.
- Reversion logic: if Oberth gate fails, Archive-only or Jupiter-only profile remains valid for S2 capsule study.

### New Artifacts

- `mission/PERIHELION_TPS_SRM_GATE_SPEC_v1.md`
- `artifacts/perihelion_tps_srm_gate.v1.json`
- `scripts/build_perihelion_tps_srm_gate_artifact.py`
- `scripts/ci/perihelion_tps_srm_gate_validate.py`

### Acceptance Criteria

- The Sun-Oberth architecture cannot be marked closed without TPS/SRM test evidence.
- Archive-only remains a first-class program option independent of Oberth.
- Public text does not imply Parker heritage equals qualification for this integrated stack.

## 12. Workstream H: External Evidence, Qualification, And Cost

### Current Gap

The repository has external-evidence plumbing, but accepted external records and lab records are still zero. Cost is proxy-only.

### External Records To Add

Files should live under `evidence/external_records/*.json` and pass the external evidence schema.

Minimum record types:

- `independent_reproduction`
- `independent_physics_backend`
- `capsule_qualification`
- `external_red_team`
- `public_wording_audit`

### Lab/Test Deliverables

The six deliverables that should unlock stronger capsule claims:

- `dust-tail-measurement-upgrade`
- `ballistic-limit-stack-test`
- `radiation-transport-campaign`
- `archive-media-aging-campaign`
- `bit-recovery-ecc-campaign`
- `independent-review-pack`

Each record requires:

- external lab or reviewer identity
- article or coupon configuration
- test date UTC
- raw report URI
- pass, fail, exception, or inconclusive result
- exception severity
- reviewed commit SHA
- source and output artifact hashes

### Cost/WBS Artifact

Create `artifacts/cost_wbs_basis_of_estimate.v1.json`.

Required row fields:

- `wbs_id`
- `parent_wbs_id`
- `work_package`
- `cost_class`
- `low_musd`
- `base_musd`
- `high_musd`
- `currency_year`
- `basis_of_estimate`
- `estimator_identity`
- `review_date_utc`
- `vendor_or_lab_quote_uri`
- `assumptions`
- `exclusions`
- `confidence_level`
- `maps_to_architecture_row_id`
- `procurement_gate_id`

### New Validators

- `scripts/ci/external_evidence_record_validate.py --strict`
- `scripts/ci/cost_wbs_basis_validate.py --strict`
- `scripts/ci/qualification_promotion_validate.py --strict`
- `scripts/ci/public_release_gate_validate.py --strict`
- `scripts/ci/external_record_uri_validate.py --strict --offline-manifest`

### Acceptance Criteria

- Accepted external records do not auto-promote claims.
- `qualification_complete` stays false until all six tracks have accepted records and a separate promotion review.
- `procurement_grade_estimate_available` stays false until WBS rows, vendor/lab quotes, launch integration, and regulatory/ops review exist.
- Public releases distinguish repository-publication readiness from certification or flight approval.

## 13. Evidence Grade Policy

Use the following grade semantics for new work:

| Grade | Meaning |
| --- | --- |
| A | Direct primary or official data in the right domain and units. |
| B | Primary but proxy/local data used with explicit scope limits. |
| C | Model-derived or cross-domain extrapolation with uncertainty. |
| D | Project assumption or stress prior. |

Examples:

- A: Voyager local plasma measurement, Ulysses local dust density, BON2020 model metadata, HI4PI column for a specified line of sight.
- B: local VLISM dust/gas used as a cruise prior, NASA/ESA impact context used for engineering bounds.
- C: dust map converted to physical dust mass, Starshot relativistic ISM paper adapted to nonrelativistic 45 km/s capsule.
- D: mm/cm interstellar tail over Myr, exact 10 Myr media degradation, stack penetration at tens of km/s without stack-level evidence.

## 14. Implementation Sequence

### Phase 0: Reframe Public Entry Points

Files:

- `README.md`
- `docs/README.md`
- `RESEARCH_POSITIONING.md`
- `LIMITATIONS.md`
- `mission/PUBLIC_NARRATIVE_HARDENING_SPEC_v1.md`

Gate:

- Public frame is passive archive boundary study.
- Blocked public claims are explicit.

### Phase 1: Success Metrics Contract

Files:

- `mission/SUCCESS_METRICS_SPEC_v1.md`
- `mission/MISSION_SPEC_v1.md`
- `mission/MISSION_PROBABILITY_COUPLING_SPEC_v1.md`

Gate:

- S0-S3 are machine-readable or unambiguously referenced by artifacts.

### Phase 2: Capsule Proof Stack

Files/artifacts:

- shield stack ballistic spec/artifact/builder/validator/tests
- material aging spec/artifact/builder/validator/tests
- data medium readability spec/artifact/builder/validator/tests
- passive survivability claim artifact

Gate:

- S2 can be decomposed into structure, vault, media physical survival, readability, and decoding probabilities.

### Phase 3: Environment Corridor Pack

Files/artifacts:

- `mission/ENVIRONMENT_CORRIDOR_PACK_SPEC_v1.md`
- `artifacts/environment_corridor_pack.v1.json`
- builder, validator, tests

Gate:

- No 1560 ly environment claim exists without corridor geometry or declared abstract bracketing corridors.

### Phase 4: Trajectory/Oberth/Control Artifact

Files/artifacts:

- `mission/TRAJECTORY_CONTROL_OBERTH_SPEC_v1.md`
- `artifacts/trajectory_control_oberth.v1.json`
- `mission/trajectory/oberth.py`
- builder, validator, tests

Gate:

- Baseline and conditional velocity bands are separated.
- Case A/Case B control interpretations are enforced.

### Phase 5: TPS/SRM Gate

Files/artifacts:

- `mission/PERIHELION_TPS_SRM_GATE_SPEC_v1.md`
- `artifacts/perihelion_tps_srm_gate.v1.json`
- builder, validator, tests

Gate:

- Oberth architecture remains conditional until hot-vacuum TPS/SRM evidence exists.

### Phase 6: External Evidence And WBS

Files/artifacts:

- `evidence/external_records/*.json`
- `artifacts/cost_wbs_basis_of_estimate.v1.json`
- external record validators
- cost/WBS validators
- qualification promotion validator

Gate:

- The repo can ingest external records without self-attesting or auto-promoting claims.

### Phase 7: Web And Release Surface

Files:

- `web/src/pages/*`
- `web/src/ui/*`
- `artifacts/browser_dataset.v1.json`
- release notes template

Gate:

- UI shows the proof ladder, open gates, blocked claims, and evidence grade rollup.
- No browser route recomputes authoritative probabilities client-side.

## 15. Definition Of Done For A Stronger Repository

The repository is materially stronger when all of the following are true:

- README first viewport explains passive archive survivability and finite control window.
- `paper/whitepaper.md` is no longer a parallel narrative; its core claims drive machine-readable specs.
- S0-S3 are explicit and cannot be collapsed into one success score.
- Capsule survival is decomposed into shield, material, media, readability, and decoding terms.
- Environment is corridor-based, not a scalar dust proxy.
- Trajectory/control separates baseline Oberth, conditional high speed, Case A, and Case B.
- Public routes show evidence gaps as first-class outputs, not footnotes.
- External evidence intake can accept real reviewer/lab records while blocking self-attestation.
- Cost remains proxy-only until WBS and quote evidence exists.
- `make check` verifies required docs, generated artifacts, validators, and blocked claims.

## 16. Immediate Next PR Candidates

Recommended order:

1. Public reframing + `SUCCESS_METRICS_SPEC_v1`.
2. `ENVIRONMENT_CORRIDOR_PACK_SPEC_v1` and no-corridor validator.
3. `TRAJECTORY_CONTROL_OBERTH_SPEC_v1` and baseline/conditional velocity artifact.
4. `CAPSULE_DATA_MEDIUM_READABILITY_SPEC_v1`.
5. External evidence schema tightening and first external-record validator.

These five PRs are independently reviewable and each moves the repo toward physical feasibility proof instead of adding more narrative bulk.

