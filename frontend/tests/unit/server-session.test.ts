import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/request-error';

const runtime = vi.hoisted(() => ({
  token: undefined as string | undefined,
  get: vi.fn(),
  user: vi.fn(),
}));
vi.mock('server-only', () => ({}));
vi.mock('next/headers', () => ({
  cookies: async () => ({ get: runtime.get }),
}));
vi.mock('@/api/auth', () => ({ getCurrentUser: runtime.user }));

import { readServerSession } from '@/lib/server-session';

const projection: API.UserResponse = {
  id: 'owner-a',
  username: 'alice',
  email: 'alice@example.com',
  role: 'user',
  created_at: '2026-09-22T00:00:00Z',
  updated_at: '2026-09-22T00:00:00Z',
};

beforeEach(() => {
  runtime.token = undefined;
  runtime.get
    .mockReset()
    .mockImplementation(() =>
      runtime.token ? { value: runtime.token } : undefined,
    );
  runtime.user.mockReset();
  vi.stubEnv('BACKEND_ORIGIN', 'http://api:8111');
});
afterEach(() => vi.unstubAllEnvs());

it('renders anonymous requests without contacting the backend or trusting a malformed Cookie', async () => {
  expect(await readServerSession()).toBeNull();
  runtime.token = 'invalid-token';
  expect(await readServerSession()).toBeNull();
  expect(runtime.user).not.toHaveBeenCalled();
});

it('uses only the configured Cookie with a bounded no-store generated API call', async () => {
  runtime.token = 'a'.repeat(43);
  vi.stubEnv('AUTH_WEB_COOKIE_NAME', 'custom_web_session');
  runtime.user.mockResolvedValue(projection);
  expect(await readServerSession()).toEqual(projection);
  expect(runtime.get).toHaveBeenCalledWith('custom_web_session');
  expect(runtime.user).toHaveBeenCalledWith({
    baseURL: 'http://api:8111',
    headers: { Cookie: `custom_web_session=${runtime.token}` },
    adapter: 'fetch',
    fetchOptions: { cache: 'no-store', redirect: 'error' },
    timeout: 2_000,
    signal: expect.any(AbortSignal),
  });
  expect(JSON.stringify(await readServerSession())).not.toContain(
    runtime.token,
  );
});

it.each([
  [new ApiError(401, 'unauthenticated', '', ''), null],
  [new ApiError(503, 'service_unavailable', '', ''), undefined],
  [new ApiError(401, 'provider_auth_required', '', ''), undefined],
  [new Error('connection closed'), undefined],
])(
  'separates confirmed anonymity from dependency failures: %s',
  async (error, expected) => {
    runtime.token = 'a'.repeat(43);
    runtime.user.mockRejectedValue(error);
    expect(await readServerSession()).toBe(expected);
  },
);

it('does not share credentials or projections between concurrent request scopes', async () => {
  const tokens = ['a'.repeat(43), 'b'.repeat(43)];
  runtime.get
    .mockImplementationOnce(() => ({ value: tokens[0] }))
    .mockImplementationOnce(() => ({ value: tokens[1] }));
  runtime.user.mockImplementation(async ({ headers }) => ({
    ...projection,
    id: headers.Cookie.endsWith(tokens[0]) ? 'owner-a' : 'owner-b',
  }));
  const [first, second] = await Promise.all([
    readServerSession(),
    readServerSession(),
  ]);
  expect(first?.id).toBe('owner-a');
  expect(second?.id).toBe('owner-b');
  expect(runtime.user).toHaveBeenCalledTimes(2);
});

it('does not forward a session to a malformed deployment target', async () => {
  runtime.token = 'a'.repeat(43);
  vi.stubEnv('BACKEND_ORIGIN', 'https://bad.example/path');
  expect(await readServerSession()).toBeUndefined();
  expect(runtime.user).not.toHaveBeenCalled();
});
