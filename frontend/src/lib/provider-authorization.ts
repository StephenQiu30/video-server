import { ApiError } from '@/lib/request-error';

export type ProviderAuthorizationTarget = {
  key: 'youtube' | 'douyin' | 'reddit' | 'wechat_channels';
  displayName: string;
  accessPolicy: API.ProviderAccessPolicy;
  authorizationAction: API.ProviderAuthorizationAction;
};

const AUTHORIZATION_ERROR_CODES = new Set([
  'provider_auth_required',
  'provider_session_expired',
]);

const PROVIDER_TARGETS: readonly ProviderAuthorizationTarget[] = [
  {
    key: 'youtube',
    displayName: 'YouTube',
    accessPolicy: 'operator_public',
    authorizationAction: 'managed_session',
  },
  {
    key: 'douyin',
    displayName: '抖音',
    accessPolicy: 'operator_public',
    authorizationAction: 'managed_session',
  },
  {
    key: 'reddit',
    displayName: 'Reddit',
    accessPolicy: 'operator_public',
    authorizationAction: 'managed_session',
  },
  {
    key: 'wechat_channels',
    displayName: '微信视频号',
    accessPolicy: 'operator_public',
    authorizationAction: 'managed_session',
  },
];

const BROWSER_BRIDGE_DOMAINS = {
  youtube: ['youtube.com', 'youtu.be'],
  douyin: ['douyin.com', 'iesdouyin.com'],
  xiaohongshu: ['xiaohongshu.com'],
  x: ['x.com', 'twitter.com'],
  instagram: ['instagram.com'],
  facebook: ['facebook.com'],
  reddit: ['reddit.com', 'redd.it'],
  pinterest: ['pinterest.com'],
} satisfies Record<string, string[]>;

export function providerAuthorizationTarget(
  input: string,
  errorCode: string,
): ProviderAuthorizationTarget | null {
  if (!AUTHORIZATION_ERROR_CODES.has(errorCode)) return null;
  const hostname = extractHostname(input);
  if (!hostname) return null;

  const target = PROVIDER_TARGETS.find((candidate) => {
    const domains = {
      ...BROWSER_BRIDGE_DOMAINS,
      wechat_channels: ['weixin.qq.com'],
    } satisfies Record<ProviderAuthorizationTarget['key'], string[]>;
    return isHost(hostname, domains[candidate.key]);
  });
  return target ?? null;
}

/** Ask the installed local browser connector to refresh one provider snapshot. */
export function requestBrowserProviderSync(
  providerKey: string,
  timeoutMs = 5_000,
): Promise<void> {
  if (typeof window === 'undefined') return Promise.resolve();
  const requestId = crypto.randomUUID();
  return new Promise((resolve, reject) => {
    const onMessage = (event: MessageEvent) => {
      if (event.source !== window || event.origin !== window.location.origin)
        return;
      if (
        event.data?.type !== 'framefetch:provider-sync:result' ||
        event.data?.requestId !== requestId ||
        event.data?.provider !== providerKey
      )
        return;
      cleanup();
      if (event.data.ok === true && typeof event.data.revision === 'string')
        resolve();
      else
        reject(
          new ApiError(
            0,
            'browser_sync_failed',
            '浏览器会话同步失败',
            '浏览器连接器未能同步当前平台会话。',
          ),
        );
    };
    const timer = window.setTimeout(() => {
      cleanup();
      reject(
        new ApiError(
          0,
          'browser_sync_failed',
          '浏览器会话同步失败',
          '未检测到浏览器连接器响应。',
        ),
      );
    }, timeoutMs);
    const cleanup = () => {
      window.clearTimeout(timer);
      window.removeEventListener('message', onMessage);
    };
    window.addEventListener('message', onMessage);
    window.postMessage(
      {
        type: 'framefetch:provider-sync',
        provider: providerKey,
        requestId,
      },
      window.location.origin,
    );
  });
}

function extractHostname(input: string): string | null {
  const candidate = input.match(/https?:\/\/[^\s]+/iu)?.[0] ?? input.trim();
  try {
    return new URL(candidate.replace(/[),，。]+$/u, '')).hostname.toLowerCase();
  } catch {
    return null;
  }
}

function isHost(hostname: string, domains: string[]): boolean {
  return domains.some(
    (domain) => hostname === domain || hostname.endsWith(`.${domain}`),
  );
}
