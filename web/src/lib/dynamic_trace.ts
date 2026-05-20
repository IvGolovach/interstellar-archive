import type {
  DynamicStaticValidationResult,
  DynamicStaticViolation,
  DynamicTraceIndex,
} from "./dynamic_trace_contract";
import type { ParameterStaticUsageEntry } from "./parameter_drilldown_dataset_contract";

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseDynamicTraceIndex(rawJson: string): DynamicTraceIndex {
  const candidate = JSON.parse(rawJson) as DynamicTraceIndex;
  if (!isObject(candidate)) {
    throw new Error("Dynamic trace payload must be an object.");
  }
  const requiredFields: Array<keyof DynamicTraceIndex> = [
    "run_id",
    "commit_sha",
    "mode",
    "seed",
    "scenario_path",
    "artifact_hash",
    "hashchain_verified",
    "events",
  ];
  for (const field of requiredFields) {
    if (!(field in candidate)) {
      throw new Error(`Dynamic trace payload missing field '${field}'.`);
    }
  }
  if (!Array.isArray(candidate.events)) {
    throw new Error("Dynamic trace field 'events' must be an array.");
  }
  return candidate;
}

export function validateDynamicTraceAgainstStatic(
  trace: DynamicTraceIndex,
  staticUsageGraph: Record<string, ParameterStaticUsageEntry>,
): DynamicStaticValidationResult {
  const errors: string[] = [];
  const violations: DynamicStaticViolation[] = [];
  let checkedPairs = 0;

  for (const [eventIndex, event] of trace.events.entries()) {
    if (!isObject(event)) {
      errors.push(`events[${eventIndex}] must be an object`);
      continue;
    }

    const moduleId = String(event.module_id ?? "").trim();
    if (!moduleId) {
      errors.push(`events[${eventIndex}].module_id must be non-empty string`);
      continue;
    }

    const drivers = event.dominant_driver_parameter_ids;
    if (!Array.isArray(drivers)) {
      errors.push(`events[${eventIndex}].dominant_driver_parameter_ids must be an array`);
      continue;
    }

    for (const parameter of drivers) {
      const parameterId = String(parameter ?? "").trim();
      if (!parameterId) {
        errors.push(`events[${eventIndex}] has invalid parameter id in dominant_driver_parameter_ids`);
        continue;
      }
      checkedPairs += 1;

      const staticEntry = staticUsageGraph[parameterId];
      if (!staticEntry) {
        violations.push({
          event_index: eventIndex,
          parameter_id: parameterId,
          module_id: moduleId,
          reason: "parameter_id missing in static usage graph",
        });
        continue;
      }

      if (!Array.isArray(staticEntry.modules)) {
        violations.push({
          event_index: eventIndex,
          parameter_id: parameterId,
          module_id: moduleId,
          reason: "static usage graph modules field is not an array",
        });
        continue;
      }

      if (!staticEntry.modules.includes(moduleId)) {
        violations.push({
          event_index: eventIndex,
          parameter_id: parameterId,
          module_id: moduleId,
          reason: "dynamic trace module not declared in static usage graph",
        });
      }
    }
  }

  return {
    status: errors.length === 0 && violations.length === 0 ? "PASS" : "FAIL",
    event_count: trace.events.length,
    checked_parameter_module_pairs: checkedPairs,
    violation_count: violations.length,
    violations,
    errors,
  };
}

export function collectDynamicTraceParameterIds(trace: DynamicTraceIndex): Set<string> {
  const ids = new Set<string>();
  for (const event of trace.events) {
    for (const parameterId of event.dominant_driver_parameter_ids ?? []) {
      ids.add(parameterId);
    }
  }
  return ids;
}
