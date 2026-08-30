import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

import { browserSecurityHeaders } from '@/lib/security-headers';

export function proxy(_request: NextRequest) {
  const response = NextResponse.next();
  for (const [name, value] of browserSecurityHeaders({
    production: process.env.NODE_ENV === 'production',
    storageEndpoint: process.env.MINIO_PUBLIC_ENDPOINT,
    storageSecure: process.env.MINIO_PUBLIC_SECURE === 'true',
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
