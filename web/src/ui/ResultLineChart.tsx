import { useMemo } from "react";
import type { SimSeriesPoint } from "../../../sim/public/types";
import {
  chartPath,
  formatResultNumber,
} from "./result_view_helpers";

interface ResultLineChartProps {
  title: string;
  series: SimSeriesPoint[];
  metric: "encounter_likelihood" | "lethal_hit_rate";
}

export function ResultLineChart(props: ResultLineChartProps): JSX.Element {
  const { title, series, metric } = props;
  const path = useMemo(() => chartPath(series, metric), [series, metric]);
  const firstYear = series[0]?.year ?? 0;
  const lastYear = series[series.length - 1]?.year ?? 0;
  const firstValue = series[0]?.[metric] ?? 0;
  const lastValue = series[series.length - 1]?.[metric] ?? 0;

  return (
    <article className="chart-card">
      <h4>{title}</h4>
      {series.length > 0 ? (
        <>
          <svg className="line-chart" viewBox="0 0 600 200" role="img" aria-label={title}>
            <path
              className="line-chart-grid"
              d="M24 24 L576 24 M24 88 L576 88 M24 152 L576 152 M24 176 L576 176"
            />
            <path className="line-chart-main" d={path} />
          </svg>
          <div className="chart-footnote">
            <span>
              {firstYear}: {formatResultNumber(firstValue)}
            </span>
            <span>
              {lastYear}: {formatResultNumber(lastValue)}
            </span>
          </div>
        </>
      ) : (
        <p className="help-text">Run a scenario to render this chart.</p>
      )}
    </article>
  );
}
