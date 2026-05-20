import { sha256Hex } from "./hash";
import { createSeededRng } from "./rng";
import { canonicalStringify } from "./serialize";
import { clamp, roundTo } from "./units";
import { SIM_ENGINE_VERSION, type SimInput, type SimOutput, type SimSeriesPoint } from "./types";

const OUTPUT_VERSION = "sim_output.v1";
const NON_PHYSICAL_WARNING =
  "Non-physical knobs break realism; use for sensitivity exploration only.";

const NON_PHYSICAL_DEFAULTS = {
  narrative_leverage_multiplier: 1,
  irreversibility_override: 0,
};

function hasNonPhysicalDeviation(input: SimInput): boolean {
  return (
    input.params.narrative_leverage_multiplier !== NON_PHYSICAL_DEFAULTS.narrative_leverage_multiplier ||
    input.params.irreversibility_override !== NON_PHYSICAL_DEFAULTS.irreversibility_override
  );
}

function buildSeries(input: SimInput): SimSeriesPoint[] {
  const rng = createSeededRng(input.seed);
  const series: SimSeriesPoint[] = [];

  const maxSteps = Math.max(1, Math.floor(input.clock.horizon_years / input.clock.step_years));
  const leverageHalfLife = clamp(
    input.params.correction_window_years / (1 + input.params.uncertainty_growth_per_year),
    2,
    80,
  );
  const interactionRadius = clamp(
    input.params.encounter_distance_au / (1 + input.params.initial_delta_v_mps / 30),
    15,
    5000,
  );

  let previousLeverage = Number.POSITIVE_INFINITY;
  for (let step = 0; step <= maxSteps; step += 1) {
    const year = roundTo(step * input.clock.step_years, 3);
    const baseLeverage = Math.exp(-year / leverageHalfLife);
    const uncertaintyPenalty = 1 / (1 + input.params.uncertainty_growth_per_year * year);
    const geometryTerm = input.params.shield_geometry_factor / (1 + input.params.dust_flux_scale * 0.25);
    const seededPerturbation = 1 + (rng.next() - 0.5) * 0.015;
    const nonPhysicalTerm =
      input.params.narrative_leverage_multiplier + input.params.irreversibility_override * 0.05;

    let leverage = baseLeverage * uncertaintyPenalty * geometryTerm * seededPerturbation * nonPhysicalTerm;
    leverage = clamp(leverage, 0, 1.25);
    leverage = Math.min(previousLeverage, leverage);
    previousLeverage = leverage;

    const exposure = year / Math.max(input.clock.horizon_years, 1);
    const lethalHitRate = clamp(
      (input.params.dust_flux_scale * exposure) / Math.max(input.params.shield_geometry_factor, 0.1),
      0,
      10,
    );
    const encounterLikelihood = clamp(1 - leverage / (1 + interactionRadius / 400), 0, 1);

    series.push({
      year,
      control_leverage: roundTo(leverage, 6),
      encounter_likelihood: roundTo(encounterLikelihood, 6),
      lethal_hit_rate: roundTo(lethalHitRate, 6),
    });
  }

  return series;
}

function evaluateInvariants(series: SimSeriesPoint[]): boolean {
  if (series.length < 2) {
    return false;
  }

  for (let index = 0; index < series.length; index += 1) {
    const point = series[index];
    const finite =
      Number.isFinite(point.year) &&
      Number.isFinite(point.control_leverage) &&
      Number.isFinite(point.encounter_likelihood) &&
      Number.isFinite(point.lethal_hit_rate);
    if (!finite) {
      return false;
    }

    if (point.encounter_likelihood < 0 || point.encounter_likelihood > 1) {
      return false;
    }

    if (index > 0 && point.control_leverage > series[index - 1].control_leverage + 1e-9) {
      return false;
    }
  }

  return true;
}

export function runSimulation(input: SimInput): SimOutput {
  const series = buildSeries(input);
  const last = series[series.length - 1];
  const expectedHits = roundTo(
    series.reduce((accumulator, point) => accumulator + point.lethal_hit_rate * input.clock.step_years, 0),
    6,
  );
  const interactionRadius = clamp(
    input.params.encounter_distance_au / (1 + input.params.initial_delta_v_mps / 30),
    15,
    5000,
  );

  let finiteWindowYear = input.clock.horizon_years;
  for (const point of series) {
    if (point.control_leverage < 0.1) {
      finiteWindowYear = point.year;
      break;
    }
  }

  const invariantsPassed = evaluateInvariants(series);
  const warnings: string[] = [];
  if (hasNonPhysicalDeviation(input)) {
    warnings.push(NON_PHYSICAL_WARNING);
  }
  if (!invariantsPassed) {
    warnings.push("Invariant checks failed; output should not be treated as valid.");
  }

  const payload = {
    output_version: OUTPUT_VERSION,
    engine_version: SIM_ENGINE_VERSION,
    schema_version: input.schema_version,
    derived_metrics: {
      finite_control_window_year: roundTo(finiteWindowYear, 6),
      terminal_interaction_radius_au: roundTo(interactionRadius, 6),
      encounter_likelihood_percent: roundTo(last.encounter_likelihood * 100, 6),
      expected_mm_tail_hits: expectedHits,
      shield_survival_margin: roundTo(input.params.shield_geometry_factor / (1 + expectedHits), 6),
    },
    series,
    warnings,
    invariants_passed: invariantsPassed,
  };

  const checksumPayload = canonicalStringify(payload);
  const goldenChecksum = sha256Hex(checksumPayload);

  return {
    ...payload,
    golden_checksum: goldenChecksum,
    checksum_payload: checksumPayload,
  };
}

export { NON_PHYSICAL_WARNING };
