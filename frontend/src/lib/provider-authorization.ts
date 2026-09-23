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

const PROVIDER_DOMAINS = {
  youtube: ['youtube.com', 'youtu.be'],
  douyin: ['douyin.com', 'iesdouyin.com'],
  reddit: ['reddit.com', 'redd.it'],
  wechat_channels: ['weixin.qq.com'],
} satisfies Record<ProviderAuthorizationTarget['key'], string[]>;

export function providerAuthorizationTarget(
  input: string,
  errorCode: string,
): ProviderAuthorizationTarget | null {
  if (!AUTHORIZATION_ERROR_CODES.has(errorCode)) return null;
  const hostname = extractHostname(input);
  if (!hostname) return null;
  return (
    PROVIDER_TARGETS.find((candidate) =>
      isHost(hostname, PROVIDER_DOMAINS[candidate.key]),
    ) ?? null
  );
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
