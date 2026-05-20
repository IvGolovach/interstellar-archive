# UNCERTAINTY_MODEL_v1

`mission/UNCERTAINTY_MODEL_v1.json` is the machine-readable uncertainty contract used by mission validation and evidence enforcement.

Each uncertainty entry declares:
- `parameter_id`
- `distribution`
- `parameters`
- `bounds` (`min`, `max`)
- `units`
- `mode`
- `category`
- `source_rationale`

## Contract rules

1. Uncertainty entries are explicit; no hidden or implicit constants are allowed.
2. Any `ParameterClaim` with `value_mode=distribution` in `mission/EVIDENCE_REGISTRY_v1.json` must map to a valid uncertainty entry.
3. Bounds must satisfy `min < max`.
4. Distribution family must be one of: `normal`, `lognormal`, `uniform`, `triangular`.

## v1 modeled uncertainty groups

1. Navigation / initial state uncertainty.
2. Correction execution uncertainty.
3. Environment variability (dust/radiation/plasma proxies).
4. Material degradation uncertainty.

This is a bounded v1 approximation. It is suitable for reproducible contract enforcement and sensitivity work, not for high-fidelity mission certification.
