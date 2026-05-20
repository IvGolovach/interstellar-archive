# Architecture Contract

## 1. System Overview

This repository is a research-facing engineering package with two layers:

1. Narrative layer (`paper/`, `appendix/`, `refs/`) for scientific framing and assumptions.
2. Evidence layer (`evidence/`, `models/`, `scripts/`, `artifacts/`) for deterministic verification of quantitative claims.

The evidence layer is authoritative for numeric claims used in public communication.

## 2. Core Invariants

1. Every quantitative claim has a unique claim ID (`C-xxxx`) and explicit numeric checks.
2. Every claim resolves a complete chain:
   `claim -> assumption -> model -> artifact -> source`.
3. Evidence scripts are deterministic for fixed inputs and Python runtime.
4. Artifact outputs include checksums and generation commit linkage.
5. Governance files in `engineering/` are human-authored and append-only where specified.

## 3. Data Model (high-level)

- `evidence/claims.json`:
  Claim registry with statement, references, checks, and linked model output paths.
- `evidence/assumptions.json`:
  Structured assumptions with confidence and impact surface.
- `evidence/sources.json`:
  Source registry including local docs, formulas/constants, and bibliography keys.
- `artifacts/`:
  Generated verification outputs (`claim_values`, tables, traceability matrix, report) and artifact-pack metadata.

## 4. Critical Failure Modes

1. Claim drift:
   Narrative claim changed without corresponding registry/model update.
2. Traceability break:
   Claim points to missing assumptions/sources/artifacts.
3. Silent behavior change:
   Core model code changes without changelog/governance update.
4. Reproducibility break:
   Script output changes but checksums/metadata are not refreshed.

## 5. Trust Assumptions

1. Maintainers run governance checks locally before push.
2. CI remains enabled and required for protected branches.
3. Public artifact consumers can run scripts in Python 3.11 environment.
4. Bibliography and source references are kept current when claims evolve.

## 6. What This System Explicitly Does NOT Guarantee

1. It does not guarantee physical mission feasibility.
2. It does not guarantee that assumptions are universally accepted.
3. It does not eliminate modeling uncertainty; it makes uncertainty explicit and testable.
4. It does not replace high-fidelity mission software verification pipelines.

