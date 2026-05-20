export async function sha256Hex(input: string): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new Error("Web Crypto API is unavailable in this environment.");
  }
  const encoded = new TextEncoder().encode(input);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", encoded);
  const bytes = Array.from(new Uint8Array(digest));
  return bytes.map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
