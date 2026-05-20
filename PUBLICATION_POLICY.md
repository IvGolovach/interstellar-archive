# Publication Policy

This repository is prepared as a future public mirror of a private research workbench. The mirror is allowed to publish reproducible artifacts, source code, documentation, and validation checks. It must not publish private operational metadata from the workbench history.

## Publishable

- Authored research documents that describe assumptions, limitations, and reproducibility boundaries.
- Deterministic source code, tests, schemas, and validation scripts.
- Tracked generated baselines when they are described as repository-native artifacts.
- Public-facing timeline summaries that describe real development phases without exposing private branch, PR, or account metadata.

## Not Publishable

- Private workbench Git history, branch names, pull requests, release objects, or action logs.
- Personal email metadata or local filesystem paths.
- Placeholder citation metadata, placeholder PDF renders, or old repository URLs.
- Claims that imply third-party validation, certification, hardware qualification, mission readiness, or procurement-grade estimates.

## Required Wording Boundary

Use terms such as `reproducible research artifact`, `publication candidate`, `deterministic reduced-order model`, `repo-native validation`, and `external evidence remains open`.

Avoid terms such as `certified`, `flight-ready`, `qualified`, `externally validated`, `validated mission design`, or `guaranteed survivability` unless external records supporting those claims are committed under the external evidence policy.

## Release Gate

Before a public release, the mirror must pass local validation, web validation, privacy/provenance scans, and remote GitHub checks for the exact pushed commit. GitHub Pages should stay disabled until the public copy and research signals are intentionally reviewed.
