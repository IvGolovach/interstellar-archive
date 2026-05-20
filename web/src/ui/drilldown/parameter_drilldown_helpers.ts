import type {
  DynamicTraceIndex,
  ParameterManifestEntry,
} from "../../lib/parameter_drilldown_loader";

export function formatParameterDefault(value: unknown): string {
  if (value === null || value === undefined) {
    return "N/A";
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? String(value) : "N/A";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value);
}

export function formatParameterBounds(entry: ParameterManifestEntry): string {
  if (!entry.bounds.has_bounds) {
    return "N/A";
  }
  const low = entry.bounds.minimum ?? "-";
  const high = entry.bounds.maximum ?? "-";
  return `[${low}, ${high}]${entry.bounds.is_fixed ? " fixed" : ""}`;
}

export function dynamicEventsForParameter(
  trace: DynamicTraceIndex,
  parameterId: string,
): DynamicTraceIndex["events"] {
  return trace.events.filter((event) => event.dominant_driver_parameter_ids.includes(parameterId));
}
