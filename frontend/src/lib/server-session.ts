import 'server-only';

import { cookies } from 'next/headers';
import { cache } from 'react';
import { getCurrentUser } from '@/api/auth';
import { backendOrigin } from '@/lib/backend-origin';
import { ApiError } from '@/lib/request-error';

// React cache deduplicates within one server render, never between requests.
// null is confirmed anonymous; undefined is unavailable and must not log out.
// Only the API's user projection crosses the server/client boundary.
export const readServerSession = cache(
  async (): Promise<API.UserResponse | null | undefined> => {
    const name = process.env.AUTH_WEB_COOKIE_NAME ?? 'video_web_session';
    const token = (await cookies()).get(name)?.value;
    if (!token || !/^[A-Za-z0-9_-]{43}$/.test(token)) return null;
    try {
      return await getCurrentUser({
        baseURL: backendOrigin().origin,
        headers: { Cookie: `${name}=${token}` },
        adapter: 'fetch',
        fetchOptions: { cache: 'no-store', redirect: 'error' },
        timeout: 2_000,
        signal: AbortSignal.timeout(2_000),
      });
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.status === 401 &&
        error.code === 'unauthenticated'
      )
        return null;
      return undefined;
    }
  },
);
