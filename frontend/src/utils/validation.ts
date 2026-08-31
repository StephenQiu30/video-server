export const URL_MESSAGE = '请输入有效的公开 HTTP(S) 视频地址。';

const HTTP_URL_PATTERN = /https?:\/\/[^\s]+/giu;
const TRAILING_URL_CHARACTERS =
  /[.,!?;:，。！？；：、)）】》〉」』〕］｝\]}>'"”’]+$/u;

function parsePublicUrl(value: string): string | null {
  const candidate = value.replace(TRAILING_URL_CHARACTERS, '');
  if (!candidate) return null;

  try {
    const parsed = new URL(candidate);
    if (
      !['http:', 'https:'].includes(parsed.protocol) ||
      parsed.username ||
      parsed.password
    ) {
      return null;
    }
  } catch {
    return null;
  }

  return candidate;
}

/**
 * Normalize a direct URL or a platform share message containing one URL.
 * Share messages are accepted only when they contain exactly one HTTP(S) URL.
 */
export function normalizeMediaUrl(value: string): string | null {
  const input = value.trim();
  if (!input) return null;

  const matches = input.match(HTTP_URL_PATTERN) ?? [];
  if (matches.length > 1) return null;

  return parsePublicUrl(matches[0] ?? input);
}

export function validateMediaUrl(value: string): string | null {
  return normalizeMediaUrl(value) ? null : URL_MESSAGE;
}
