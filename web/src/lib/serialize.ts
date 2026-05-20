import * as serializeModule from "../../../sim/public/runtime";

type SerializeExports = {
  canonicalStringify: (value: unknown) => string;
};

function resolveSerializer(module: Record<string, unknown>): SerializeExports {
  const asAny = module as Record<string, any>;
  const candidates = [asAny, asAny.default, asAny["module.exports"]];

  for (const candidate of candidates) {
    if (!candidate) {
      continue;
    }
    if (typeof candidate.canonicalStringify === "function") {
      return candidate as SerializeExports;
    }
  }

  throw new Error("Unable to resolve canonicalStringify export from sim/public/runtime.");
}

const serializer = resolveSerializer(serializeModule as unknown as Record<string, unknown>);

export const canonicalStringify = serializer.canonicalStringify;
