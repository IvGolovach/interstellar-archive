import { useMemo } from "react";
import type { SimOutput } from "../../../sim/public/types";
import { ResultIntegritySection } from "./ResultIntegritySection";
import { ResultLineChart } from "./ResultLineChart";
import { ResultMetricsSection } from "./ResultMetricsSection";
import { ResultReproducibilitySection } from "./ResultReproducibilitySection";
import { ResultSeriesTable } from "./ResultSeriesTable";
import { buildMetricCards } from "./result_view_helpers";

interface ResultViewProps {
  output: SimOutput | null;
  lastVerifiedCommitSha: string;
  deterministicEngineVersion: string;
  deterministicSchemaVersion: string;
  deterministicGoldenChecksum: string | null;
}

export function ResultView({
  output,
  lastVerifiedCommitSha,
  deterministicEngineVersion,
  deterministicSchemaVersion,
  deterministicGoldenChecksum,
}: ResultViewProps): JSX.Element {
  const cards = useMemo(() => buildMetricCards(output), [output]);
  const checksumValue = output?.golden_checksum ?? deterministicGoldenChecksum;
  const engineVersion = output?.engine_version ?? deterministicEngineVersion;
  const schemaVersion = output?.schema_version ?? deterministicSchemaVersion;

  return (
    <section>
      <h2>Results</h2>

      <ResultMetricsSection cards={cards} />

      <ResultIntegritySection checksumValue={checksumValue} />

      <ResultReproducibilitySection
        checksumValue={checksumValue}
        engineVersion={engineVersion}
        schemaVersion={schemaVersion}
        lastVerifiedCommitSha={lastVerifiedCommitSha}
      />

      <div className="chart-grid">
        <ResultLineChart
          title="Encounter likelihood by year"
          series={output?.series ?? []}
          metric="encounter_likelihood"
        />
        <ResultLineChart
          title="Lethal hit rate by year"
          series={output?.series ?? []}
          metric="lethal_hit_rate"
        />
      </div>

      <ResultSeriesTable output={output} />
    </section>
  );
}
