# Engineering Changelog

Append-only engineering changelog for governance-critical changes in the clean mirror.

Historical entries below preserve the wording that was current when the repository was still being prepared privately. The current public repository is the reviewed `interstellar-archive` publication snapshot.

## 2026-05-19 - Clean Mirror Bootstrap
- Date (UTC): 2026-05-20T00:57:40Z
- Commit: 18f33501e24f05efccf3be4fb1f5fc240ab14b8a
- Type: infra
- Summary: Created the private clean mirror baseline from the retained provenance snapshot and removed old public-surface metadata from the mirror.
- Link: private-provenance:18f33501e24f05efccf3be4fb1f5fc240ab14b8a
- Rationale: The public-candidate repository needs a fresh history, neutral metadata, and validation-ready governance files while the original workbench remains private for provenance.

## 2026-05-20 - Private Mirror CI Bootstrap
- Date (UTC): 2026-05-20T01:15:45Z
- Commit: 4bf46ecd9e9eb8a059367df9d35ef4155f0c8842
- Type: infra
- Summary: Made remote-proof validation and initial-push CI work before the new private GitHub remote exists.
- Link: private-provenance:18f33501e24f05efccf3be4fb1f5fc240ab14b8a
- Rationale: The clean mirror must validate locally before first push and must not deploy Pages while the GitHub repository remains private.

## 2026-05-26 - Public Repository Surface Cleanup
- Date (UTC): 2026-05-27T00:48:12Z
- Commit: ef555e9a2d2ed076181b90cba6aafd46f31b4fdd
- Type: doc
- Summary: Updated public-facing documentation after the repository became public and restored hosted-demo publication through the existing GitHub Pages workflow.
- Link: https://github.com/IvGolovach/interstellar-archive/commit/ef555e9a2d2ed076181b90cba6aafd46f31b4fdd
- Rationale: The published repository should describe itself as the current public research artifact, not as a pre-publication staging repository.
