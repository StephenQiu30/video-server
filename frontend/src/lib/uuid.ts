const UUID_BYTE_LENGTH = 16;
const UUID_VERSION_INDEX = 6;
const UUID_VARIANT_INDEX = 8;
const UUID_VERSION_MASK = 0x0f;
const UUID_VERSION_FOUR = 0x40;
const UUID_VARIANT_MASK = 0x3f;
const UUID_VARIANT_RFC_9562 = 0x80;

/** Generate an RFC 9562 UUID without requiring a secure browser context. */
export function createUuid(): string {
  const bytes = globalThis.crypto.getRandomValues(
    new Uint8Array(UUID_BYTE_LENGTH),
  );
  bytes[UUID_VERSION_INDEX] =
    (bytes[UUID_VERSION_INDEX] & UUID_VERSION_MASK) | UUID_VERSION_FOUR;
  bytes[UUID_VARIANT_INDEX] =
    (bytes[UUID_VARIANT_INDEX] & UUID_VARIANT_MASK) | UUID_VARIANT_RFC_9562;

  const hex = Array.from(bytes, (value) =>
    value.toString(16).padStart(2, '0'),
  ).join('');
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20),
  ].join('-');
}
