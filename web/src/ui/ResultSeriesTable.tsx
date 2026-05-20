import type { SimOutput } from "../../../sim/public/types";
import { formatResultNumber } from "./result_view_helpers";

interface ResultSeriesTableProps {
  output: SimOutput | null;
}

export function ResultSeriesTable(props: ResultSeriesTableProps): JSX.Element {
  const { output } = props;

  if (!output) {
    return (
      <p className="help-text">
        Run a scenario to generate deterministic output metrics and the full series table.
      </p>
    );
  }

  return (
    <div className="series-table-wrap">
      <table className="series-table">
        <thead>
          <tr>
            <th>Year</th>
            <th>Control leverage</th>
            <th>Encounter likelihood</th>
            <th>Lethal hit rate</th>
          </tr>
        </thead>
        <tbody>
          {output.series.map((point) => (
            <tr key={point.year}>
              <td>{point.year}</td>
              <td>{formatResultNumber(point.control_leverage)}</td>
              <td>{formatResultNumber(point.encounter_likelihood)}</td>
              <td>{formatResultNumber(point.lethal_hit_rate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
