# Capsule Environment Data Brief v1

Purpose: primary-source input brief for the Capsule Design & Deep-Time Survivability Layer. Scope is limited to durable environment and trajectory exposure anchors: interstellar gas/plasma, interstellar dust, dust size distributions, GCR/radiation references, spacecraft hypervelocity impact constraints, target distance/time-of-flight anchors, and Sun-Oberth velocity ranges compatible with the current repository framing.

This is not a new physics model. It is a source-backed triage layer for deciding which numbers are stable enough to encode and which must remain explicit assumptions or sensitivity parameters.

## Repository framing to preserve

Current local framing:

| Repo surface | Current value or range | Interpretation for this brief |
| --- | ---: | --- |
| `paper/whitepaper.md` Sun-Oberth range | near-parabolic `v_infinity = 23-34 km/s`; conditional `35-45 km/s` | Keep compatible; source-check with two-body energy closure and external Oberth mission literature. |
| `paper/whitepaper.md` perihelion | `0.05-0.10 AU`; SRM impulse `2-3 km/s` | Use as the compatible Sun-Oberth design band. |
| `paper/whitepaper.md` high-relative-speed extrapolation | up to `~60 km/s` conditional dust/relative-speed scenario | Keep as extrapolation risk, not validated test capability. |
| `mission/BASELINE_SCENARIO_v1.json` target distance | `26000 ly` | Compatible with a rounded Galactic-center scale, but not a precision measurement. |
| `mission/BASELINE_SCENARIO_v1.json` dust scale | `dust_flux_scale = 1.4`; uncertainty min/mode/max `0.8/1.4/2.4`; bound `[0.5, 3.0]` | Retain as dimensionless scenario stress, not as a measured flux. |
| `mission/BASELINE_SCENARIO_v1.json` plasma proxy | `5.0e10 m^-3` baseline; `8.0e10 m^-3` max acceptance | This is a black-hole/proxy environment value. Do not map local interstellar gas density directly onto it. |
| `engineering/DECISIONS.md` D-0020 | capsule heritage values and survivability priors are distinct evidence classes | Preserve this boundary. Environment data can inform priors, but does not certify capsule survival. |

## Summary recommendations

| Topic | Recommended treatment | Stable enough to encode? |
| --- | --- | --- |
| SI/astronomical constants | Use repo constants for `c`, `AU`, Julian year, solar GM, solar constant. | Yes. |
| Local interstellar neutral H density | Use `0.127 +- 0.015 cm^-3` as a local heliosphere/VLISM anchor, equivalent to `1.27e5 +- 1.5e4 m^-3`. | Yes as local-cruise reference only. |
| Interstellar plasma/electron density | Use Voyager plasma-wave order-of-magnitude anchor `~0.08 cm^-3` (`~8e4 m^-3`) near/just beyond the heliopause. | Yes as local-cruise reference only. |
| Interstellar dust mass density | Use Ulysses 16-year result `(2.1 +- 0.6)e-24 kg/m^3` as the best local in-situ dust mass-density anchor. | Yes as a local prior with factor-level uncertainty. |
| Dust size distribution | Use MRN/extinction distribution and Ulysses in-situ large-grain evidence as separate regimes. | Encode regimes, not a single universal curve. |
| Millimeter/centimeter impact tail | Treat as sensitivity tail. No strong primary source supports an exact deep-time interstellar mm/cm flux. | No. Keep assumption-bound. |
| GCR radiation | Use NASA BON2020 / NASA-STD-3001 and RAD measurements as reference environments. | Encode model/source hooks; avoid fixed Myr scalar dose. |
| Hypervelocity test validation | NASA HVIT validates roughly `<2` to `>7 km/s` lab impacts for specific projectile sizes; tens-of-km/s capsule claims are extrapolation/modeling. | Encode as validation limit. |
| Natural meteoroid impact speeds | ESA notes meteoroids can reach `72 km/s`; NASA MEM is for inner solar system meteoroid risk, not interstellar cruise. | Encode as solar-system design context only. |
| Sun-Oberth speed band | Current repo `23-34 km/s` baseline and `35-45 km/s` conditional band are consistent with two-body energy closure. | Yes as architecture framing, with conditional tags. |
| Target time of flight | Encode calculated TOF tables from distance and velocity; treat target distance as scenario-owned. | Yes if source and scenario labels are kept. |

## Interstellar gas and plasma anchors

| Quantity | Source-backed value | Converted value | Source | Trust note | Encode guidance |
| --- | ---: | ---: | --- | --- | --- |
| Local interstellar neutral hydrogen density at the termination shock | `0.127 +- 0.015 cm^-3` | `1.27e5 +- 1.5e4 m^-3`; H-only mass density `~2.13e-22 kg/m^3` | Swaczyna et al., "Density of Neutral Hydrogen in the Sun's Interstellar Neighborhood", ApJ 2020, DOI `10.3847/1538-4357/abb80a`; NASA summary: https://www.nasa.gov/solar-system/new-evidence-our-neighborhood-in-space-is-stuffed-with-hydrogen/ | Strong local heliosphere/VLISM anchor from New Horizons/SWAP pickup-ion analysis; still model-dependent and direction/epoch-specific. | Stable local-cruise prior. Do not reuse as dense target-region plasma. |
| Voyager 1 interstellar plasma/electron density from plasma oscillations | `~0.08 cm^-3` | `~8.0e4 m^-3` | Gurnett et al., "In situ observations of interstellar plasma with Voyager 1", Science 2013: https://pubmed.ncbi.nlm.nih.gov/24030496/ | Strong in-situ plasma-wave measurement near/just beyond heliopause. Measures plasma/electrons, not neutral gas. | Stable order-of-magnitude local plasma anchor. |
| Repo plasma-density proxy | `5.0e10 m^-3` baseline; `8.0e10 m^-3` max acceptance | `5.0e4 cm^-3` baseline; `8.0e4 cm^-3` max | `mission/BASELINE_SCENARIO_v1.json` | This is many orders above local VLISM density and should be treated as a target-environment/accretion proxy, not cruise gas. | Keep as scenario/proxy parameter until a target-region model is added. |

Notes:

- Local interstellar gas density is sparse enough that gas drag should remain a secondary cruise perturbation for the repository's `23-45 km/s` speed band, but it is still useful as a floor for long-horizon perturbation accounting.
- The local values above are not valid as universal averages across a `1560 ly` or `26000 ly` trajectory. Crossing clouds, bubbles, denser regions, or target-environment plasma invalidates a single-density assumption.

## Interstellar dust density and flux anchors

| Quantity | Source-backed value | Source | Trust note | Encode guidance |
| --- | ---: | --- | --- | --- |
| Ulysses/Galileo interstellar dust flux, early in-situ result | Mean grain mass `3e-13 g` (`3e-16 kg`); flux about `1e-4 m^-2 s^-1 (pi sr)^-1` | Baguhl et al., "The flux of interstellar dust observed by Ulysses and Galileo", Space Science Reviews 1995, DOI `10.1007/BF00768822`: https://link.springer.com/article/10.1007/BF00768822 | Strong direct spacecraft detection, but reported in instrument/directional terms and inside heliosphere. | Use as a source anchor for local ISD flux, not as a universal mission hit rate. |
| Ulysses 16-year local interstellar dust mass density | `(2.1 +- 0.6)e-24 kg/m^3` | Krueger, Strub, Grun, Sterken, "16 Years of Ulysses Interstellar Dust Measurements in the Solar System: I", ApJ 2015, DOI `10.1088/0004-637X/812/2/139`; arXiv: https://arxiv.org/abs/1510.06180 | Best compact local in-situ mass-density anchor found for the brief. Authors note sensitivity to inflow speed and heliospheric filtering. | Stable as a local prior with factor-level uncertainty. |
| Ulysses 16-year gas-to-dust mass ratio | `193 +85/-57` | Same Krueger et al. 2015 source | Useful consistency check against gas density, but depends on adopted gas values and inflow speed. | Encode as source-backed context, not as a hard design constraint. |
| Ulysses large-grain evidence | "Big" local ISD grains near `~1 micron`; earlier analyses up to `1e-13 kg`; grains above `1e-16 kg` contribute significantly to mass | Same Krueger et al. 2015 source | Directly relevant to impact energy because mass is tail-dominated. It does not provide a robust mm/cm flux. | Encode micron-class tail awareness; keep larger-particle tails as assumptions. |

Monodisperse sanity conversions from the Ulysses mass density `(2.1e-24 kg/m^3)`, assuming compact grains with material density `3300 kg/m^3`:

| Assumed grain radius | Mass per grain | Equivalent number density if all dust mass had this size | Why this is only a sanity check |
| ---: | ---: | ---: | --- |
| `0.1 micron` | `1.38e-17 kg` | `1.5e-7 m^-3` (`~152 km^-3`) | Real distribution is not monodisperse. |
| `0.25 micron` | `2.16e-16 kg` | `9.7e-9 m^-3` (`~9.7 km^-3`) | Large grains dominate mass faster than number. |
| `1.0 micron` | `1.38e-14 kg` | `1.5e-10 m^-3` (`~0.15 km^-3`) | Useful for impact-energy intuition, not flux prediction. |

## Dust size distribution anchors

| Distribution/source | Source-backed value | What it supports | What it does not support | Encode guidance |
| --- | --- | --- | --- | --- |
| MRN diffuse-ISM extinction distribution | Rough power law exponent `-3.3` to `-3.6`; canonical usage often `n(a) da proportional to a^-3.5 da`; graphite extends from about `0.005 micron` upward, other materials have narrower ranges around `0.025-0.25 micron` | Baseline diffuse interstellar extinction-sized grains | A spacecraft impact tail beyond micron scale | Encode as an extinction-size reference curve only. Source: Mathis, Rumpl, Nordsieck 1977, DOI `10.1086/155591`: https://adsabs.harvard.edu/pdf/1977ApJ...217..425M |
| Ulysses in-situ distribution | Direct detection of micron-class and larger-than-extinction grains in the local flow | Local impact-relevant grains that extinction-only MRN underweights | Universal large-particle abundance over Myr paths | Encode as direct local large-grain evidence with uncertainty. Source: Krueger et al. 2015. |
| ESA interstellar dust module context | ESA meteoroid model spans `1e-18` to `1e0 g`; Ulysses shows `1e-15` to `1e-12 g` impacts can dominate the outer-solar-system meteoroid flux in that mass interval | Spacecraft-surface impact modeling context | Deep interstellar mm/cm flux | Keep as model-context source. ESA proceedings: https://conference.sdo.esoc.esa.int/proceedings/sdc3/paper/105 |

Bottom line: do not collapse MRN plus Ulysses into a single "the dust distribution" constant. The survivability layer should carry at least two knobs: an extinction-sized grain population and an impact-tail population.

## Hypervelocity and dust-impact constraints

| Constraint | Source-backed value | Source | Trust note | Encode guidance |
| --- | ---: | --- | --- | --- |
| NASA HVIT lab impact capability | `100 micron` to `10 mm` aluminum balls; velocities from below `2 km/s` to over `7 km/s` | NASA JSC HVIT: https://hvit.jsc.nasa.gov/hypervelocity-testing/ | Strong facility capability statement. It is a validation band, not the mission environment. | Encode as ground-test validation ceiling for direct tests. |
| ESA spacecraft impact environment | Debris speeds can reach `15 km/s`; meteoroids can reach `72 km/s`; micrometer impactors pit, millimeter impactors can perforate, `>1 cm` can be mission-critical, `10 cm` catastrophic | ESA Space Safety: https://www.esa.int/Space_Safety/Space_Debris/Hypervelocity_impacts_and_protecting_spacecraft | Strong engineering context for spacecraft shielding. Mostly near-Earth/solar-system MMOD framing. | Encode as spacecraft-design context, not interstellar flux. |
| NASA MEM 3 threat model | MEM 3 reports flux by mass, speed, direction, and density for spacecraft risk; minimum recommended meteoroid mass is `1e-6 g`; near-Earth impact-rate uncertainty estimated at factor `2-3` | NASA MEM guide: https://fireballs.ndc.nasa.gov/mem/guide/ and NTRS MEM 3: https://ntrs.nasa.gov/citations/20200000563 | Strong NASA engineering model, but inner-solar-system focused and not a deep-interstellar dust model. | Use for solar-system/launch-cruise comparison only. |

Specific kinetic energy for relevant impact speeds:

| Relative speed | Specific kinetic energy | Notes |
| ---: | ---: | --- |
| `7 km/s` | `24.5 MJ/kg` (`24.5 kJ/g`) | NASA HVIT lab-capable order. |
| `14 km/s` | `98 MJ/kg` (`98 kJ/g`) | Typical debris context order. |
| `23 km/s` | `264.5 MJ/kg` (`264.5 kJ/g`) | Lower repo Sun-Oberth baseline asymptotic speed. |
| `34 km/s` | `578 MJ/kg` (`578 kJ/g`) | Upper near-parabolic repo baseline. |
| `45 km/s` | `1012.5 MJ/kg` (`1012.5 kJ/g`) | Conditional repo high-speed architecture. |
| `60 km/s` | `1800 MJ/kg` (`1800 kJ/g`) | Repo conditional high-relative-speed extrapolation. |
| `72 km/s` | `2592 MJ/kg` (`2592 kJ/g`) | ESA natural meteoroid upper context. |

Design implication: if the layer claims direct validation at tens of km/s, it will overstate the evidence. The defensible statement is "validated in representative lower-speed hypervelocity regimes, then extrapolated by hydrocode/ballistic-limit models with explicit uncertainty."

## Cosmic radiation and GCR references

| Quantity/model | Source-backed value | Source | Trust note | Encode guidance |
| --- | ---: | --- | --- | --- |
| NASA GCR design reference | NASA-STD-3001 cites 2009 solar-minimum Badhwar-O'Neill 2020 GCR spectrum for verification; unshielded free-space GCR effective dose rate `1.5 mSv/day`; protected free-space requirement `<1.3 mSv/day`; planetary-surface requirement `<0.9 mSv/day` | NASA-STD-3001, section 4.8.5: https://www.nasa.gov/reference/4-0-human-performance/ | Strong NASA human-spaceflight standard. Effective dose is human-health oriented, not direct electronics/material damage. | Encode as GCR reference environment, not as capsule TID. |
| Shielding density-thickness context | NASA-STD-3001 notes reductions can be achieved with `10-40 g/cm^2`; `40-100 g/cm^2` can be negligible or negative for exposure rate due secondary effects | Same NASA-STD-3001 source | Strong for crew-effective-dose context; material and geometry dependent. | Encode as caution against "more areal density always helps" for GCR. |
| Mars surface RAD absorbed-dose measurement | About `210 microgray/day`, almost entirely due to GCR during first 10 months on Mars | NASA RAD resource: https://science.nasa.gov/resource/radiation-measurements-on-mars/ | Strong measured surface environment, with atmospheric shielding and Martian local context. | Use as measured reference point only, not free-space dose. |
| Stopping powers/ranges for particles in materials | ESTAR/PSTAR/ASTAR provide electron, proton, and alpha stopping powers and ranges | NIST: https://www.nist.gov/pml/stopping-power-range-tables-electrons-protons-and-helium-ions | Strong reference data for material-specific radiation transport inputs. Does not solve heavy-ion GCR transport by itself. | Encode as required reference tool for material-specific calculations. |
| NASA OLTARIS / BON model family | OLTARIS exposes free-space GCR models including Badhwar-O'Neill 2010, 2014, and 2020 | NASA Space Radiation Group: https://spaceradiation.larc.nasa.gov/oltaris.html | Strong NASA model tooling; results depend on date/solar modulation, shielding, and geometry. | Store model/version, not a single static GCR scalar. |

Radiation modeling boundary:

- Do not map GCR dose directly into `environment_model.radiative_flux_w_m2`. The repo parameter reads as radiative/thermal or target-environment flux, while GCR is an ionizing-particle transport problem.
- For capsule media integrity, encode GCR as a reference model choice plus material/shield stack inputs. The current `capsule_model.data_media_survival_margin` and `capsule_model.material_degradation_mu_1_per_year` should remain assumption-bound until tied to material-specific TID, displacement damage, and single-event-effect evidence.

## Target distance and time-of-flight anchors

Primary distance anchors:

| Anchor | Source-backed value | Source | Encode guidance |
| --- | ---: | --- | --- |
| Alpha Centauri system | `4.3 ly` approximate NASA/ESA Hubble value | NASA/ESA Hubble: https://science.nasa.gov/missions/hubble/hubbles-best-image-of-alpha-centauri-a-and-b/ | Stable nearby-star scaling anchor. Use approximate only unless Gaia/astrometric precision is needed. |
| Galactic Center / Sgr A* distance | `R0 = 8178 +- 13(stat) +- 22(sys) pc` = about `26670 ly` | GRAVITY Collaboration 2019, A&A 625 L10, DOI `10.1051/0004-6361/201935656`; arXiv: https://arxiv.org/abs/1904.05721 | Stable precision anchor. Repo `26000 ly` is a rounded scenario value, not precision astronomy. |
| Repo reference compact-object distance | `1560 ly` | `paper/whitepaper.md` project framing | Scenario reference. Keep as project-owned, not external measurement. |
| Repo baseline black-hole distance | `26000 ly` | `mission/BASELINE_SCENARIO_v1.json` | Scenario value compatible with Galactic-center order of magnitude. Label rounded. |

Calculated ballistic time of flight, ignoring acceleration phase and perturbations:

| Distance | `23 km/s` | `34 km/s` | `45 km/s` | `60 km/s` | `95 km/s` |
| ---: | ---: | ---: | ---: | ---: | ---: |
| `4.2465 ly` Proxima-scale | `55,351 yr` | `37,443 yr` | `28,290 yr` | `21,218 yr` | `13,401 yr` |
| `4.37 ly` Alpha-Centauri-system scale | `56,961 yr` | `38,532 yr` | `29,113 yr` | `21,835 yr` | `13,790 yr` |
| `1560 ly` repo reference | `20.33 Myr` | `13.76 Myr` | `10.39 Myr` | `7.79 Myr` | `4.92 Myr` |
| `26000 ly` repo baseline | `338.90 Myr` | `229.25 Myr` | `173.21 Myr` | `129.91 Myr` | `82.05 Myr` |
| `26670 ly` Galactic-center precision anchor | `347.63 Myr` | `235.16 Myr` | `177.68 Myr` | `133.26 Myr` | `84.16 Myr` |

Context: Voyager 1 is a legacy escape-speed anchor at about `3.5 AU/yr` and `17.0 km/s` relative to the Sun as reported by NASA, while the repository Sun-Oberth band is faster but still far below relativistic interstellar-probe concepts. NASA Voyager source: https://science.nasa.gov/mission/voyager/voyager-1/

## Sun-Oberth velocity ranges compatible with repo framing

The current repo claims are consistent with two-body Sun-Oberth energy closure using:

- Solar GM `1.32712440018e20 m^3/s^2`
- `1 AU = 149597870700 m`
- near-parabolic inbound `v_infinity,in = 0`
- perihelion `q = 0.05-0.10 AU`
- impulsive perihelion burn `delta-v = 2-3 km/s`

Derived values:

| Case | Perihelion speed before burn | Burn | Outgoing `v_infinity` | Fraction of `c` |
| --- | ---: | ---: | ---: | ---: |
| `q = 0.10 AU`, near-parabolic | `133.20 km/s` | `2 km/s` | `23.17 km/s` | `7.73e-5 c` |
| `q = 0.10 AU`, near-parabolic | `133.20 km/s` | `3 km/s` | `28.43 km/s` | `9.48e-5 c` |
| `q = 0.05 AU`, near-parabolic | `188.37 km/s` | `2 km/s` | `27.52 km/s` | `9.18e-5 c` |
| `q = 0.05 AU`, near-parabolic | `188.37 km/s` | `3 km/s` | `33.75 km/s` | `1.13e-4 c` |

Conditional inbound-energy cases using `q = 0.05 AU` and `delta-v = 3 km/s`:

| Inbound `v_infinity,in` | Outgoing `v_infinity` | Fraction of `c` |
| ---: | ---: | ---: |
| `10 km/s` | `35.23 km/s` | `1.17e-4 c` |
| `20 km/s` | `39.31 km/s` | `1.31e-4 c` |
| `30 km/s` | `45.32 km/s` | `1.51e-4 c` |

External Sun-Oberth references:

| Source | Relevant durable number | Trust note |
| --- | ---: | --- |
| NASA NIAC Phase I "Combined Heat Shield and Solar Thermal Propulsion System for an Oberth Maneuver" | Desired interstellar-probe speeds `>10 AU/yr`; Voyager `3.6 AU/yr`; SLS + Jupiter gravity assist `7-8 AU/yr` for about `1 tonne`; solar thermal Oberth study claims `>10 AU/yr` and up to `~13 AU/yr` for specific concept assumptions | Useful architecture context, but higher-speed solar-thermal results are concept-study values and should not be imported into the repo baseline. Source: https://ntrs.nasa.gov/api/citations/20250001946/downloads/NIAC_2022_PhI_Benkoski_Oberth.pdf |
| NASA Parker Solar Probe public mission context | Record final-orbit speed `430000 mph` (`~192 km/s`) and close solar operation around `3.83 million miles` from visible surface | Thermal/solar-proximity precedent only; Parker is not an Oberth escape architecture. Source: https://www.nasa.gov/solar-system/its-surprisingly-hard-to-go-to-the-sun/ |

Perihelion solar flux from the repo solar constant `1361 W/m^2`:

| Perihelion | Solar irradiance |
| ---: | ---: |
| `0.10 AU` | `0.1361 MW/m^2` |
| `0.05 AU` | `0.5444 MW/m^2` |

Encode guidance:

- The `23-34 km/s` near-parabolic Sun-Oberth range is stable enough to encode as the baseline repository architecture band.
- The `35-45 km/s` band is stable enough to encode only with a conditional inbound-energy tag.
- The `~60 km/s` relative dust-speed/conditional regime should remain an extrapolation stress case, not a validated flight speed.
- Anything above `~10 AU/yr` from solar-thermal Oberth concepts belongs in a future architecture mode, not the current capsule survivability baseline.

## Values that should remain assumptions

These should not be promoted to hard constants without new primary evidence:

| Value/family | Why not encode as fact yet | What evidence would upgrade it |
| --- | --- | --- |
| Exact mm/cm interstellar dust flux over `Myr` horizons | Primary sources found here support local micron-class ISD and solar-system meteoroid models, not a robust deep-interstellar mm/cm distribution. | Mission-specific dust-tail model calibrated to in-situ, radar meteor, astronomical, and uncertainty-tail evidence. |
| Capsule shield areal density effectiveness | Existing repo value is a sizing prior. Public ballistic-limit data for the exact stack was not established in this brief. | Stack-level ballistic limit tests plus hydrocode validation across angle, material, and velocity regimes. |
| Direct GCR-to-media survival fraction | GCR references are model/dose environments, not direct media persistence measurements over Myr. | Material-specific radiation transport, TID/SEE/displacement-damage tests, and archive-media degradation evidence. |
| Local ISM density as whole-path average | The Sun's local cloud is not a representative average for arbitrary 1560 ly or Galactic-center trajectories. | Line-of-sight ISM model and uncertainty bins by target direction. |
| Black-hole/accretion plasma proxy values | Current `plasma_density_proxy_m3` is scenario-owned and far above local VLISM. | Target-region environmental model linked to accretion state, distance, and uncertainty propagation. |

## Minimal data schema candidates

If this brief is converted into machine-readable inputs, prefer a small source-backed schema rather than stuffing values into existing scenario knobs:

```json
{
  "interstellar_local_gas": {
    "neutral_h_cm3": {"value": 0.127, "sigma": 0.015, "source": "Swaczyna_2020_ApJ"},
    "electron_density_cm3_order": {"value": 0.08, "source": "Gurnett_2013_Science"},
    "applicability": "local heliosphere / VLISM only"
  },
  "interstellar_local_dust": {
    "mass_density_kg_m3": {"value": 2.1e-24, "sigma": 0.6e-24, "source": "Krueger_2015_ApJ"},
    "gas_to_dust_ratio": {"value": 193, "minus": 57, "plus": 85, "source": "Krueger_2015_ApJ"},
    "impact_tail": "assumption-bound sensitivity"
  },
  "hypervelocity_validation": {
    "direct_lab_velocity_km_s": {"min": 2, "max": 7, "source": "NASA_JSC_HVIT"},
    "tens_km_s_regime": "model extrapolation"
  },
  "gcr_reference": {
    "model": "Badhwar-O'Neill 2020",
    "design_spectrum": "2009 solar minimum",
    "source": "NASA-STD-3001"
  },
  "sun_oberth_repo_band": {
    "near_parabolic_vinf_km_s": [23.17, 33.75],
    "conditional_vinf_km_s": [35.23, 45.32],
    "perihelion_au": [0.05, 0.10],
    "burn_km_s": [2, 3]
  }
}
```

## Source index

- Baguhl et al. 1995, "The flux of interstellar dust observed by Ulysses and Galileo", Space Science Reviews, DOI `10.1007/BF00768822`: https://link.springer.com/article/10.1007/BF00768822
- Krueger, Strub, Grun, Sterken 2015, "16 Years of Ulysses Interstellar Dust Measurements in the Solar System: I", ApJ, DOI `10.1088/0004-637X/812/2/139`: https://arxiv.org/abs/1510.06180
- Mathis, Rumpl, Nordsieck 1977, "The Size Distribution of Interstellar Grains", ApJ, DOI `10.1086/155591`: https://adsabs.harvard.edu/pdf/1977ApJ...217..425M
- Swaczyna et al. 2020, "Density of Neutral Hydrogen in the Sun's Interstellar Neighborhood", ApJ, DOI `10.3847/1538-4357/abb80a`; NASA summary: https://www.nasa.gov/solar-system/new-evidence-our-neighborhood-in-space-is-stuffed-with-hydrogen/
- Gurnett et al. 2013, "In situ observations of interstellar plasma with Voyager 1", Science: https://pubmed.ncbi.nlm.nih.gov/24030496/
- NASA JSC HyperVelocity Impact Technology: https://hvit.jsc.nasa.gov/hypervelocity-testing/
- ESA Space Safety, hypervelocity impacts and spacecraft protection: https://www.esa.int/Space_Safety/Space_Debris/Hypervelocity_impacts_and_protecting_spacecraft
- NASA Meteoroid Engineering Model guide: https://fireballs.ndc.nasa.gov/mem/guide/
- NASA MEM 3 NTRS record: https://ntrs.nasa.gov/citations/20200000563
- NASA-STD-3001 section 4.8.5 GCR limits and BON2020 reference: https://www.nasa.gov/reference/4-0-human-performance/
- NASA RAD Mars radiation measurement resource: https://science.nasa.gov/resource/radiation-measurements-on-mars/
- NIST ESTAR/PSTAR/ASTAR stopping-power and range tables: https://www.nist.gov/pml/stopping-power-range-tables-electrons-protons-and-helium-ions
- NASA/ESA Hubble Alpha Centauri distance page: https://science.nasa.gov/missions/hubble/hubbles-best-image-of-alpha-centauri-a-and-b/
- GRAVITY Collaboration 2019 Galactic-center distance, A&A 625 L10, DOI `10.1051/0004-6361/201935656`: https://arxiv.org/abs/1904.05721
- NASA NIAC solar thermal Oberth Phase I report: https://ntrs.nasa.gov/api/citations/20250001946/downloads/NIAC_2022_PhI_Benkoski_Oberth.pdf
- NASA Parker Solar Probe solar-proximity/speed context: https://www.nasa.gov/solar-system/its-surprisingly-hard-to-go-to-the-sun/
- NASA Voyager 1 mission page: https://science.nasa.gov/mission/voyager/voyager-1/
