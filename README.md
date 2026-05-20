# Interstellar Archive

## Thesis
This repository treats long-horizon mission reasoning as an evidence-governed engineering problem, not a narrative thought experiment.
The public contract is deterministic computation plus explicit uncertainty, versioning, and governance enforcement.
Every non-trivial claim should be reproducible from tracked inputs and scripts, or marked as speculative with visible boundaries.
The goal is not to prove optimistic outcomes, but to make assumptions auditable and model drift impossible to hide.

## Research Signals
[![Determinism](https://img.shields.io/badge/Determinism-checksum--verified-0b7d3b)](sim/golden/golden_checksum.txt)
[![Traceability](https://img.shields.io/badge/Traceability-registry--complete-0b7d3b)](artifacts/research_signals.json)
[![External validation](https://img.shields.io/badge/External%20validation-open-6a6a6a)](evidence/external_records/README.md)
[![Version](https://img.shields.io/badge/Version-0.3.0-465d84)](VERSION)
[![License](https://img.shields.io/badge/License-CC--BY--4.0-6a6a6a)](LICENSE)

## Abstract
This repository publishes a deterministic, schema-driven simulation and evidence workflow for long-horizon encounter analysis.
It is structured as a reproducible research artifact and publication candidate.
Claims are tied to assumptions, models, artifacts, and sources through reproducible checks.
Simulation outputs are guarded by a golden checksum and CI enforcement to prevent silent drift.
Governance documents define decision traceability, reproducibility requirements, and explicit non-goals.

## What this project is
- A reproducible research demo with deterministic simulation in `sim/` and browser UI in `web/`.
- A public evidence chain linking `claim -> assumption -> model -> artifact -> source`.
- A governance-layered repository with auditable decisions and change rationale in `engineering/`.
- A small hash-routed workspace with mission, parameter, failure-surface, and optimization views over one tracked browser dataset.
- An artifact-backed Capsule Lab that exposes capsule materials, target/flight-time/velocity choices, and p05/p50/p95 capsule-only survivability rows.
- A Mission Feasibility screen artifact that makes target, velocity, flight years, dust/gas exposure, risk-budget linkage, and energy/cost proxy blockers inspectable.
- A User Mission Run catalog, Runtime Scenario Generation artifact, and strict local pack validator that assign stable run ids, expose run recipes, and execute the Mission DAG into ignored `ops/reports/` evidence packs without claiming a server run store.
- A Mission Probability Coupling artifact that factors selected mission probability into open external factors plus a closed capsule/data review proxy backed by compact DAG snapshots.
- An Uncertainty Interactions artifact that exposes pairwise uncertainty residual screens while keeping covariance and correlation evidence external.
- An Evidence Upgrade Campaign artifact that ranks source-review work across all parameter claims while keeping trust promotion and source correctness external.
- An Optimization v2 artifact that adds four-axis Pareto screening over success, risk, qualification gap, and cost proxy without claiming a global optimum, procurement estimate, or hardware qualification.
- A Mission DAG v2 boundary artifact that maps every DAG module to v1 wrapper support, v2 trace/backend requirements, failure taxonomy coverage, and blocked independent-backend claims.
- A full-v2 roadmap closure artifact that tracks all 15 complex next-step items as repo-native contracts while keeping external evidence gaps open and visible.
- An External Proof route and artifact suite that tracks review execution records, repo analytic cross-checks, capsule qualification matrix, exportable reproduction packs, external evidence intake rules, evidence closure, and publication-readiness gates without fabricating third-party validation or lab evidence.
- The public parameter workspace is intentionally limited to mission/design/environment parameters; internal model literals stay in canonical registries but are excluded from the browser-facing index.

## What this project is not
- Not a mission-ready flight system.
- Not a full-fidelity physical model of all interstellar hazards.
- Not a substitute for hardware qualification, regulatory certification, or operational safety review.

## Scientific Trust Model
- `realistic` results are policy-facing outputs: no speculative (`D`-grade) parameter influence is allowed.
- `speculative` results are exploratory outputs: non-physical controls are allowed, but always explicitly labeled.
- Dual-mode reporting is mandatory for mission runs; realistic and speculative outputs are never merged into a single undisclosed score.

## Deterministic Reproducibility Contract
- Simulation core is pure and seeded; no runtime randomness or wall-clock dependence in model math.
- Canonical serialization is stable and checksum-based.
- CI verifies golden output integrity and blocks unauthorized drift.

## Reproducibility Contract (short version)
1. Clone repository and install dependencies.
2. Run deterministic checks (`make check` and `npm run golden:check --prefix web`).
3. Treat checksum drift as a blocking event unless model evolution protocol is followed.

## Reproducibility in 30 seconds
```bash
make check
python3 scripts/ci/required_paths_validate.py --strict
npm run golden:check --prefix web
python3 scripts/mission_baseline_check.py --verify-deterministic
```

Full contract: [REPRODUCIBILITY.md](REPRODUCIBILITY.md)
Repository map: [docs/README.md](docs/README.md)

## Web Workspace
The web workspace is included in `web/` and can be built locally. GitHub Pages is intentionally disabled while this private mirror is prepared for future public release.

Workspace routes:
- `#/mission`
- `#/parameters`
- `#/failure-surface`
- `#/optimization`
- `#/optimization/optv2-pt-000`
- `#/capsule-lab`
- `#/mission-feasibility`
- `#/mission-runs`
- `#/mission-probability`
- `#/uncertainty-interactions`
- `#/evidence-campaign`
- `#/external-proof`

## Golden checksum section
- Current golden checksum: `bda117f5294cdd3147506d0b3f3f92c99d4113857631230b05bacdd0bd70288c`
- Source of truth: `sim/golden/golden_checksum.txt`
- Determinism status payload: `artifacts/determinism_status.json`

## Architecture link
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/ARTIFACT_POLICY.md](docs/ARTIFACT_POLICY.md)

## Governance link
- [engineering/GOVERNANCE.md](engineering/GOVERNANCE.md)
- [engineering/DECISIONS.md](engineering/DECISIONS.md)
- [engineering/CHANGELOG.md](engineering/CHANGELOG.md)
- [PROJECT_TIMELINE.md](PROJECT_TIMELINE.md)
- [PUBLICATION_POLICY.md](PUBLICATION_POLICY.md)

## Public Research Artifacts
- [CITATION.cff](CITATION.cff)
- [THREAT_MODEL.md](THREAT_MODEL.md)
- [MODEL_VERSION.json](MODEL_VERSION.json)
- [artifacts/research_signals.json](artifacts/research_signals.json)

## Version + Release section
- Current repository version: see `VERSION`
- This private mirror starts from the `0.3.0` publication-candidate content snapshot.
- Fresh public release tags should be created only after the mirror passes local and remote validation gates.
