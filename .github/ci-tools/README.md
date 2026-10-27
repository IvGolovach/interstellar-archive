# CI routing and Pages recovery

CI-only pushes (AGENTS.md and .github/**) do not publish Pages. Runtime changes,
including a file moved from web/ into .github/, retain the normal publication path.

If a runtime deployment fails, a later CI-only push intentionally does not retry
publication. After explicit release authorization, run `web-sim-deterministic`
on `main` with `publish_pages=true` to verify and publish the current main.
Verification and the floating-point matrix must pass before the existing Pages
environment is used. The input defaults to false; a normal manual verification
does not publish. The failed original runtime workflow can also be retried at
its exact revision when that is the desired release.
