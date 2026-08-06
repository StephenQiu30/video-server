export function createIdempotencyKey(): string {
  return globalThis.crypto.randomUUID();
}
