export interface SeededRng {
  next(): number;
}

function hashSeed(seed: string | number): number {
  const source = String(seed);
  let state = 2166136261;
  for (let index = 0; index < source.length; index += 1) {
    state ^= source.charCodeAt(index);
    state = Math.imul(state, 16777619);
  }
  return state >>> 0;
}

export function createSeededRng(seed: string | number): SeededRng {
  let state = hashSeed(seed) || 0x6d2b79f5;
  return {
    next(): number {
      state |= 0;
      state = (state + 0x6d2b79f5) | 0;
      let value = Math.imul(state ^ (state >>> 15), 1 | state);
      value ^= value + Math.imul(value ^ (value >>> 7), 61 | value);
      return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
    },
  };
}
