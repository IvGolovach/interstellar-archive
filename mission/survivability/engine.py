"""Deterministic deep-time capsule survivability engine.

The model is intentionally reduced-order. It keeps every input value tagged by
provenance and reports the hazard formulas used to integrate annual rates over
the caller-provided flight duration.
"""

from __future__ import annotations

import copy
import hashlib
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple


ENGINE_VERSION = "capsule-survivability-engine-v1"
ALLOWED_PROVENANCE = {"validated_source", "proxy", "assumption"}
ALLOWED_BAND_TARGETS = {
    "capsule.mass_kg",
    "capsule.frontal_area_m2",
    "capsule.shield_areal_density_kg_m2",
    "capsule.data_media_survival_margin",
    "capsule.material_degradation_mu_1_per_year",
    "target.radiation_reference_w_m2",
    "target.plasma_reference_m3",
    "target.dust_reference_scale",
    "trajectory.encounter_velocity_km_s",
    "trajectory.exposure_fraction",
    "trajectory.shield_orientation_factor",
    "environment.radiative_flux_w_m2",
    "environment.plasma_density_proxy_m3",
    "environment.dust_flux_scale",
}

STRUCTURE_DUST_BASE_HAZARD_1_PER_YEAR = 3.0e-9
STRUCTURE_RADIATION_BASE_HAZARD_1_PER_YEAR = 5.0e-10
STRUCTURE_PLASMA_BASE_HAZARD_1_PER_YEAR = 2.0e-10
MEDIA_RADIATION_BASE_HAZARD_1_PER_YEAR = 2.0e-9
MEDIA_PLASMA_BASE_HAZARD_1_PER_YEAR = 1.0e-9
MEDIA_MARGIN_HAZARD_SCALE_1_PER_YEAR = 7.5e-9
MASS_REFERENCE_KG = 200.0
VELOCITY_REFERENCE_KM_S = 20.0

HAZARD_MODEL_COEFFICIENTS = {
    "structure_dust_base_hazard_1_per_year": STRUCTURE_DUST_BASE_HAZARD_1_PER_YEAR,
    "structure_radiation_base_hazard_1_per_year": STRUCTURE_RADIATION_BASE_HAZARD_1_PER_YEAR,
    "structure_plasma_base_hazard_1_per_year": STRUCTURE_PLASMA_BASE_HAZARD_1_PER_YEAR,
    "media_radiation_base_hazard_1_per_year": MEDIA_RADIATION_BASE_HAZARD_1_PER_YEAR,
    "media_plasma_base_hazard_1_per_year": MEDIA_PLASMA_BASE_HAZARD_1_PER_YEAR,
    "media_margin_hazard_scale_1_per_year": MEDIA_MARGIN_HAZARD_SCALE_1_PER_YEAR,
    "mass_reference_kg": MASS_REFERENCE_KG,
    "velocity_reference_km_s": VELOCITY_REFERENCE_KM_S,
}


@dataclass(frozen=True)
class ProvenancedValue:
    value: float
    units: str
    provenance: str
    source_ids: Tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class UncertaintyBand:
    name: str
    target: str
    low: float
    high: float
    provenance: str
    distribution: str = "uniform"


@dataclass(frozen=True)
class _NormalizedValue:
    value: float
    units: str
    provenance: str
    source_ids: Tuple[str, ...]
    note: str


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _round(value: float, digits: int = 12) -> float:
    return float(f"{float(value):.{digits}f}")


def _safe_positive(value: float, *, floor: float = 1.0e-12) -> float:
    return max(float(value), floor)


def _normalize_source_ids(raw: Any) -> Tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, Iterable):
        out = tuple(str(item) for item in raw if str(item).strip())
        return out
    return ()


def _normalize_value(raw: Any, path: str) -> _NormalizedValue:
    if isinstance(raw, ProvenancedValue):
        value = raw.value
        units = raw.units
        provenance = raw.provenance
        source_ids = raw.source_ids
        note = raw.note
    elif isinstance(raw, Mapping) and "value" in raw:
        value = raw.get("value")
        units = str(raw.get("units", ""))
        provenance = str(raw.get("provenance", "assumption"))
        source_ids = _normalize_source_ids(raw.get("source_ids", ()))
        note = str(raw.get("note", ""))
    else:
        value = raw
        units = ""
        provenance = "assumption"
        source_ids = ()
        note = "bare numeric input treated as an explicit assumption"

    if not _is_number(value):
        raise ValueError(f"input {path} must be a finite number")
    if provenance not in ALLOWED_PROVENANCE:
        raise ValueError(f"input {path} has unsupported provenance {provenance!r}")
    if provenance == "validated_source" and not source_ids:
        raise ValueError(f"validated_source input {path} requires source_ids")

    return _NormalizedValue(
        value=float(value),
        units=units,
        provenance=provenance,
        source_ids=tuple(source_ids),
        note=note,
    )


def _extract(
    payload: Mapping[str, Any],
    *,
    prefix: str,
    fields: Mapping[str, Tuple[str, ...]],
) -> Tuple[Dict[str, float], Dict[str, Dict[str, Any]]]:
    values: Dict[str, float] = {}
    provenance: Dict[str, Dict[str, Any]] = {}
    for canonical_key, aliases in fields.items():
        raw: Any = None
        selected_key = ""
        for alias in aliases:
            if alias in payload:
                raw = payload[alias]
                selected_key = alias
                break
        if not selected_key:
            raise ValueError(f"missing required input {prefix}.{canonical_key}")

        path = f"{prefix}.{canonical_key}"
        normalized = _normalize_value(raw, path)
        values[canonical_key] = normalized.value
        provenance[path] = {
            "value": normalized.value,
            "units": normalized.units,
            "provenance": normalized.provenance,
            "source_ids": list(normalized.source_ids),
            "source_backed": normalized.provenance == "validated_source",
            "input_key": selected_key,
            "note": normalized.note,
        }
    return values, provenance


def _provenanced_dict(
    value: float,
    *,
    units: str,
    provenance: str,
    source_ids: Sequence[str] = (),
    note: str = "",
) -> Dict[str, Any]:
    return {
        "value": value,
        "units": units,
        "provenance": provenance,
        "source_ids": list(source_ids),
        "note": note,
    }


def _coerce_capsule_design_inputs(capsule_design: Mapping[str, Any]) -> Mapping[str, Any]:
    """Accept either flat engine inputs or the public capsule design contract."""

    if capsule_design.get("schema_version") != "capsule_design.v1":
        return capsule_design

    from mission.capsule.design import summarize_mass_budget, validate_capsule_design

    errors = validate_capsule_design(capsule_design)
    if errors:
        raise ValueError("capsule_design.v1 validation failed: " + "; ".join(errors))

    summary = summarize_mass_budget(capsule_design)
    model_inputs = capsule_design.get("survivability_model_inputs", {})
    if not isinstance(model_inputs, Mapping):
        raise ValueError("capsule_design.v1 survivability_model_inputs must be object")

    coerced: Dict[str, Any] = {
        "mass_kg": _provenanced_dict(
            float(summary["configured_capsule_mass_kg"]),
            units="kg",
            provenance="proxy",
            source_ids=("SRC-GENESIS-SRC-205-6KG",),
            note="Capsule design mass closure from public capsule_design.v1 stack.",
        )
    }
    for field in (
        "frontal_area_m2",
        "shield_areal_density_kg_m2",
        "data_media_survival_margin",
        "material_degradation_mu_1_per_year",
    ):
        if field not in model_inputs:
            raise ValueError(f"capsule_design.v1 survivability_model_inputs.{field} is required")
        coerced[field] = model_inputs[field]

    return coerced


def _normalize_inputs(
    *,
    capsule_design: Mapping[str, Any],
    target: Mapping[str, Any],
    trajectory: Mapping[str, Any],
    environment: Mapping[str, Any],
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, Any]]]:
    capsule_design = _coerce_capsule_design_inputs(capsule_design)
    capsule, capsule_provenance = _extract(
        capsule_design,
        prefix="capsule",
        fields={
            "mass_kg": ("mass_kg",),
            "frontal_area_m2": ("frontal_area_m2",),
            "shield_areal_density_kg_m2": ("shield_areal_density_kg_m2",),
            "data_media_survival_margin": ("data_media_survival_margin",),
            "material_degradation_mu_1_per_year": ("material_degradation_mu_1_per_year",),
        },
    )
    target_values, target_provenance = _extract(
        target,
        prefix="target",
        fields={
            "radiation_reference_w_m2": (
                "radiation_reference_w_m2",
                "max_radiative_flux_w_m2",
            ),
            "plasma_reference_m3": (
                "plasma_reference_m3",
                "max_plasma_density_proxy_m3",
            ),
            "dust_reference_scale": (
                "dust_reference_scale",
                "max_dust_flux_scale",
            ),
        },
    )
    trajectory_values, trajectory_provenance = _extract(
        trajectory,
        prefix="trajectory",
        fields={
            "encounter_velocity_km_s": ("encounter_velocity_km_s", "relative_velocity_km_s"),
            "exposure_fraction": ("exposure_fraction",),
            "shield_orientation_factor": ("shield_orientation_factor",),
        },
    )
    environment_values, environment_provenance = _extract(
        environment,
        prefix="environment",
        fields={
            "radiative_flux_w_m2": ("radiative_flux_w_m2",),
            "plasma_density_proxy_m3": ("plasma_density_proxy_m3",),
            "dust_flux_scale": ("dust_flux_scale",),
        },
    )

    provenance: Dict[str, Dict[str, Any]] = {}
    provenance.update(capsule_provenance)
    provenance.update(target_provenance)
    provenance.update(trajectory_provenance)
    provenance.update(environment_provenance)

    return (
        {
            "capsule": capsule,
            "target": target_values,
            "trajectory": trajectory_values,
            "environment": environment_values,
        },
        provenance,
    )


def _validate_physical_inputs(values: Mapping[str, Mapping[str, float]]) -> None:
    capsule = values["capsule"]
    target = values["target"]
    trajectory = values["trajectory"]
    environment = values["environment"]

    positive_paths = {
        "capsule.mass_kg": capsule["mass_kg"],
        "capsule.frontal_area_m2": capsule["frontal_area_m2"],
        "capsule.shield_areal_density_kg_m2": capsule["shield_areal_density_kg_m2"],
        "capsule.material_degradation_mu_1_per_year": capsule["material_degradation_mu_1_per_year"],
        "target.radiation_reference_w_m2": target["radiation_reference_w_m2"],
        "target.plasma_reference_m3": target["plasma_reference_m3"],
        "target.dust_reference_scale": target["dust_reference_scale"],
        "trajectory.encounter_velocity_km_s": trajectory["encounter_velocity_km_s"],
    }
    for path, value in positive_paths.items():
        if value <= 0.0:
            raise ValueError(f"input {path} must be > 0")

    fraction_paths = {
        "capsule.data_media_survival_margin": capsule["data_media_survival_margin"],
        "trajectory.exposure_fraction": trajectory["exposure_fraction"],
        "trajectory.shield_orientation_factor": trajectory["shield_orientation_factor"],
    }
    for path, value in fraction_paths.items():
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"input {path} must be in [0, 1]")

    non_negative_paths = {
        "environment.radiative_flux_w_m2": environment["radiative_flux_w_m2"],
        "environment.plasma_density_proxy_m3": environment["plasma_density_proxy_m3"],
        "environment.dust_flux_scale": environment["dust_flux_scale"],
    }
    for path, value in non_negative_paths.items():
        if value < 0.0:
            raise ValueError(f"input {path} must be >= 0")


def _u01(*, seed: int, sample_index: int, band_index: int, stream: int, name: str) -> float:
    payload = f"{seed}:{sample_index}:{band_index}:{stream}:{name}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    value = int.from_bytes(digest[:8], "big")
    return (value + 0.5) / 18446744073709551616.0


def _sample_band(band: UncertaintyBand, *, seed: int, sample_index: int, band_index: int) -> float:
    if band.distribution != "uniform":
        raise ValueError(f"uncertainty band {band.name} uses unsupported distribution {band.distribution!r}")
    u = _u01(seed=seed, sample_index=sample_index, band_index=band_index, stream=0, name=band.name)
    return band.low + u * (band.high - band.low)


def _validate_bands(bands: Sequence[UncertaintyBand]) -> None:
    seen: set[str] = set()
    for band in bands:
        if not band.name.strip():
            raise ValueError("uncertainty band name must be non-empty")
        if band.name in seen:
            raise ValueError(f"uncertainty band {band.name} is duplicated")
        seen.add(band.name)
        if band.target not in ALLOWED_BAND_TARGETS:
            raise ValueError(f"uncertainty band {band.name} has unsupported target {band.target!r}")
        if band.provenance not in ALLOWED_PROVENANCE:
            raise ValueError(f"uncertainty band {band.name} has unsupported provenance {band.provenance!r}")
        if not (_is_number(band.low) and _is_number(band.high)):
            raise ValueError(f"uncertainty band {band.name} bounds must be finite numbers")
        if not float(band.low) < float(band.high):
            raise ValueError(f"uncertainty band {band.name} must satisfy low < high")


def _apply_draw(values: MutableMapping[str, Dict[str, float]], target: str, value: float) -> None:
    group, key = target.split(".", 1)
    values[group][key] = float(value)


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("quantile requires values")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] + (ordered[high] - ordered[low]) * weight


def _survival_metrics(values: Mapping[str, Mapping[str, float]], *, flight_years: float) -> Dict[str, Any]:
    capsule = values["capsule"]
    target = values["target"]
    trajectory = values["trajectory"]
    environment = values["environment"]

    exposure_years = flight_years * trajectory["exposure_fraction"]
    radiation_ratio = environment["radiative_flux_w_m2"] / _safe_positive(target["radiation_reference_w_m2"])
    plasma_ratio = environment["plasma_density_proxy_m3"] / _safe_positive(target["plasma_reference_m3"])
    dust_ratio = environment["dust_flux_scale"] / _safe_positive(target["dust_reference_scale"])
    velocity_factor = trajectory["encounter_velocity_km_s"] / VELOCITY_REFERENCE_KM_S
    mass_factor = math.sqrt(MASS_REFERENCE_KG / _safe_positive(capsule["mass_kg"]))
    shield_factor = 1.0 / (_safe_positive(capsule["shield_areal_density_kg_m2"]) ** 0.75)
    area_factor = capsule["frontal_area_m2"]
    orientation_factor = trajectory["shield_orientation_factor"]
    media_margin_gap = 1.0 - capsule["data_media_survival_margin"]

    dust_hazard = (
        STRUCTURE_DUST_BASE_HAZARD_1_PER_YEAR
        * dust_ratio
        * area_factor
        * shield_factor
        * (velocity_factor**2)
        * mass_factor
        * orientation_factor
    )
    structure_radiation_hazard = STRUCTURE_RADIATION_BASE_HAZARD_1_PER_YEAR * max(0.0, radiation_ratio)
    structure_plasma_hazard = STRUCTURE_PLASMA_BASE_HAZARD_1_PER_YEAR * math.sqrt(max(0.0, plasma_ratio))
    material_hazard = capsule["material_degradation_mu_1_per_year"]
    structure_hazard = material_hazard + dust_hazard + structure_radiation_hazard + structure_plasma_hazard

    media_margin_hazard = MEDIA_MARGIN_HAZARD_SCALE_1_PER_YEAR * media_margin_gap
    media_material_hazard = material_hazard * (1.0 + media_margin_gap)
    media_radiation_hazard = MEDIA_RADIATION_BASE_HAZARD_1_PER_YEAR * max(0.0, radiation_ratio)
    media_plasma_hazard = MEDIA_PLASMA_BASE_HAZARD_1_PER_YEAR * math.sqrt(max(0.0, plasma_ratio))
    media_hazard = media_material_hazard + media_margin_hazard + media_radiation_hazard + media_plasma_hazard

    structure_integrated_hazard = structure_hazard * exposure_years
    media_integrated_hazard = media_hazard * exposure_years
    structure_survival = _clamp(math.exp(-structure_integrated_hazard))
    media_integrity = _clamp(math.exp(-media_integrated_hazard))

    return {
        "structure_survival": structure_survival,
        "media_integrity": media_integrity,
        "total_capsule_survival": structure_survival * media_integrity,
        "annual_hazards": {
            "structure": structure_hazard,
            "media": media_hazard,
        },
        "integrated_hazards": {
            "structure": structure_integrated_hazard,
            "media": media_integrated_hazard,
        },
        "hazard_components": {
            "structure": {
                "material": material_hazard,
                "dust": dust_hazard,
                "radiation": structure_radiation_hazard,
                "plasma": structure_plasma_hazard,
            },
            "media": {
                "material": media_material_hazard,
                "margin_gap": media_margin_hazard,
                "radiation": media_radiation_hazard,
                "plasma": media_plasma_hazard,
            },
        },
        "normalized_exposures": {
            "radiation_ratio": radiation_ratio,
            "plasma_ratio": plasma_ratio,
            "dust_ratio": dust_ratio,
            "velocity_factor": velocity_factor,
            "mass_factor": mass_factor,
            "shield_factor": shield_factor,
            "exposure_years": exposure_years,
        },
    }


def _stable_metrics(metrics: Mapping[str, Any]) -> Dict[str, Any]:
    structure_survival = _round(metrics["structure_survival"])
    media_integrity = _round(metrics["media_integrity"])
    return {
        "structure_survival": structure_survival,
        "media_integrity": media_integrity,
        "total_capsule_survival": structure_survival * media_integrity,
        "annual_hazards": {
            "structure": metrics["annual_hazards"]["structure"],
            "media": metrics["annual_hazards"]["media"],
        },
        "integrated_hazards": {
            "structure": metrics["integrated_hazards"]["structure"],
            "media": metrics["integrated_hazards"]["media"],
        },
        "hazard_components": copy.deepcopy(metrics["hazard_components"]),
        "normalized_exposures": copy.deepcopy(metrics["normalized_exposures"]),
    }


def _band(values: Sequence[float]) -> Dict[str, float]:
    return {
        "min": min(values),
        "p05": _quantile(values, 0.05),
        "p50": _quantile(values, 0.50),
        "p95": _quantile(values, 0.95),
        "max": max(values),
    }


def _provenance_summary(input_provenance: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    by_class: Dict[str, List[str]] = {key: [] for key in sorted(ALLOWED_PROVENANCE)}
    for path, payload in input_provenance.items():
        provenance = str(payload["provenance"])
        by_class.setdefault(provenance, []).append(path)
    for paths in by_class.values():
        paths.sort()
    return {
        "validated_source_inputs": by_class.get("validated_source", []),
        "proxy_inputs": by_class.get("proxy", []),
        "assumption_inputs": by_class.get("assumption", []),
        "counts": {
            "validated_source": len(by_class.get("validated_source", [])),
            "proxy": len(by_class.get("proxy", [])),
            "assumption": len(by_class.get("assumption", [])),
        },
    }


def _formulas() -> Dict[str, str]:
    return {
        "hazard_integration": "exp(-annual_hazard_1_per_year * flight_years * exposure_fraction)",
        "structure_survival": "exp(-(material + dust + radiation + plasma) * flight_years * exposure_fraction)",
        "media_integrity": "exp(-(media_material + media_margin_gap + radiation + plasma) * flight_years * exposure_fraction)",
        "total_capsule_survival": "structure_survival * media_integrity",
        "dust_hazard": (
            "structure_dust_base_hazard * dust_ratio * frontal_area_m2 * shield_areal_density_kg_m2^-0.75 "
            "* (encounter_velocity_km_s / 20)^2 * sqrt(200 / mass_kg) * shield_orientation_factor"
        ),
    }


def _model_coefficients() -> Dict[str, Dict[str, Any]]:
    coefficients: Dict[str, Dict[str, Any]] = {}
    for name, value in sorted(HAZARD_MODEL_COEFFICIENTS.items()):
        if name == "mass_reference_kg":
            units = "kg"
        elif name == "velocity_reference_km_s":
            units = "km/s"
        else:
            units = "1/year"
        coefficients[name] = {
            "value": value,
            "units": units,
            "provenance": "assumption",
            "source_ids": ["SRC-CAPSULE-MODEL-COEFFICIENTS-V1"],
            "source_backed": False,
            "note": "Reduced-order v1 coefficient; exposes model assumption rather than hardware qualification.",
        }
    return coefficients


def run_survivability_analysis(
    *,
    capsule_design: Mapping[str, Any],
    target: Mapping[str, Any],
    trajectory: Mapping[str, Any],
    flight_years: float,
    environment: Mapping[str, Any],
    uncertainty_bands: Sequence[UncertaintyBand],
    samples: int,
    seed: int,
) -> Dict[str, Any]:
    if not _is_number(flight_years) or float(flight_years) <= 0.0:
        raise ValueError("flight_years must be > 0")
    if isinstance(samples, bool) or not isinstance(samples, int) or samples <= 0:
        raise ValueError("samples must be a positive integer")

    _validate_bands(uncertainty_bands)
    values, input_provenance = _normalize_inputs(
        capsule_design=capsule_design,
        target=target,
        trajectory=trajectory,
        environment=environment,
    )
    _validate_physical_inputs(values)

    nominal_metrics = _stable_metrics(_survival_metrics(values, flight_years=float(flight_years)))

    sample_results: List[Dict[str, Any]] = []
    for sample_index in range(samples):
        sampled_values = copy.deepcopy(values)
        draws: Dict[str, float] = {}
        draw_provenance: Dict[str, str] = {}
        for band_index, band in enumerate(uncertainty_bands):
            sampled = _sample_band(
                band,
                seed=int(seed),
                sample_index=sample_index,
                band_index=band_index,
            )
            _apply_draw(sampled_values, band.target, sampled)
            draws[band.name] = sampled
            draw_provenance[band.name] = band.provenance
        _validate_physical_inputs(sampled_values)
        metrics = _stable_metrics(_survival_metrics(sampled_values, flight_years=float(flight_years)))
        sample_results.append(
            {
                "sample_id": f"s{sample_index:04d}",
                "uncertainty_draws": draws,
                "uncertainty_provenance": draw_provenance,
                "structure_survival": metrics["structure_survival"],
                "media_integrity": metrics["media_integrity"],
                "total_capsule_survival": metrics["total_capsule_survival"],
                "annual_hazards": metrics["annual_hazards"],
                "integrated_hazards": metrics["integrated_hazards"],
            }
        )

    structure_values = [item["structure_survival"] for item in sample_results]
    media_values = [item["media_integrity"] for item in sample_results]
    total_values = [item["total_capsule_survival"] for item in sample_results]

    return {
        "engine_version": ENGINE_VERSION,
        "flight_years": float(flight_years),
        "sample_count": samples,
        "seed": int(seed),
        "nominal": nominal_metrics,
        "scenario_bands": {
            "structure_survival": _band(structure_values),
            "media_integrity": _band(media_values),
            "total_capsule_survival": _band(total_values),
        },
        "samples": sample_results,
        "input_provenance": dict(sorted(input_provenance.items())),
        "provenance_summary": _provenance_summary(input_provenance),
        "model_coefficients": _model_coefficients(),
        "uncertainty_model": [
            {
                "name": band.name,
                "target": band.target,
                "low": float(band.low),
                "high": float(band.high),
                "provenance": band.provenance,
                "distribution": band.distribution,
            }
            for band in uncertainty_bands
        ],
        "formulas": _formulas(),
    }
