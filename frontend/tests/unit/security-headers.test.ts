import { describe, expect, it } from 'vitest';

import {
  browserSecurityHeaders,
  resolveStorageOrigin,
} from '@/lib/security-headers';

describe('browser security headers', () => {
  it('allows only the configured browser storage origin in production', () => {
    const headers = new Map(
      browserSecurityHeaders({
        production: true,
        storageEndpoint: 'storage.example.com:9443',
        storageSecure: true,
      }),
    );

    expect(headers.get('Content-Security-Policy')).toContain(
      "connect-src 'self' https://storage.example.com:9443",
    );
    expect(headers.get('Content-Security-Policy')).toContain(
      "object-src 'none'",
    );
    expect(headers.get('Strict-Transport-Security')).toContain(
      'max-age=31536000',
    );
    expect(headers.get('X-Frame-Options')).toBe('DENY');
  });

  it('fails closed for malformed storage endpoints', () => {
    expect(resolveStorageOrigin('https://attacker.example/path', true)).toBe(
      '',
    );
    const headers = new Map(
      browserSecurityHeaders({
        production: true,
        storageEndpoint: 'https://attacker.example/path',
      }),
    );

    expect(headers.get('Content-Security-Policy')).toContain(
      "connect-src 'self';",
    );
    expect(headers.get('Content-Security-Policy')).not.toContain(
      'attacker.example',
    );
  });
});
