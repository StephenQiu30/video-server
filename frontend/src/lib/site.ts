const LOCAL_SITE_URL = 'http://127.0.0.1:8101';

export function resolveSiteUrl(value: string | undefined): URL {
  const candidate = value?.trim();
  if (!candidate) return new URL(LOCAL_SITE_URL);

  try {
    const url = new URL(candidate);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      throw new Error('unsupported protocol');
    }

    url.pathname = '/';
    url.search = '';
    url.hash = '';
    return url;
  } catch (error) {
    throw new Error('SITE_URL must be an absolute HTTP(S) URL', {
      cause: error,
    });
  }
}

export function canonicalSecureDeploymentRedirect(
  requestUrl: URL,
  requestHost: string | null,
  forwardedProtocol: string | null,
  configuredSiteUrl: string | undefined,
  secureDeployment: boolean,
): URL | null {
  if (!secureDeployment) return null;

  const canonicalUrl = resolveSiteUrl(configuredSiteUrl);
  if (canonicalUrl.protocol !== 'https:') {
    throw new Error('SITE_URL must use HTTPS in secure deployments');
  }

  const host = (requestHost ?? requestUrl.host).trim().toLowerCase();
  const protocol = (forwardedProtocol ?? requestUrl.protocol)
    .split(',', 1)[0]
    .trim()
    .toLowerCase()
    .replace(/:$/, '');
  if (host === canonicalUrl.host.toLowerCase() && protocol === 'https') {
    return null;
  }

  const redirectUrl = new URL(canonicalUrl);
  redirectUrl.pathname = requestUrl.pathname;
  redirectUrl.search = requestUrl.search;
  return redirectUrl;
}

export const siteConfig = {
  name: '帧取 FrameFetch',
  shortName: '帧取',
  title: '帧取 FrameFetch — 开源自托管的视频下载与 AI 分析平台',
  description:
    '帧取 FrameFetch 是 MIT 开源、可自托管的公开视频下载、剧本处理与 AI 视频分析平台，基于 FastAPI、Next.js、FFmpeg 与 yt-dlp 构建。',
  englishDescription:
    'FrameFetch is a self-hosted open-source workflow for authorized public video downloads, screenplay processing, and AI video analysis.',
  repositoryUrl: 'https://github.com/StephenQiu30/video-server',
  mobileRepositoryUrl: 'https://github.com/StephenQiu30/video-app',
  licenseUrl: 'https://github.com/StephenQiu30/video-server/blob/main/LICENSE',
} as const;

export const socialPalette = {
  background: '#0a0a0a',
  foreground: '#fafafa',
  muted: '#a3a3a3',
} as const;

export const siteUrl = resolveSiteUrl(process.env.SITE_URL);

export function absoluteUrl(path = '/'): string {
  return new URL(path, siteUrl).toString();
}
