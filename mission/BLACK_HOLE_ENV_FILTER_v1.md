# BLACK_HOLE_ENV_FILTER_v1

## 1. Purpose

Define a checkable environment admissibility condition for the requirement "cross the horizon without entering a prohibitive plasma/radiative regime".

## 2. v1 filter type

v1 uses a simplified **proxy filter** (optionally strict). It is explicitly a surrogate model, not full accretion MHD.

Inputs:
- `F_rad` = radiative flux at periapsis (`W/m^2`)
- `rho_plasma` = plasma density proxy (`1/m^3`)
- `S_dust` = dust flux scale (`dimensionless`)
- thresholds: `F_rad,max`, `rho_plasma,max`, `S_dust,max`

Mode coefficients:
- `strict`: `(alpha_F, alpha_rho, alpha_S) = (1.0, 1.0, 1.0)`
- `proxy`: `(alpha_F, alpha_rho, alpha_S) = (1.2, 1.2, 1.2)`

## 3. Formal predicate

\[
\text{is\_bh\_environment\_acceptable}(p) =
\left(\frac{F_{rad}}{F_{rad,max}} \le \alpha_F\right)
\land
\left(\frac{\rho_{plasma}}{\rho_{plasma,max}} \le \alpha_\rho\right)
\land
\left(\frac{S_{dust}}{S_{dust,max}} \le \alpha_S\right)
\]

Return type: `bool`.

## 4. Deterministic reference implementation

```python
def is_bh_environment_acceptable(params):
    mode = params["environment_acceptance_mode"]
    alpha = 1.0 if mode == "strict" else 1.2
    return (
        params["environment_model"]["radiative_flux_w_m2"] <= alpha * params["bh_parameters"]["max_radiative_flux_w_m2"]
        and params["environment_model"]["plasma_density_proxy_m3"] <= alpha * params["bh_parameters"]["max_plasma_density_proxy_m3"]
        and params["environment_model"]["dust_flux_scale"] <= alpha * params["bh_parameters"]["max_dust_flux_scale"]
    )
```

## 5. v2 improvement path

Planned v2 upgrades:
1. Replace scalar plasma proxy with radial profile model.
2. Couple accretion luminosity fraction to flux model with uncertainty propagation.
3. Add thermal load time integral (`J/m^2`) instead of instantaneous flux threshold only.
