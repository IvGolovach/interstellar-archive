# Independent Physics Backend Comparison Spec v1

## Scope

`artifacts/independent_physics_backend_comparison.v1.json` records repository-local closed-form cross-checks against committed mission artifacts and keeps the external backend requirement visible.

## Required Semantics

- `comparison_status` must be `repo_analytic_crosscheck_ready_external_backend_open`.
- The artifact may compare closed-form calculations such as Schwarzschild radius, ballistic flight time, velocity fraction of `c`, swept dust mass, and capsule kinetic energy.
- `independent_external_backend_complete`, `cross_backend_comparison_completed`, `high_fidelity_state_trace_complete`, and `independent_physics_backend_validated` must remain `false`.
- Relative error for repository arithmetic checks must be bounded, but arithmetic agreement is not physical validation.

## Evidence Boundary

This artifact is a deterministic repo analytic cross-check, not an independently implemented high-fidelity physics backend, external benchmark report, MHD/geodesic integration, or material-transport simulation.
