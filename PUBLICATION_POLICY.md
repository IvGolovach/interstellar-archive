# Publication Policy

This public repository is a reviewed publication snapshot of a retained archival source repository. It publishes reproducible artifacts, source code, documentation, and validation checks. It must not publish operational metadata from the retained source history.

## Publishable

- Authored research documents that describe assumptions, limitations, and reproducibility boundaries.
- Deterministic source code, tests, schemas, and validation scripts.
- Tracked generated baselines when they are described as repository-native artifacts.
- Public-facing timeline summaries that describe real development phases without exposing branch, PR, or account metadata from the retained source history.

## Not Publishable

- Retained source-repository Git history, branch names, pull requests, release objects, or action logs.
- Personal email metadata or local filesystem paths.
- Placeholder citation metadata, placeholder PDF renders, or old repository URLs.
- Claims that imply third-party validation, certification, hardware qualification, mission readiness, or procurement-grade estimates.

## Required Wording Boundary

Use terms such as `reproducible research artifact`, `publication candidate`, `deterministic reduced-order model`, `repo-native validation`, and `external evidence remains open`.

Avoid terms such as `certified`, `flight-ready`, `qualified`, `externally validated`, `validated mission design`, or `guaranteed survivability` unless external records supporting those claims are committed under the external evidence policy.

## Release Gate

Before future release tags or hosted-demo updates, the repository must pass local validation, web validation, privacy/provenance scans, and remote GitHub checks for the exact pushed commit. GitHub Pages deployment must be produced only by the reviewed GitHub Actions workflow on `main`.
