export const AU_IN_METERS = 149_597_870_700;
export const YEAR_IN_SECONDS = 31_557_600;

export function clamp(value: number, min: number, max: number): number {
  if (value < min) {
    return min;
  }
  if (value > max) {
    return max;
  }
  return value;
}

export function roundTo(value: number, digits: number): number {
  const multiplier = 10 ** digits;
  const rounded = Math.round(value * multiplier) / multiplier;
  if (Object.is(rounded, -0)) {
    return 0;
  }
  return rounded;
}
