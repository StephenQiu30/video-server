export function validateVideoUrl(value: string): string | null {
  const input = value.trim();
  if (!input) return '请输入视频链接';
  if (input.length > 2048) return '视频链接过长';
  try {
    const url = new URL(input);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      return '仅支持 HTTP 或 HTTPS 视频链接';
    }
    if (url.username || url.password) return '视频链接不能包含账号或密码';
    return null;
  } catch {
    return '请输入有效的视频链接';
  }
}
