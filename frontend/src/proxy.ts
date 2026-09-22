import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

import { browserSecurityHeaders } from '@/lib/security-headers';

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (/^\/(api|health)(\/|$)/.test(pathname)) {
    // next.config rewrites are frozen into standalone builds. Resolve the
    // deployment origin here so the same image can run against another API.
    let target: URL;
    try {
      target = new URL(process.env.BACKEND_ORIGIN ?? 'http://127.0.0.1:8111');
      if (
        !['http:', 'https:'].includes(target.protocol) ||
        target.username ||
        target.password ||
        target.pathname !== '/' ||
        target.search ||
        target.hash
      ) {
        throw new Error('Invalid backend origin');
      }
    } catch {
      return NextResponse.json(
        {
          code: 'service_unavailable',
          message: 'API routing is unavailable.',
          data: null,
        },
        { status: 503 },
      );
    }
    // FastAPI routes are slashless. Avoid its redirect leaking the internal
    // host, including when a browser retained a previous slash redirect.
    target.pathname = pathname.replace(/\/+$/, '');
    target.search = search;
    // Overwrite caller-supplied forwarding hosts before the trusted API hop.
    const headers = new Headers(request.headers);
    headers.set(
      'x-forwarded-host',
      request.headers.get('host') ?? request.nextUrl.host,
    );
    const forwardedProto = request.headers.get('x-forwarded-proto');
    headers.set(
      'x-forwarded-proto',
      forwardedProto === 'https'
        ? 'https'
        : request.nextUrl.protocol.slice(0, -1),
    );
    return NextResponse.rewrite(target, { request: { headers } });
  }
  const response = NextResponse.next();
  for (const [name, value] of browserSecurityHeaders({
    production: process.env.NODE_ENV === 'production',
    storageEndpoint: process.env.MINIO_PUBLIC_ENDPOINT,
    storageSecure: process.env.MINIO_PUBLIC_SECURE === 'true',
    localStorageEndpoint: process.env.MINIO_LOCAL_BROWSER_ENDPOINT,
    localStorageSecure: process.env.MINIO_LOCAL_BROWSER_SECURE === 'true',
  })) {
    response.headers.set(name, value);
  }
  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
