# LIMITATIONS_AND_NON_GOALS_APPENDIX

## 1. Known limitations in mission-definition v1

1. Schwarzschild-only geometry excludes spin effects and frame dragging.
2. Environment filter is proxy-based and does not model full plasma thermodynamics.
3. Survival model uses compact hazard proxies instead of full coupled thermal/radiation transport.
4. Guidance/actuation model is reduced-order and not tied to a hardware-qualified control stack.
5. Data integrity is modeled at physical-media level, not at full ECC/bit-error layer.

## 2. Non-goals

1. v1 does not claim end-to-end mission feasibility certification.
2. v1 does not optimize mission design; it defines optimization-ready structure only.
3. v1 does not include launch, legal, licensing, or procurement constraints.

## 3. Explicit assumptions

- Parameter bounds marked as `estimate` or `placeholder` are assumptions, not measured mission data.
- Proxy thresholds (`max_radiative_flux`, `max_plasma_density_proxy`, `max_dust_flux_scale`) are bounded design guards.
- Speculative parameters are explicitly isolated by `mission_mode` and warning text.

## 4. Failure mode examples

1. Crossing condition met but environment unacceptable -> `P_survive` collapse.
2. Environment acceptable but correction uncertainty high -> reduced `P_hit`.
3. High `P_hit` and `P_survive` with poor media margin -> low `P_data_intact`.
