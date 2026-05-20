import type { SimOutput, SimSeriesPoint } from "../../../sim/public/types";

export interface MetricCard {
  id: string;
  label: string;
  value: number | string;
  unit: string;
  tooltip?: string;
}

export function formatResultNumber(value: number): string {
  if (!Number.isFinite(value)) {
    return "-";
  }
  if (Math.abs(value) >= 1000) {
    return value.toFixed(0);
  }
  if (Math.abs(value) >= 100) {
    return value.toFixed(2);
  }
  if (Math.abs(value) >= 10) {
    return value.toFixed(3);
  }
  return value.toFixed(4);
}

export function chartPath(
  series: SimSeriesPoint[],
  metric: "encounter_likelihood" | "lethal_hit_rate",
): string {
  if (series.length === 0) {
    return "";
  }

  const width = 600;
  const height = 200;
  const padding = 24;
  const xMin = series[0].year;
  const xMax = series[series.length - 1].year;
  const values = series.map((point) => point[metric]);
  const yMin = Math.min(...values);
  const yMax = Math.max(...values);
  const ySpan = yMax - yMin || 1;
  const xSpan = xMax - xMin || 1;

  return series
    .map((point, index) => {
      const x = padding + ((point.year - xMin) / xSpan) * (width - padding * 2);
      const y = height - padding - ((point[metric] - yMin) / ySpan) * (height - padding * 2);
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

export function buildMetricCards(output: SimOutput | null): MetricCard[] {
  if (!output) {
    return [
      { id: "finite_control_window_year", label: "Finite control window", value: "-", unit: "years" },
      { id: "terminal_interaction_radius_au", label: "Terminal interaction radius", value: "-", unit: "AU" },
      { id: "encounter_likelihood_percent", label: "Encounter likelihood", value: "-", unit: "%" },
      { id: "expected_mm_tail_hits", label: "Expected mm-tail hits", value: "-", unit: "hits" },
      { id: "shield_survival_margin", label: "Shield survival margin", value: "-", unit: "ratio" },
      { id: "invariants_passed", label: "Invariants", value: "-", unit: "status" },
    ];
  }

  const horizonPoint = output.series[output.series.length - 1];

  return [
    {
      id: "finite_control_window_year",
      label: "Finite control window",
      value: output.derived_metrics.finite_control_window_year,
      unit: "years",
      tooltip: "Last year where early intervention still has meaningful leverage.",
    },
    {
      id: "terminal_interaction_radius_au",
      label: "Terminal interaction radius",
      value: output.derived_metrics.terminal_interaction_radius_au,
      unit: "AU",
      tooltip: "Distance threshold defining terminal interaction in this scenario.",
    },
    {
      id: "encounter_likelihood_percent",
      label: "Encounter likelihood",
      value: output.derived_metrics.encounter_likelihood_percent,
      unit: "%",
      tooltip: "Aggregate encounter likelihood over the simulated horizon.",
    },
    {
      id: "expected_mm_tail_hits",
      label: "Expected mm-tail hits",
      value: output.derived_metrics.expected_mm_tail_hits,
      unit: "hits",
      tooltip: "Expected cumulative high-velocity dust impacts.",
    },
    {
      id: "shield_survival_margin",
      label: "Shield survival margin",
      value: output.derived_metrics.shield_survival_margin,
      unit: "ratio",
      tooltip: "Protective margin under modeled thermal and impact loads.",
    },
    {
      id: "invariants_passed",
      label: "Invariants",
      value: output.invariants_passed ? "pass" : "fail",
      unit: "status",
      tooltip: "Core deterministic and safety checks for this run.",
    },
    {
      id: "horizon_encounter",
      label: "Horizon encounter",
      value: horizonPoint?.encounter_likelihood ?? 0,
      unit: "fraction",
      tooltip: "Encounter likelihood at the final simulated year.",
    },
    {
      id: "horizon_lethal",
      label: "Horizon lethal hit rate",
      value: horizonPoint?.lethal_hit_rate ?? 0,
      unit: "fraction",
      tooltip: "Lethal hit rate at the final simulated year.",
    },
  ];
}
