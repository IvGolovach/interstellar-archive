#!/usr/bin/env python3
"""
proof.py — every number quoted in proof/README.md is produced by this file.

    python3 proof.py            # prints all results, writes results.json
    python3 proof.py --figures  # also writes figures/*.png

Sections
  A. Launch: Sun-Oberth escape speed, flight times
  B. Targets: heliocentric kinematics of the nearest known black holes,
     straight-line intercept feasibility, and full orbit integration in the
     Galactic potential (galpy MWPotential2014) for the reachable one
  C. Survival: dust column, erosion, large-grain impacts, Whipple ballistic
     limit, cosmic-ray dose, gas sputtering and drag
  D. Capture: relativistic capture cross-section, arrival dispersion from
     astrometry and stellar encounters, P(capture), P(close pass),
     and the target-independent "any black hole in the Galaxy" estimate

Dependencies: numpy, scipy, galpy (+astropy). matplotlib only for --figures.
All literature inputs are listed in SOURCES.md with the value used here.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, asdict

import numpy as np
from scipy.optimize import minimize

# ----------------------------------------------------------------------------
# Physical constants (SI) and unit conversions
# ----------------------------------------------------------------------------
G = 6.67430e-11
C = 299_792_458.0
M_SUN = 1.98847e30
MU_SUN = 1.32712440018e20          # GM_sun, m^3 s^-2
R_SUN = 6.957e8
AU = 1.495978707e11
PC = 3.0856775814913673e16
LY = 9.4607304725808e15
YR = 365.25 * 86400.0
MYR = 1e6 * YR
M_H = 1.6735575e-27                # hydrogen atom mass, kg
EV = 1.602176634e-19
KM_S_PER_PC_MYR = PC / MYR / 1e3   # 1 pc/Myr = 0.9778 km/s
MAS_YR_PC_TO_KM_S = 4.740470463    # v_t [km/s] = 4.74047 * mu[arcsec/yr] * d[pc]

results: dict = {}


def log(section: str, key: str, value, unit: str = "", note: str = ""):
    results.setdefault(section, {})[key] = {"value": value, "unit": unit, "note": note}
    if isinstance(value, float):
        s = f"{value:.4g}"
    else:
        s = str(value)
    print(f"  {key:<46s} = {s} {unit}  {('# ' + note) if note else ''}")


# ============================================================================
# A. LAUNCH
# ============================================================================
def perihelion_speed(q_m: float, vinf_in: float = 0.0) -> float:
    return math.sqrt(vinf_in**2 + 2.0 * MU_SUN / q_m)


def oberth_vinf(q_au: float, dv: float, vinf_in: float = 0.0) -> float:
    """Asymptotic heliocentric speed after a prograde impulse dv at perihelion q (vis-viva)."""
    q = q_au * AU
    vp = perihelion_speed(q, vinf_in) + dv
    return math.sqrt(max(vp**2 - 2.0 * MU_SUN / q, 0.0))


def section_A():
    print("\nA. LAUNCH — Sun-Oberth escape")
    for q_au in (0.05, 0.10):
        for dv in (2000.0, 3000.0):
            v = oberth_vinf(q_au, dv)
            log("A", f"vinf_q{q_au:.2f}au_dv{int(dv)}", v / 1e3, "km/s",
                f"perihelion {q_au} AU = {q_au*AU/R_SUN:.1f} R_sun, burn {dv/1e3:.0f} km/s, parabolic inbound")
    v_cond = oberth_vinf(0.05, 3000.0, vinf_in=30e3)
    log("A", "vinf_q0.05au_dv3000_inbound30", v_cond / 1e3, "km/s", "conditional: needs 30 km/s inbound excess")
    log("A", "solar_flux_0.05au", 1361.0 / 0.05**2 / 1e6, "MW/m^2", "inverse square from 1361 W/m^2")
    log("A", "solar_flux_parker_perihelion_9.86Rsun", 1361.0 / ((9.86 * R_SUN / AU) ** 2) / 1e6, "MW/m^2",
        "Parker Solar Probe reached 9.86 R_sun = 0.046 AU")
    for d_ly, v in ((1560.0, 34.0), (1560.0, 45.0), (3460.0, 34.0)):
        t = d_ly * LY / (v * 1e3) / MYR
        log("A", f"straight_flight_time_{int(d_ly)}ly_{int(v)}kms", t, "Myr")


# ============================================================================
# B. TARGETS AND REACHABILITY
# ============================================================================
@dataclass
class Target:
    name: str
    ra_deg: float
    dec_deg: float
    distance_pc: float
    distance_err_pc: float
    pmra_mas_yr: float
    pmra_err: float
    pmdec_mas_yr: float
    pmdec_err: float
    rv_km_s: float | None
    rv_err: float | None
    bh_mass_msun: float | None

    @property
    def mu_mas_yr(self) -> float:
        return math.hypot(self.pmra_mas_yr, self.pmdec_mas_yr)

    @property
    def v_tan(self) -> float:
        return MAS_YR_PC_TO_KM_S * self.mu_mas_yr / 1e3 * self.distance_pc

    @property
    def v_rad(self) -> float | None:
        return self.rv_km_s


def load_targets(path="targets.json") -> list[Target]:
    raw = json.load(open(path))["targets"]
    keys = Target.__dataclass_fields__.keys()
    return [Target(**{k: t[k] for k in keys}) for t in raw]


def straight_line_intercept(d_pc: float, v_r: float, v_t: float, vinf: float):
    """Straight-line kinematics in the heliocentric inertial frame.
    Target at distance D receding at v_r with transverse speed v_t.
    A capsule with speed vinf can meet it at time t iff |r0 + v_bh t| = vinf t, i.e.
    sqrt((D/t + v_r)^2 + v_t^2) = vinf.  Required speed is >= v_t for every t.
    Returns flight time in Myr, or None if no solution."""
    if vinf <= v_t:
        return None
    denom = math.sqrt(vinf**2 - v_t**2) - v_r      # = D/t
    if denom <= 0:
        return None
    D = d_pc * PC
    return D / (denom * 1e3) / MYR


def section_B_straight(targets):
    print("\nB1. TARGETS — heliocentric kinematics and straight-line reachability")
    rows = []
    for t in targets:
        row = {"name": t.name, "d_pc": t.distance_pc, "v_tan_km_s": round(t.v_tan, 1),
               "v_rad_km_s": t.v_rad, "bh_mass": t.bh_mass_msun}
        for vinf in (34.0, 45.0):
            if t.v_rad is None:
                row[f"t_intercept_{int(vinf)}"] = "no RV" if vinf > t.v_tan else "unreachable (v_tan)"
            else:
                tt = straight_line_intercept(t.distance_pc, t.v_rad, t.v_tan, vinf)
                row[f"t_intercept_{int(vinf)}"] = None if tt is None else round(tt, 1)
        rows.append(row)
        print(f"  {t.name:<34s} d={t.distance_pc:5.0f} pc  v_tan={t.v_tan:6.1f}  v_rad={str(t.v_rad):>7s}"
              f"  t34={row['t_intercept_34']}  t45={row['t_intercept_45']} Myr")
    results.setdefault("B", {})["straight_line_table"] = rows
    return rows


# ---- Galactic-potential orbit integration --------------------------------
RO, VO, ZO = 8.0, 220.0, 0.0208   # galpy defaults; MWPotential2014 was fit with these


def _galpy():
    from galpy.orbit import Orbit
    from galpy.potential import MWPotential2014
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    return Orbit, MWPotential2014, u, SkyCoord


def bh_orbit(t: Target, distance_pc=None):
    Orbit, pot, u, SkyCoord = _galpy()
    d = t.distance_pc if distance_pc is None else distance_pc
    sc = SkyCoord(ra=t.ra_deg * u.deg, dec=t.dec_deg * u.deg, distance=d * u.pc,
                  pm_ra_cosdec=t.pmra_mas_yr * u.mas / u.yr, pm_dec=t.pmdec_mas_yr * u.mas / u.yr,
                  radial_velocity=t.rv_km_s * u.km / u.s, frame="icrs")
    return Orbit(sc, ro=RO, vo=VO, zo=ZO, solarmotion="schoenrich")


def capsule_orbit(l_deg: float, b_deg: float, vinf_km_s: float):
    """Capsule leaving the Sun with heliocentric asymptotic velocity vinf along Galactic (l, b)."""
    Orbit, pot, u, SkyCoord = _galpy()
    sc = SkyCoord(l=l_deg * u.deg, b=b_deg * u.deg, distance=1e-6 * u.pc,
                  pm_l_cosb=0 * u.mas / u.yr, pm_b=0 * u.mas / u.yr,
                  radial_velocity=vinf_km_s * u.km / u.s, frame="galactic")
    return Orbit(sc, ro=RO, vo=VO, zo=ZO, solarmotion="schoenrich")


def integrate_xyz(orbit, ts_myr: np.ndarray):
    Orbit, pot, u, SkyCoord = _galpy()
    orbit.integrate(ts_myr * u.Myr, pot, method="dop853_c")
    return np.vstack([orbit.x(ts_myr * u.Myr), orbit.y(ts_myr * u.Myr), orbit.z(ts_myr * u.Myr)]).T  # kpc


def min_separation(xyz_a: np.ndarray, xyz_b: np.ndarray, ts: np.ndarray):
    d = np.linalg.norm(xyz_a - xyz_b, axis=1)
    i = int(np.argmin(d))
    # parabolic refinement around the minimum
    if 0 < i < len(d) - 1:
        y0, y1, y2 = d[i - 1], d[i], d[i + 1]
        denom = (y0 - 2 * y1 + y2)
        if denom > 0:
            delta = 0.5 * (y0 - y2) / denom
            dt = ts[1] - ts[0]
            return float(y1 - 0.25 * (y0 - y2) * delta), float(ts[i] + delta * dt)
    return float(d[i]), float(ts[i])


def galactic_lb(t: Target):
    Orbit, pot, u, SkyCoord = _galpy()
    sc = SkyCoord(ra=t.ra_deg * u.deg, dec=t.dec_deg * u.deg, frame="icrs").galactic
    return float(sc.l.deg), float(sc.b.deg)


def fibonacci_sphere(n: int):
    """n roughly uniform directions on the sphere, returned as (l_deg, b_deg)."""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)              # polar angle from +z
    theta = np.pi * (1 + 5**0.5) * i
    b = 90.0 - np.degrees(phi)
    l = np.degrees(theta) % 360.0
    return l, b


def solve_intercept(t: Target, vinf: float, distance_pc=None, t_max_myr=250.0, n_steps=5001,
                    n_grid=2000, n_refine=4, verbose=False):
    """Find the launch direction (l, b) that minimises the closest approach to the target in the
    Galactic potential for a given heliocentric launch speed.  Global search over the whole sky
    (the Galactic orbit curves strongly over ~100 Myr, so the landscape is multimodal), then
    Nelder-Mead refinement of the best grid minima.  Returns (miss_pc, t_myr, l, b)."""
    ts = np.linspace(0.0, t_max_myr, n_steps)
    xyz_bh = integrate_xyz(bh_orbit(t, distance_pc), ts)
    l0, b0 = galactic_lb(t)

    def miss(p):
        l, b = p
        b = max(min(b, 89.9), -89.9)
        xyz_c = integrate_xyz(capsule_orbit(l, b, vinf), ts)
        return min_separation(xyz_c, xyz_bh, ts)[0]

    ls, bs = fibonacci_sphere(n_grid)
    grid = np.array([miss((l, b)) for l, b in zip(ls, bs)])
    order = np.argsort(grid)
    # keep the best n_refine starting points that are not near-duplicates
    starts = []
    for i in order:
        if all(math.hypot(ls[i] - ls[j], bs[i] - bs[j]) > 15 for j in starts):
            starts.append(i)
        if len(starts) >= n_refine:
            break
    best = None
    for i in starts:
        res = minimize(miss, x0=[ls[i], bs[i]], method="Nelder-Mead",
                       options={"xatol": 1e-4, "fatol": 1e-8, "maxiter": 600})
        if best is None or res.fun < best.fun:
            best = res
    l, b = best.x
    xyz_c = integrate_xyz(capsule_orbit(l, b, vinf), ts)
    m, tm = min_separation(xyz_c, xyz_bh, ts)
    if verbose:
        print(f"    vinf={vinf:5.1f} km/s: min separation {m*1e3:9.3f} pc at t={tm:6.1f} Myr, aim (l,b)=({l:.2f},{b:.2f}) vs now ({l0:.2f},{b0:.2f})")
    return m * 1e3, tm, l, b


def section_B_galpy(targets, cache_path="galpy_cache.json", t_max_myr=300.0):
    """Global intercept search in the Galactic potential for every target with a measured systemic
    velocity, at 34 and 45 km/s; a launch-speed scan for A0620-00 (both distance hypotheses); and
    the minimal launch speed for A0620-00 and Gaia BH1.  Results are cached (each solve ~25 s)."""
    import os
    print("\nB2. ORBIT INTEGRATION in MWPotential2014 (galpy), full-sky launch-direction search, t <= %g Myr" % t_max_myr)
    if os.path.exists(cache_path):
        out = json.load(open(cache_path))
        print("  (loaded cached results from %s; delete it to recompute)" % cache_path)
    else:
        out = {"all_targets": [], "A0620_scan": {}, "min_vinf": {}}
        for t in targets:
            if t.rv_km_s is None:
                continue
            for vinf in (34.0, 45.0):
                m, tm, l, b = solve_intercept(t, vinf, t_max_myr=t_max_myr)
                out["all_targets"].append({"name": t.name, "vinf_km_s": vinf, "min_miss_pc": round(float(m), 3),
                                           "t_myr": round(float(tm), 1), "aim_l_deg": round(float(l), 2), "aim_b_deg": round(float(b), 2)})
                print(f"  {t.name:<32s} v={vinf:4.0f}: miss {m:8.3f} pc at {tm:6.1f} Myr, aim l={l:6.1f} b={b:6.1f}")
        a0620 = next(t for t in targets if t.name.startswith("A0620"))
        for dist_label, d in (("photometric_1060pc", 1060.0), ("gaia_parallax_1435pc", 1435.0)):
            rows = []
            for vinf in (20.0, 25.0, 30.0, 34.0, 38.0, 45.0, 60.0):
                m, tm, l, b = solve_intercept(a0620, vinf, distance_pc=d, t_max_myr=t_max_myr)
                rows.append({"vinf_km_s": vinf, "min_miss_pc": round(m, 3), "t_myr": round(tm, 1),
                             "aim_l_deg": round(l, 2), "aim_b_deg": round(b, 2)})
                print(f"  A0620 {dist_label} v={vinf:4.0f}: miss {m:8.3f} pc at {tm:6.1f} Myr")
            out["A0620_scan"][dist_label] = rows
        for t in (a0620, next(t for t in targets if t.name == "Gaia BH1")):
            lo, hi = 5.0, 60.0
            for _ in range(8):
                mid = 0.5 * (lo + hi)
                m, tm, l, b = solve_intercept(t, mid, t_max_myr=t_max_myr, n_grid=1500)
                if m < 1.0:
                    hi = mid
                else:
                    lo = mid
            m, tm, l, b = solve_intercept(t, hi, t_max_myr=t_max_myr)
            out["min_vinf"][t.name] = {"vinf_km_s": round(hi, 1), "t_myr": round(tm, 1), "miss_pc": round(m, 3)}
            print(f"  minimal launch speed for {t.name}: {hi:.1f} km/s (flight {tm:.1f} Myr, miss {m:.2f} pc)")
        json.dump(out, open(cache_path, "w"), indent=1)
    if "A0620_earliest" not in out or any("scan_t_max" not in v for v in out["A0620_earliest"].values()):
        # earliest intercept: shortest time window in which an intercept (miss < 0.5 pc) exists
        a0620 = next(t for t in targets if t.name.startswith("A0620"))
        out["A0620_earliest"] = {}
        for vinf in (34.0, 45.0):
            found = None
            for t_max in (25.0, 35.0, 45.0, 60.0, 80.0):
                m, tm, l, b = solve_intercept(a0620, vinf, t_max_myr=t_max, n_steps=2001, n_grid=1500)
                print(f"  A0620 v={vinf:.0f} window t<={t_max:.0f} Myr: miss {m:.3f} pc at {tm:.1f} Myr")
                if m < 0.5:
                    found = {"vinf_km_s": vinf, "min_miss_pc": round(float(m), 3), "t_myr": round(float(tm), 1),
                             "aim_l_deg": round(float(l), 2), "aim_b_deg": round(float(b), 2), "scan_t_max": t_max}
                    break
            out["A0620_earliest"][f"v{int(vinf)}"] = found
        json.dump(out, open(cache_path, "w"), indent=1)
    for k, v in out["A0620_earliest"].items():
        log("B", f"A0620_earliest_intercept_{k}", v, "")
    for r in out["all_targets"]:
        log("B", f"galpy_{r['name'].split(' (')[0].replace(' ', '_')}_v{int(r['vinf_km_s'])}",
            {"min_miss_pc": r["min_miss_pc"], "t_myr": r["t_myr"], "aim_l": r["aim_l_deg"], "aim_b": r["aim_b_deg"]}, "")
    for k, v in out["min_vinf"].items():
        log("B", f"min_vinf_{k.split(' (')[0].replace(' ', '_')}", v, "")
    results.setdefault("B", {})["galpy"] = out
    return out


# ============================================================================
# C. SURVIVAL
# ============================================================================
CAPSULE = {
    "mass_kg": 206.0,                 # Genesis SRC class (205.6 kg)
    "frontal_area_m2": 1.81,          # 1.52 m diameter
    "front_tps_c_c_sic_mass_kg": 46.0,
    "bumper_al_li_thickness_cm": 0.7,
    "bumper_density_g_cc": 2.65,
    "standoff_cm": 30.0,
    "rear_wall_thickness_cm": 1.4,    # B4C/Ta graded wall; BLE applied as if Al 2219 (sigma=70 ksi)
    "rear_wall_density_g_cc": 6.5,
}
DUST = {
    "local_rho_kg_m3": 2.1e-24,       # Krueger et al. 2015 (Ulysses), +/-0.6e-24
    "local_gas_to_dust": 193.0,       # Krueger et al. 2015, +85/-57
    "gas_to_dust_avg": 100.0,         # canonical diffuse-ISM value (local in-situ values are 94-193)
    "grain_density_kg_m3": 3300.0,
    "dust_stream_speed_km_s": 26.0,   # interstellar dust flow speed relative to the Sun
    "N_H_per_EBV": 5.8e21,            # Bohlin, Savage & Drake 1978, cm^-2 mag^-1
    "A0620_EBV": 0.30,                # Cantrell et al. 2010, Table 4: E(B-V) = 0.30 +/- 0.02 toward A0620-00
    "A0620_distance_pc": 1060.0,
}
FLUX_LIMITS = [  # interstellar meteoroid fluxes at Earth
    {"label": "Musci et al. 2012 optical upper limit", "flux_km2_h": 2e-4, "m_min_kg": 2e-7, "kind": "upper"},
    {"label": "Froncisz, Brown & Weryk 2020 CMOR candidates", "flux_km2_h": 6.6e-7, "m_min_kg": 1.8e-7, "kind": "detection (5 candidates / 11M orbits)"},
    {"label": "Wiegert et al. 2025 optical 95% upper limit", "flux_km2_h": 8e-11, "m_min_kg": 6.6e-5, "kind": "upper"},
]
GCR = {
    "dose_rate_1au_cruise_Gy_yr": 0.167,   # MSL/RAD cruise, tissue-equivalent, ~16 g/cm2 (Guo et al. 2015)
    "lism_factor_range": (1.0, 2.0),       # GCR peak intensity outside heliopause is ~15x at 10-50 MeV/nuc;
                                           # high-energy (dose-dominant) part changes far less; range assumed
    "silica_visible_ok_MGy": 18.0,         # Yang et al. 2022: minimal attenuation at 360-400 nm up to 10-18 MGy
    "sapphire_ok_MGy": 100.0,              # Sporea & Sporea 2016: radiation hardened up to 1e8 Gy gamma
}


def grain_mass(r_m, rho=DUST["grain_density_kg_m3"]):
    return 4.0 / 3.0 * math.pi * r_m**3 * rho


def grain_radius(m_kg, rho=DUST["grain_density_kg_m3"]):
    return (3.0 * m_kg / (4.0 * math.pi * rho)) ** (1.0 / 3.0)


def whipple_ble_dc_cm(v_km_s: float, t_w_cm: float, rho_p: float, rho_b: float, S_cm: float,
                      sigma_ksi: float = 70.0, theta_deg: float = 0.0) -> float:
    """Christiansen 'new non-optimum' Whipple ballistic limit, hypervelocity regime (V_n > 7 km/s):
    d_c = 3.918 t_w^(2/3) rho_p^(-1/3) rho_b^(-1/9) (V cos theta)^(-2/3) S^(1/3) (sigma/70)^(1/3)
    [cm, g/cm^3, km/s, ksi]. Piekutowski et al. 2011 IJIE 38, 495, Eq. 3."""
    vn = v_km_s * math.cos(math.radians(theta_deg))
    return 3.918 * t_w_cm ** (2 / 3) * rho_p ** (-1 / 3) * rho_b ** (-1 / 9) * vn ** (-2 / 3) * S_cm ** (1 / 3) * (sigma_ksi / 70.0) ** (1 / 3)


def survival(path_length_pc: float, flight_myr: float, v_km_s: float, label: str, ebv: float | None = None, ebv_distance_pc: float | None = None):
    print(f"\nC. SURVIVAL — {label}: path {path_length_pc:.0f} pc, {flight_myr:.1f} Myr at {v_km_s:.0f} km/s")
    sec = f"C_{label}"
    A = CAPSULE["frontal_area_m2"]
    L = path_length_pc * PC

    # --- dust column ---------------------------------------------------------
    columns = {}
    columns["local_LIC"] = DUST["local_rho_kg_m3"] * L                          # kg/m^2, Ulysses in-situ density
    n_H_lic = DUST["local_rho_kg_m3"] * DUST["local_gas_to_dust"] / (1.4 * M_H) / 1e6
    log(sec, "implied_n_H_LIC", n_H_lic, "cm^-3", "from Ulysses dust density x gas-to-dust 193")
    if ebv is not None:
        # reddening along the line of sight -> hydrogen column -> mean density -> dust column over the path
        N_H = DUST["N_H_per_EBV"] * ebv * 1e4                                     # m^-2 over the target distance
        n_H = N_H / (ebv_distance_pc * PC)                                         # m^-3, sightline-averaged
        log(sec, "sightline_mean_n_H_from_reddening", n_H / 1e6, "cm^-3", f"E(B-V)={ebv}, N_H=5.8e21 E(B-V) cm^-2, over {ebv_distance_pc:.0f} pc")
        columns["sightline_reddening_gd100"] = n_H * 1.4 * M_H * L / DUST["gas_to_dust_avg"]
    for k, col in columns.items():
        swept = col * A
        ke = 0.5 * swept * (v_km_s * 1e3) ** 2
        eroded_100x = 100.0 * swept
        log(sec, f"swept_dust_mass_{k}", swept * 1e3, "g", "dust mass column x frontal area")
        log(sec, f"dust_kinetic_energy_{k}", ke / 1e3, "kJ", "whole-path total")
        log(sec, f"eroded_shield_fraction_{k}", eroded_100x / CAPSULE["front_tps_c_c_sic_mass_kg"], "",
            "crater mass = 100 x projectile mass, / 46 kg TPS")

    # --- micro-hit count from in-situ size range ---------------------------------
    for r in (1e-7, 1e-6):
        n = DUST["local_rho_kg_m3"] / grain_mass(r)
        log(sec, f"hits_if_all_local_dust_in_r{r*1e6:g}um", n * A * L, "", "monodisperse sanity bound")

    # --- large grains from meteor-survey fluxes -----------------------------------
    v_earth_entry = 26.0  # km/s: interstellar meteoroid speed relative to Sun; gravitational focusing at 1 AU ignored (conservative)
    for fl in FLUX_LIMITS:
        n_m3 = fl["flux_km2_h"] / (1e6 * 3600.0) / (v_earth_entry * 1e3)
        hits = n_m3 * A * L
        d_mm = 2 * grain_radius(fl["m_min_kg"]) * 1e3
        log(sec, f"expected_hits_m>{fl['m_min_kg']:.1e}kg_({d_mm:.1f}mm)", hits, "",
            f"{fl['label']} [{fl['kind']}], KE per hit at {v_km_s:.0f} km/s = {0.5*fl['m_min_kg']*(v_km_s*1e3)**2/1e3:.1f} kJ")
        log(sec, f"P_at_least_one_m>{fl['m_min_kg']:.1e}kg", 1 - math.exp(-hits), "")

    # --- Whipple ballistic limit at cruise speed ----------------------------------
    for rho_p in (3.3, 1.0):
        dc = whipple_ble_dc_cm(v_km_s, CAPSULE["rear_wall_thickness_cm"], rho_p, CAPSULE["bumper_density_g_cc"], CAPSULE["standoff_cm"])
        log(sec, f"whipple_critical_diameter_rho{rho_p}", dc * 10, "mm",
            f"NNO BLE at {v_km_s:.0f} km/s; validated only to ~10 km/s (equation conservative there)")
        log(sec, f"whipple_critical_mass_rho{rho_p}", grain_mass(dc / 2 * 1e-2, rho_p * 1e3), "kg")

    # --- cosmic rays ----------------------------------------------------------------
    for f in GCR["lism_factor_range"]:
        dose = GCR["dose_rate_1au_cruise_Gy_yr"] * f * flight_myr * 1e6 / 1e6
        log(sec, f"gcr_dose_lism_factor_{f:g}", dose, "MGy", "MSL/RAD cruise 0.167 Gy/yr x LISM factor x time")
    log(sec, "silica_visible_transmission_verified_to", GCR["silica_visible_ok_MGy"], "MGy", "Yang et al. 2022 (LHC irradiation)")
    log(sec, "sapphire_gamma_hardness_to", GCR["sapphire_ok_MGy"], "MGy", "Sporea & Sporea 2016")

    # --- interstellar gas -------------------------------------------------------------
    E_H = 0.5 * M_H * (v_km_s * 1e3) ** 2 / EV
    log(sec, "H_atom_impact_energy", E_H, "eV", "sputtering threshold for H on graphite 40-50 eV (Gray & Edmunds 2004)")
    swept_gas = columns["local_LIC"] * DUST["local_gas_to_dust"] * A
    log(sec, "swept_gas_mass", swept_gas * 1e3, "g")
    log(sec, "drag_delta_v", swept_gas / CAPSULE["mass_kg"] * v_km_s, "km/s", "momentum-transfer bound, along track")
    return sec


# ============================================================================
# D. CAPTURE PROBABILITY
# ============================================================================
def b_capture(M_kg: float, vinf_m_s: float) -> float:
    """Critical impact parameter for capture of a slow (v<<c) particle by a Schwarzschild black hole:
    b = 4GM/(c v_inf)  (sigma = 16 pi G^2 M^2 / (c^2 v_inf^2))."""
    return 4.0 * G * M_kg / (C * vinf_m_s)


def astrometric_dispersion(t: Target, flight_myr: float, err_scale: float = 1.0, n=20000, seed=1):
    """Monte Carlo: propagate the target's catalogued 6D uncertainties for the flight time and
    measure the transverse scatter of its position relative to the nominal aim point.
    Straight-line propagation in the heliocentric frame (adequate for the *dispersion*)."""
    rng = np.random.default_rng(seed)
    T = flight_myr * MYR
    d = rng.normal(t.distance_pc, t.distance_err_pc * err_scale, n) * PC
    pmra = rng.normal(t.pmra_mas_yr, t.pmra_err * err_scale, n)
    pmdec = rng.normal(t.pmdec_mas_yr, t.pmdec_err * err_scale, n)
    rv = rng.normal(t.rv_km_s, t.rv_err * err_scale, n) * 1e3
    # local frame: x along the line of sight, y along pmra, z along pmdec
    vy = MAS_YR_PC_TO_KM_S * pmra / 1e3 * (d / PC) * 1e3
    vz = MAS_YR_PC_TO_KM_S * pmdec / 1e3 * (d / PC) * 1e3
    pos = np.vstack([d + rv * T, vy * T, vz * T]).T
    nominal = pos.mean(axis=0)
    # the capsule flies straight at the nominal point; miss = component of the offset perpendicular
    # to the capsule's velocity direction (nominal aim direction)
    u = nominal / np.linalg.norm(nominal)
    off = pos - nominal
    para = off @ u
    perp = off - np.outer(para, u)
    sig = perp.std(axis=0)
    # two principal transverse axes
    cov = np.cov(perp.T)
    eig = np.sqrt(np.maximum(np.linalg.eigvalsh(cov), 0))
    eig = np.sort(eig)[::-1][:2]
    return {"sigma_transverse_axes_au": (eig / AU).tolist(), "along_track_sigma_au": float(para.std() / AU)}


def encounter_dispersion(flight_myr: float, n_runs=2000, seed=2, n_star=0.0895, rate_1pc_per_myr=19.7,
                         b_max_pc=2.0, sigma_v=40.0):
    """Monte Carlo of impulsive kicks from passing field stars (impulse approximation
    dv = 2 G M / (b v_rel)), for both the capsule and the target; returns the per-axis
    scatter of their relative transverse displacement at arrival. Encounter rate is
    normalised to the Gaia-based 19.7 encounters within 1 pc per Myr (Bailer-Jones et al. 2018)."""
    rng = np.random.default_rng(seed)
    T = flight_myr
    rate = rate_1pc_per_myr * b_max_pc**2          # encounters within b_max per Myr
    disp = np.zeros((n_runs, 2))
    for body in range(2):                          # capsule and target independently
        for i in range(n_runs):
            N = rng.poisson(rate * T)
            if N == 0:
                continue
            b = b_max_pc * np.sqrt(rng.random(N)) * PC
            b = np.maximum(b, 50 * AU)             # avoid singular kicks (a direct hit is a different event)
            tk = rng.random(N) * T
            v = np.sqrt(rng.normal(0, sigma_v, (N, 3)) ** 2 @ np.ones(3)) * 1e3 + 5e3  # relative speed, m/s
            M = rng.lognormal(math.log(0.35), 0.8, N) * M_SUN                       # crude field-star mass function
            dv = 2 * G * M / (b * v)
            ang = rng.random(N) * 2 * math.pi
            lever = (T - tk) * MYR
            disp[i, 0] += np.sum(dv * np.cos(ang) * lever)
            disp[i, 1] += np.sum(dv * np.sin(ang) * lever)
    sig = disp.std(axis=0) / AU
    return {"sigma_per_axis_au": float(np.sqrt(sig[0] * sig[1])), "rms_kick_note": "impulse approx, b_max=2 pc"}


def p_within(radius_m: float, sig_x_m: float, sig_y_m: float) -> float:
    """P(|miss| < R) for a 2-D Gaussian miss distribution (exact for sig_x = sig_y; product form otherwise).
    -expm1 keeps the tiny-probability limit R^2/(2 sx sy) exact instead of underflowing to 0."""
    x = radius_m**2 / (2.0 * sig_x_m * sig_y_m)
    return -math.expm1(-x)


def section_D(target: Target, flight_myr: float, vinf_km_s: float, label: str):
    print(f"\nD. CAPTURE — {label}: {target.name}, flight {flight_myr:.0f} Myr at {vinf_km_s:.0f} km/s")
    sec = f"D_{label}"
    M = target.bh_mass_msun * M_SUN
    # relative speed at encounter ~ heliocentric capsule speed minus target motion; use |v_cap - v_bh| straight-line estimate
    v_rel = math.sqrt((vinf_km_s) ** 2 + target.v_tan**2 + (target.v_rad or 0) ** 2 - 2 * vinf_km_s * (target.v_rad or 0)) * 1e3
    b = b_capture(M, v_rel)
    log(sec, "encounter_relative_speed", v_rel / 1e3, "km/s", "straight-line estimate")
    log(sec, "capture_impact_parameter_b", b / 1e3, "km", "b = 4GM/(c v)")
    log(sec, "capture_impact_parameter_b_au", b / AU, "AU")
    log(sec, "schwarzschild_radius", 2 * G * M / C**2 / 1e3, "km")

    enc = encounter_dispersion(flight_myr)
    log(sec, "encounter_dispersion_per_axis", enc["sigma_per_axis_au"], "AU", "stellar-encounter kicks, physics floor")

    scenarios = {}
    for lab, scale in (("today_catalog_errors", 1.0), ("errors_x0.1_future_astrometry", 0.1), ("errors_x0.01", 0.01)):
        ad = astrometric_dispersion(target, flight_myr, err_scale=scale)
        sx, sy = ad["sigma_transverse_axes_au"]
        sx = math.sqrt(sx**2 + enc["sigma_per_axis_au"] ** 2)
        sy = math.sqrt(sy**2 + enc["sigma_per_axis_au"] ** 2)
        pc_ = p_within(b, sx * AU, sy * AU)
        p100 = p_within(100 * AU, sx * AU, sy * AU)
        p1000 = p_within(1000 * AU, sx * AU, sy * AU)
        scenarios[lab] = {"sigma_axes_au": [sx, sy], "P_capture": pc_, "P_within_100au": p100, "P_within_1000au": p1000}
        log(sec, f"{lab}_sigma_axes", [round(sx, 1), round(sy, 1)], "AU")
        log(sec, f"{lab}_P_capture", pc_, "")
        log(sec, f"{lab}_P_within_1000au", p1000, "")
    # physics floor: encounters only
    s = enc["sigma_per_axis_au"] * AU
    log(sec, "floor_encounters_only_P_capture", p_within(b, s, s), "", "perfect astrometry, only stellar-encounter noise")
    log(sec, "floor_encounters_only_P_within_1000au", p_within(1000 * AU, s, s), "")
    # correction leverage
    for dv in (0.1, 1.0):
        log(sec, f"lateral_reach_of_{dv:g}m_s_correction_at_launch", dv * flight_myr * MYR / AU, "AU",
            "what an early-window burn can move the arrival point by")
    results[sec]["scenarios"] = scenarios
    return sec


def section_D_population():
    print("\nD2. TARGET-INDEPENDENT: capture by *any* black hole while drifting through the disk")
    sec = "D_population"
    v_rel = 40e3
    for n_bh_pc3, note in ((1e-4, "stellar density 0.09/pc^3 x N_BH/N_star = 1.2e8/1e11"), (5e-4, "Fender et al. 2013: 1e8 BH over 200 kpc^3")):
        M = 14 * M_SUN                       # mean single-BH mass, Olejak et al. 2020
        sig = math.pi * b_capture(M, v_rel) ** 2
        rate = n_bh_pc3 / PC**3 * sig * v_rel * MYR   # per Myr
        log(sec, f"capture_rate_per_Myr_n{n_bh_pc3:g}", rate, "1/Myr", note)
        for T in (10, 100, 1000):
            log(sec, f"expected_captures_{T}Myr_n{n_bh_pc3:g}", rate * T, "")
    # comparison: falling into a random star (gravitational focusing included)
    n_star = 0.0895 / PC**3
    sig_star = math.pi * R_SUN**2 * (1 + (2 * G * M_SUN / R_SUN) / v_rel**2)
    rate_star = n_star * sig_star * v_rel * MYR
    log(sec, "star_collision_rate_per_Myr", rate_star, "1/Myr", "Sun-like stars, focusing included")
    log(sec, "star_vs_black_hole_ratio", rate_star / (1e-4 / PC**3 * math.pi * b_capture(14 * M_SUN, v_rel) ** 2 * v_rel * MYR), "")
    # lifetime cap from the large-grain population (CMOR candidate flux, unshielded case)
    fl = FLUX_LIMITS[1]
    n_m3 = fl["flux_km2_h"] / (1e6 * 3600.0) / (26e3)
    hits_per_Myr = n_m3 * CAPSULE["frontal_area_m2"] * (34e3 * MYR)
    log(sec, "sub_mm_hits_per_Myr_at_34kms", hits_per_Myr, "1/Myr", "CMOR candidate flux; these are within the Whipple limit")


# ============================================================================
def main():
    figures = "--figures" in sys.argv
    section_A()
    targets = load_targets()
    section_B_straight(targets)
    a0620 = next(t for t in targets if t.name.startswith("A0620"))
    gal = section_B_galpy(targets)

    # survival for (i) the generic 480 pc / 10 Myr crossing and (ii) the A0620-00 intercept
    survival(480.0, 13.8, 34.0, "480pc_10Myr_generic")
    row34 = gal["A0620_earliest"]["v34"]
    row45 = gal["A0620_earliest"]["v45"]
    for row, lab in ((row34, "A0620_34kms"), (row45, "A0620_45kms")):
        if row["min_miss_pc"] < 1.0:
            path_pc = row["vinf_km_s"] * row["t_myr"] / KM_S_PER_PC_MYR
            survival(path_pc, row["t_myr"], row["vinf_km_s"], lab, ebv=DUST["A0620_EBV"], ebv_distance_pc=DUST["A0620_distance_pc"])
            section_D(a0620, row["t_myr"], row["vinf_km_s"], lab)
    section_D_population()

    json.dump(results, open("results.json", "w"), indent=1, default=float)
    print("\nwrote results.json")
    if figures:
        make_figures(targets, gal)


def make_figures(targets, gal):
    import os
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs("figures", exist_ok=True)
    # 1. straight-line reachability: transverse speed vs distance, with launch-speed lines
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for t in targets:
        ax.scatter(t.distance_pc, t.v_tan, s=30, color="#1f4e79" if t.rv_km_s is not None else "#999")
        ax.annotate(t.name.split(" (")[0], (t.distance_pc, t.v_tan), textcoords="offset points", xytext=(4, 3), fontsize=7)
    for v, ls in ((34, "-"), (45, "--")):
        ax.axhline(v, color="#b24d2d", ls=ls, lw=1)
        ax.text(3300, v + 3, f"launch speed {v} km/s", color="#b24d2d", fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("distance (pc)")
    ax.set_ylabel("transverse speed relative to the Sun (km/s)")
    ax.set_title("Straight-line test: a target moving sideways faster than the capsule cannot be caught")
    ax.set_ylim(0, 170)
    fig.tight_layout()
    fig.savefig("figures/reachability.png", dpi=160)
    # 2. flight time to intercept A0620-00 vs launch speed (Galactic potential, t <= 300 Myr window)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for lab, rows in gal["A0620_scan"].items():
        ax.plot([r["vinf_km_s"] for r in rows], [r["t_myr"] for r in rows], marker="o",
                label=lab.replace("_", " "))
    e34, e45 = gal["A0620_earliest"]["v34"], gal["A0620_earliest"]["v45"]
    ax.scatter([e34["vinf_km_s"], e45["vinf_km_s"]], [e34["t_myr"], e45["t_myr"]], marker="*", s=160, color="#b24d2d", zorder=5,
               label="earliest intercept (1060 pc)")
    ax.set_xlabel("launch speed v∞ (km/s)")
    ax.set_ylabel("flight time of the intercept solution (Myr)")
    ax.set_title("A0620-00 intercept solutions in MWPotential2014 (every point is an intercept)")
    ax.set_ylim(0, 320)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig("figures/a0620_intercept.png", dpi=160)
    print("wrote figures/")


if __name__ == "__main__":
    main()
