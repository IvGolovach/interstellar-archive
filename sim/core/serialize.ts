import { roundTo } from "./units";

type CanonicalValue =
  | null
  | boolean
  | number
  | string
  | CanonicalValue[]
  | { [key: string]: CanonicalValue };

function normalizeNumber(value: number): number {
  return roundTo(value, 12);
}

function canonicalize(value: unknown): CanonicalValue {
  if (value === null || typeof value === "boolean" || typeof value === "string") {
    return value;
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new Error("Non-finite number is not supported in canonical serialization.");
    }
    return normalizeNumber(value);
  }

  if (Array.isArray(value)) {
    return value.map((item) => canonicalize(item));
  }

  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const sortedKeys = Object.keys(record).sort();
    const normalized: { [key: string]: CanonicalValue } = {};
    for (const key of sortedKeys) {
      normalized[key] = canonicalize(record[key]);
    }
    return normalized;
  }

  throw new Error("Unsupported value type in canonical serialization.");
}

export function canonicalStringify(value: unknown): string {
  return JSON.stringify(canonicalize(value));
}
