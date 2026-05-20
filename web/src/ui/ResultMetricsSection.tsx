import type { MetricCard } from "./result_view_helpers";
import { formatResultNumber } from "./result_view_helpers";

interface ResultMetricsSectionProps {
  cards: MetricCard[];
}

export function ResultMetricsSection(props: ResultMetricsSectionProps): JSX.Element {
  const { cards } = props;

  return (
    <div className="metrics-section">
      <h3>Key metrics</h3>
      <div className="metrics-cards-grid">
        {cards.map((card) => (
          <article key={card.id} className="metric-card" title={card.tooltip ?? card.label}>
            <p className="metric-label">{card.label}</p>
            <p className="metric-value">
              {typeof card.value === "number" ? formatResultNumber(card.value) : card.value}
            </p>
            <p className="metric-unit">{card.unit}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
