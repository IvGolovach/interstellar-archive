# Mission Probability Coupling v1

`mission_probability_coupling.v1` is a deterministic, non-certifying coupling layer for user-selected mission rows.

It exists to make the mission-level probability formula explicit:

`P_archive_recoverable = P_target_delivery * P_environment_survival * P_capsule_survival * P_data_integrity * P_recovery_readout`

Only the capsule survival and data-integrity factors are currently repo-estimated. Target delivery, whole-path environment closure, launch/navigation authority, and archive recovery/readout remain external evidence gaps. The artifact must therefore publish a review proxy for the closed capsule/data factors while keeping the full mission probability marked `not_closed_external_factors_open`.

## Required Contract

- Exactly one coupling row per `user_mission_run_catalog.v1` row.
- Every row must carry the source run id, selection hash, target, velocity, flight years, source risk-budget row, and local review-pack script reference.
- Every row must expose factor records for target delivery, environment path, capsule survival, data integrity, and recovery/readout.
- Full mission probability values must remain `null` until all external factors are evidence-backed.
- The closed capsule/data proxy must be finite, bounded in `[0, 1]`, and derived from the selected Capsule Risk Budget snapshot.
- External evidence gaps and blocked claims must remain visible on every row.
- Browser surfaces may render this artifact but must not recompute probability truth.

## Non-Certification Boundary

This artifact is a factorized review coupling. It does not certify launch readiness, hardware qualification, trajectory success, black-hole encounter success, or archive recovery.
