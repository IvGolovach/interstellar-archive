import { useMemo, useState } from "react";
import type { ParameterManifestEntry } from "../../lib/parameter_drilldown_loader";
import {
  formatParameterBounds,
  formatParameterDefault,
} from "./parameter_drilldown_helpers";

interface ParameterIndexPageProps {
  parameters: ParameterManifestEntry[];
  onOpenDetail: (parameterId: string) => void;
  dynamicTraceParameterIds: Set<string>;
  devLocalEnabled: boolean;
}

type SortMode = "parameter_id" | "trust_grade" | "modules_touched_count";

function matchesSearch(parameterId: string, searchQuery: string): boolean {
  if (!searchQuery) {
    return true;
  }
  return parameterId.toLowerCase().includes(searchQuery.toLowerCase());
}

function sortParameters(parameters: ParameterManifestEntry[], mode: SortMode): ParameterManifestEntry[] {
  return [...parameters].sort((left, right) => {
    if (mode === "modules_touched_count") {
      if (left.modules_touched_count !== right.modules_touched_count) {
        return right.modules_touched_count - left.modules_touched_count;
      }
      return left.parameter_id.localeCompare(right.parameter_id);
    }
    if (mode === "trust_grade") {
      const trustCmp = left.trust_grade.localeCompare(right.trust_grade);
      if (trustCmp !== 0) {
        return trustCmp;
      }
      return left.parameter_id.localeCompare(right.parameter_id);
    }
    return left.parameter_id.localeCompare(right.parameter_id);
  });
}

export function ParameterIndexPage(props: ParameterIndexPageProps): JSX.Element {
  const { parameters, onOpenDetail, dynamicTraceParameterIds, devLocalEnabled } = props;
  const [searchQuery, setSearchQuery] = useState("");
  const [domainFilter, setDomainFilter] = useState<"all" | "realistic" | "speculative">("all");
  const [trustFilter, setTrustFilter] = useState<"all" | "A" | "B" | "C" | "D">("all");
  const [coreOnly, setCoreOnly] = useState(false);
  const [sortMode, setSortMode] = useState<SortMode>("parameter_id");

  const filteredParameters = useMemo(() => {
    const filtered = parameters.filter((entry) => {
      if (!matchesSearch(entry.parameter_id, searchQuery)) {
        return false;
      }
      if (domainFilter !== "all" && entry.domain !== domainFilter) {
        return false;
      }
      if (trustFilter !== "all" && entry.trust_grade !== trustFilter) {
        return false;
      }
      if (coreOnly && !entry.affects_core_probability) {
        return false;
      }
      return true;
    });
    return sortParameters(filtered, sortMode);
  }, [parameters, searchQuery, domainFilter, trustFilter, coreOnly, sortMode]);

  return (
    <section className="panel drilldown-panel" aria-label="Parameter drilldown index">
      <h2>Parameter Index</h2>
      <p className="help-text">
        Public scope uses committed static artifacts only. This index is intentionally limited to mission, design, and
        environment parameters; internal model literals remain in canonical registries but are excluded from the public
        workspace surface.
      </p>

      <div className="drilldown-filter-grid">
        <label className="field compact-field">
          <span>Search parameter_id</span>
          <input
            type="text"
            value={searchQuery}
            placeholder="e.g. parameter_id fragment"
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </label>
        <label className="field compact-field">
          <span>Domain</span>
          <select value={domainFilter} onChange={(event) => setDomainFilter(event.target.value as typeof domainFilter)}>
            <option value="all">all</option>
            <option value="realistic">realistic</option>
            <option value="speculative">speculative</option>
          </select>
        </label>
        <label className="field compact-field">
          <span>Trust</span>
          <select value={trustFilter} onChange={(event) => setTrustFilter(event.target.value as typeof trustFilter)}>
            <option value="all">all</option>
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
            <option value="D">D</option>
          </select>
        </label>
        <label className="field compact-field">
          <span>Sort</span>
          <select value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)}>
            <option value="parameter_id">parameter_id</option>
            <option value="trust_grade">trust_grade</option>
            <option value="modules_touched_count">modules_touched_count</option>
          </select>
        </label>
      </div>

      <label className="checkbox-row">
        <input type="checkbox" checked={coreOnly} onChange={(event) => setCoreOnly(event.target.checked)} />
        <span>Show only affects_core_probability=true</span>
      </label>

      <p className="help-text">
        Showing {filteredParameters.length} / {parameters.length} public parameters.
      </p>

      <div className="series-table-wrap drilldown-table-wrap">
        <table className="series-table drilldown-table">
          <thead>
            <tr>
              <th>parameter_id</th>
              <th>trust_grade</th>
              <th>domain</th>
              <th>units</th>
              <th>bounds</th>
              <th>default_value</th>
              <th>affects_core_probability</th>
              <th>modules_touched_count</th>
              <th>evidence_status</th>
              <th>has_dynamic_trace</th>
              <th>detail</th>
            </tr>
          </thead>
          <tbody>
            {filteredParameters.map((entry) => {
              const hasDynamicTrace = dynamicTraceParameterIds.has(entry.parameter_id);
              return (
                <tr key={entry.parameter_id}>
                  <td className="mono-cell">{entry.parameter_id}</td>
                  <td>{entry.trust_grade}</td>
                  <td>{entry.domain}</td>
                  <td>{entry.units}</td>
                  <td className="mono-cell">{formatParameterBounds(entry)}</td>
                  <td className="mono-cell">{formatParameterDefault(entry.default_value)}</td>
                  <td>{entry.affects_core_probability ? "true" : "false"}</td>
                  <td>{entry.modules_touched_count}</td>
                  <td title={entry.evidence_status.reason ?? ""}>{entry.evidence_status.status}</td>
                  <td>
                    {devLocalEnabled ? (hasDynamicTrace ? "true" : "false") : "hidden (public)"}
                  </td>
                  <td>
                    <button
                      className="ghost-button"
                      type="button"
                      onClick={() => onOpenDetail(entry.parameter_id)}
                    >
                      Open
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
