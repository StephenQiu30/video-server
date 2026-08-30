type SecurityHeaderOptions = {
  production: boolean;
  storageEndpoint?: string;
  storageSecure?: boolean;
};

export function browserSecurityHeaders({
  production,
  storageEndpoint,
  storageSecure = false,
}: SecurityHeaderOptions): ReadonlyArray<readonly [string, string]> {
  const storageOrigin = resolveStorageOrigin(storageEndpoint, storageSecure);
  const connectSources = ["'self'", storageOrigin];
  const mediaSources = ["'self'", storageOrigin];
  if (!production) connectSources.push('ws:', 'wss:');
  const scriptSources = ["'self'", "'unsafe-inline'"];
  if (!production) scriptSources.push("'unsafe-eval'");
  const csp = [
    "default-src 'self'",
    `script-src ${scriptSources.join(' ')}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    `connect-src ${connectSources.filter(Boolean).join(' ')}`,
    `media-src ${mediaSources.filter(Boolean).join(' ')}`,
    "font-src 'self' data:",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ');
  const headers: Array<readonly [string, string]> = [
    ['Content-Security-Policy', csp],
    [
      'Permissions-Policy',
      'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
    ],
    ['Referrer-Policy', 'strict-origin-when-cross-origin'],
    ['X-Content-Type-Options', 'nosniff'],
    ['X-Frame-Options', 'DENY'],
  ];
  if (production) {
    headers.push([
      'Strict-Transport-Security',
      'max-age=31536000; includeSubDomains',
    ]);
  }
  return headers;
}

export function resolveStorageOrigin(
  endpoint = '127.0.0.1:19190',
  secure = false,
): string {
  const value = endpoint.trim();
  if (!value) return '';
  try {
    const parsed = new URL(`${secure ? 'https' : 'http'}://${value}`);
    if (
      !parsed.hostname ||
      parsed.username ||
      parsed.password ||
      parsed.pathname !== '/' ||
      parsed.search ||
      parsed.hash
    ) {
      return '';
    }
    return parsed.origin;
  } catch {
    return '';
  }
}
