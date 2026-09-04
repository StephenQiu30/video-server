import type { NextRequest } from 'next/server';

const TARGET_HEADER = 'X-FrameFetch-Upload-Target';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function PUT(request: NextRequest) {
  const target = resolveTarget(request.headers.get(TARGET_HEADER));
  if (!target) {
    return new Response('Invalid upload target', { status: 400 });
  }

  const headers = new Headers();
  const contentType = request.headers.get('content-type');
  const contentLength = request.headers.get('content-length');
  if (contentType) headers.set('content-type', contentType);
  if (contentLength) headers.set('content-length', contentLength);

  try {
    const upstream = await fetch(target, {
      body: request.body,
      cache: 'no-store',
      duplex: 'half',
      headers,
      method: 'PUT',
      redirect: 'error',
      signal: request.signal,
    } as RequestInit & { duplex: 'half' });
    const responseHeaders = new Headers({ 'Cache-Control': 'no-store' });
    const etag = upstream.headers.get('etag');
    if (etag) responseHeaders.set('ETag', etag);
    return new Response(null, {
      headers: responseHeaders,
      status: upstream.status,
    });
  } catch {
    return new Response('Upload storage unavailable', { status: 502 });
  }
}

export function resolveTarget(value: string | null): URL | null {
  const expected = storageOrigin();
  if (!value || !expected) return null;
  try {
    const target = new URL(value);
    if (
      target.origin !== expected ||
      target.username ||
      target.password ||
      target.hash ||
      target.searchParams.get('X-Amz-Algorithm') !== 'AWS4-HMAC-SHA256' ||
      !target.searchParams.has('X-Amz-Signature')
    ) {
      return null;
    }
    return target;
  } catch {
    return null;
  }
}

function storageOrigin(): string | null {
  const endpoint = process.env.MINIO_PUBLIC_ENDPOINT?.trim();
  if (!endpoint) return null;
  try {
    const origin = new URL(
      `${process.env.MINIO_PUBLIC_SECURE === 'true' ? 'https' : 'http'}://${endpoint}`,
    );
    if (
      !origin.hostname ||
      origin.username ||
      origin.password ||
      origin.pathname !== '/' ||
      origin.search ||
      origin.hash
    ) {
      return null;
    }
    return origin.origin;
  } catch {
    return null;
  }
}
