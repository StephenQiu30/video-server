const URL_MESSAGE = '请输入有效的公开 HTTP(S) 视频地址。';

export function validateMediaUrl(value: string): string | null {
  if (!value) {
    return URL_MESSAGE;
  }
  try {
    const parsed = new URL(value);
    if (
      !['http:', 'https:'].includes(parsed.protocol) ||
      parsed.username ||
      parsed.password
    ) {
      return URL_MESSAGE;
    }
  } catch {
    return URL_MESSAGE;
  }
  return null;
}
