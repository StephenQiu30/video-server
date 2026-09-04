import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

import { browserSecurityHeaders } from '@/lib/security-headers';
import { canonicalSecureDeploymentRedirect } from '@/lib/site';

export function proxy(request: NextRequest) {
  const appEnvironment = process.env.APP_ENV;
  const redirectUrl = canonicalSecureDeploymentRedirect(
    request.nextUrl,
    request.headers.get('host'),
    request.headers.get('x-forwarded-proto'),
    process.env.SITE_URL,
    appEnvironment === 'staging' || appEnvironment === 'production',
  );
  const response = redirectUrl
    ? NextResponse.redirect(redirectUrl, 307)
    : NextResponse.next();
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
  matcher: [
    '/((?!api(?:/|$)|health(?:/|$)|_next/static|_next/image|favicon.ico).*)',
  ],
};
