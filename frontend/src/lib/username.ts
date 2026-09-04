export const USERNAME_HELP =
  '2–32 个字符，仅支持字母、数字、中文以及 _-. 字符。';

export type UsernameValidationError =
  | 'required'
  | 'too_short'
  | 'too_long'
  | 'unsupported_characters';

export function normalizeUsername(value: string): string {
  return value.normalize('NFKC').trim();
}

export function usernameLength(value: string): number {
  return Array.from(normalizeUsername(value)).length;
}

export function validateUsername(
  value: string,
): UsernameValidationError | null {
  const normalized = normalizeUsername(value);
  if (!normalized) return 'required';
  const length = usernameLength(normalized);
  if (length < 2) return 'too_short';
  if (length > 32) return 'too_long';
  return /^[\p{L}\p{N}_.-]+$/u.test(normalized)
    ? null
    : 'unsupported_characters';
}
