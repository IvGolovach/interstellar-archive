# MISSION_SPEC_v1

## 1. Mission intent
The v1 mission definition evaluates whether a data-capsule concept can be represented with a physically coherent reduced-order contract for event-horizon crossing, correction authority, environment survivability, and media persistence. The objective is to define an optimization-ready contract, not to claim mission readiness or hardware-qualified capsule performance.
Capsule-related numeric priors are split between a Genesis-class geometry/mass heritage proxy and assumption-bound survivability terms; the current evidence split is tracked in `mission/CAPSULE_NUMERIC_AUDIT_v1.md`.

## 2. Baseline BH model: Schwarzschild
v1 uses a non-rotating Schwarzschild black hole model:

\[
r_s = \frac{2GM}{c^2}
\]

where `r_s` is Schwarzschild radius (m), `G = 6.67430e-11 m^3 kg^-1 s^-2`, `M` is black-hole mass (kg), and `c = 299792458 m s^-1`.

## 3. Horizon crossing definition: r <= r_s
The crossing criterion is defined on radial coordinate `r` at periapsis or at crossing epoch:

\[
\text{crossing\_condition\_met} = (r \le r_s)
\]

v1 baseline uses this as a binary geometric success sub-condition, then propagates to probabilistic mission success via `P_hit`.

## 4. "No plasma hell" constraint definition
v1 uses an explicit environment acceptance filter (proxy or strict mode):

\[
\text{environment\_acceptable} = \mathbb{1}\left(
\frac{F_{rad}}{F_{rad,max}} \le \alpha_F,
\frac{\rho_{plasma}}{\rho_{plasma,max}} \le \alpha_\rho,
\frac{S_{dust}}{S_{dust,max}} \le \alpha_S
\right)
\]

In `strict` mode, `\alpha_F = \alpha_\rho = \alpha_S = 1.0`.
In `proxy` mode, `\alpha_F = \alpha_\rho = \alpha_S = 1.2`.

## 5. Success definition
The mission success probability is:

\[
P_{success} = P_{hit} \times P_{survive} \times P_{data\_intact}
\]

with configurable threshold:

\[
\text{success} = (P_{success} \ge \text{success\_threshold}), \quad \text{success\_threshold} \in [0,1]
\]

## 6. Modes: Realistic vs Speculative
- `realistic`: only physically motivated parameters and uncertainty ranges may vary; speculative overrides are forbidden.
- `speculative`: non-physical controls may be activated but must remain explicitly tagged and warning-labeled.

Separation is machine-enforced via:
- `mission_mode`
- `speculative_overrides`
- `parameter_tags` (`mode` + `category` + warning)

## 7. Correction window allowed and bounded
Mid-course correction is allowed only inside declared window `[start_year, end_year]` with bounded duration and actuation budget:
- `max_duration_years <= 2000`
- finite `delta_v_budget_mps`
- finite `power_available_w`
- finite guidance and execution uncertainty distributions.

## 8. What is explicitly not covered in v1
- Kerr/charged black-hole metrics.
- Full GR ray-tracing or magnetohydrodynamics.
- End-to-end flight software, autonomy stack, and hardware qualification campaign.
- Bit-level ECC failure modeling under full relativistic radiation transport.
