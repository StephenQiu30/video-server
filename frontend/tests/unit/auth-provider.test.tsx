import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider, useAuth } from '@/components/auth/auth-provider';
import { ApiError } from '@/lib/request-error';
import { sessionGeneration } from '@/lib/session-events';

const runtime = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  logout: vi.fn(),
  resetSocket: vi.fn(),
}));

vi.mock('@/lib/task-socket', () => ({
  taskSocket: { reset: runtime.resetSocket },
}));

const user = {
  created_at: '2026-08-09T10:00:00Z',
  email: 'user@example.com',
  id: '11111111-1111-4111-8111-111111111111',
  role: 'user' as const,
  updated_at: '2026-08-09T10:00:00Z',
  username: 'video_user',
};

class TestChannel {
  static instances: TestChannel[] = [];
  onmessage: ((event: { data: unknown }) => void) | null = null;
  postMessage = vi.fn();
  close = vi.fn();
  constructor() {
    TestChannel.instances.push(this);
  }
}

describe('AuthProvider', () => {
  beforeEach(() => {
    TestChannel.instances = [];
    vi.stubGlobal('BroadcastChannel', TestChannel);
    runtime.getCurrentUser.mockReset();
    runtime.logout.mockReset();
    runtime.resetSocket.mockReset();
    window.history.replaceState({}, '', '/');
    vi.unstubAllEnvs();
  });

  afterEach(() => vi.unstubAllGlobals());

  it('does not invalidate an in-flight login when anonymous session discovery returns 401', async () => {
    const generation = sessionGeneration();
    runtime.getCurrentUser.mockRejectedValueOnce(
      new ApiError(401, 'unauthenticated', '', 'Sign in'),
    );
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveAttribute(
        'data-session-status',
        'anonymous',
      ),
    );
    expect(sessionGeneration()).toBe(generation);
  });

  it('restores the current cookie session and exposes it through useAuth', async () => {
    runtime.getCurrentUser.mockResolvedValue(user);
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    expect(screen.getByRole('status')).toHaveAttribute(
      'data-auth-state',
      'loading',
    );
    expect(await screen.findByTestId('auth-user')).toHaveAttribute(
      'data-user',
      'video_user',
    );
    expect(screen.getByRole('status')).toHaveAttribute(
      'data-auth-state',
      'ready',
    );
    expect(runtime.getCurrentUser).toHaveBeenCalledOnce();
  });

  it('restores the real session even when the removed design query is present', async () => {
    vi.stubEnv('NODE_ENV', 'development');
    runtime.getCurrentUser.mockResolvedValue(user);
    window.history.replaceState({}, '', '/?design=inspection');
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    expect(await screen.findByTestId('auth-user')).toHaveAttribute(
      'data-user',
      'video_user',
    );
    expect(screen.getByRole('status')).toHaveAttribute(
      'data-auth-state',
      'ready',
    );
    expect(runtime.getCurrentUser).toHaveBeenCalledOnce();
  });

  it('masks private identity and retains retry state until logout is confirmed', async () => {
    runtime.getCurrentUser.mockResolvedValue(user);
    runtime.logout.mockRejectedValue(new Error('stale session'));
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await screen.findByTestId('auth-user');

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '退出' }));
    });

    await waitFor(() =>
      expect(screen.getByTestId('auth-user')).toHaveAttribute(
        'data-user',
        'guest',
      ),
    );
    expect(screen.getByRole('status')).toHaveAttribute(
      'data-session-status',
      'unknown',
    );
    runtime.logout.mockResolvedValueOnce(undefined);
    fireEvent.click(screen.getByRole('button', { name: '刷新用户' }));
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveAttribute(
        'data-session-status',
        'anonymous',
      ),
    );
    expect(runtime.logout).toHaveBeenCalledTimes(2);
    expect(runtime.resetSocket).toHaveBeenCalled();
  });

  it('does not interpret an initial network failure as an anonymous session', async () => {
    runtime.getCurrentUser.mockRejectedValue(
      new ApiError(503, 'unavailable', '', '暂不可用'),
    );
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveAttribute(
        'data-auth-state',
        'ready',
      ),
    );
    expect(screen.getByRole('status')).toHaveAttribute(
      'data-session-status',
      'unknown',
    );
    expect(screen.getByRole('status')).toHaveAttribute(
      'data-session-error',
      'true',
    );
  });

  it('does not reset task subscriptions for the same authenticated identity', async () => {
    runtime.getCurrentUser.mockResolvedValue(user);
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await screen.findByTestId('auth-user');
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveAttribute(
        'data-auth-state',
        'ready',
      ),
    );
    runtime.resetSocket.mockClear();
    fireEvent.click(screen.getByRole('button', { name: '刷新用户' }));
    await waitFor(() =>
      expect(runtime.getCurrentUser).toHaveBeenCalledTimes(2),
    );
    expect(runtime.resetSocket).not.toHaveBeenCalled();
  });

  it('ignores session restoration that arrives after a new login', async () => {
    let resolve!: (value: typeof user) => void;
    runtime.getCurrentUser.mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    fireEvent.click(screen.getByRole('button', { name: '另一账号登录' }));
    resolve(user);
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveAttribute(
        'data-auth-state',
        'ready',
      ),
    );
    expect(screen.getByTestId('auth-user')).toHaveAttribute(
      'data-user',
      'new_user',
    );
  });

  it('masks an old identity on cross-tab change and does not rebroadcast reads', async () => {
    runtime.getCurrentUser.mockResolvedValueOnce(user);
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId('auth-user')).toHaveAttribute(
        'data-user',
        'video_user',
      ),
    );
    let resolve!: (value: typeof user) => void;
    runtime.getCurrentUser.mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    const channel = TestChannel.instances.at(-1);
    if (!channel) throw new Error('Expected identity channel');
    act(() => channel.onmessage?.({ data: { type: 'identity-changed' } }));
    expect(screen.getByTestId('auth-user')).toHaveAttribute(
      'data-user',
      'guest',
    );
    expect(screen.getByRole('status')).toHaveAttribute(
      'data-session-status',
      'unknown',
    );
    await act(async () =>
      resolve({ ...user, id: 'other-user', username: 'other_user' }),
    );
    expect(screen.getByTestId('auth-user')).toHaveAttribute(
      'data-user',
      'other_user',
    );
    expect(channel.postMessage).not.toHaveBeenCalled();
    runtime.getCurrentUser.mockRejectedValueOnce(
      new ApiError(401, 'unauthenticated', '', 'Sign in'),
    );
    await act(async () =>
      channel.onmessage?.({ data: { type: 'identity-changed' } }),
    );
    expect(screen.getByRole('status')).toHaveAttribute(
      'data-session-status',
      'anonymous',
    );
    expect(channel.postMessage).not.toHaveBeenCalled();
  });

  it('confirms logout even when another tab starts logout at the same time', async () => {
    runtime.getCurrentUser.mockResolvedValue(user);
    let resolve!: () => void;
    runtime.logout.mockImplementationOnce(
      () =>
        new Promise<void>((done) => {
          resolve = done;
        }),
    );
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId('auth-user')).toHaveAttribute(
        'data-user',
        'video_user',
      ),
    );
    fireEvent.click(screen.getByRole('button', { name: '退出' }));
    const channel = TestChannel.instances.at(-1);
    if (!channel) throw new Error('Expected identity channel');
    act(() => channel.onmessage?.({ data: { type: 'logout-started' } }));
    await act(async () => resolve());
    expect(screen.getByRole('status')).toHaveAttribute(
      'data-session-status',
      'anonymous',
    );
    expect(channel.postMessage).toHaveBeenLastCalledWith({
      type: 'identity-changed',
    });
  });

  it('keeps the current page authenticated during a failed background refresh', async () => {
    runtime.getCurrentUser
      .mockResolvedValueOnce(user)
      .mockRejectedValueOnce(
        new ApiError(0, 'request_failed', '网络错误', '断网'),
      );
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await screen.findByTestId('auth-user');

    fireEvent.click(screen.getByRole('button', { name: '刷新用户' }));

    await waitFor(() =>
      expect(runtime.getCurrentUser).toHaveBeenCalledTimes(2),
    );
    expect(screen.getByTestId('auth-user')).toHaveAttribute(
      'data-user',
      'video_user',
    );
    expect(screen.getByRole('status')).toHaveAttribute(
      'data-auth-state',
      'ready',
    );
  });
});

function AuthProbe() {
  const { loading, refreshUser, signOut, user, status, sessionError, setUser } =
    useAuth();
  return (
    <div>
      <p
        data-auth-state={loading ? 'loading' : 'ready'}
        data-session-status={status}
        data-session-error={Boolean(sessionError)}
        role="status"
      />
      <p data-testid="auth-user" data-user={user?.username ?? 'guest'} />
      <button
        onClick={() => void signOut().catch(() => undefined)}
        type="button"
      >
        退出
      </button>
      <button
        onClick={() =>
          setUser({
            ...user,
            id: 'new-user',
            username: 'new_user',
          } as API.UserResponse)
        }
        type="button"
      >
        另一账号登录
      </button>
      <button onClick={() => void refreshUser()} type="button">
        刷新用户
      </button>
    </div>
  );
}

vi.mock('@/api/auth', async (original) => ({
  ...(await original<typeof import('@/api/auth')>()),
  getCurrentUser: runtime.getCurrentUser,
  logoutUser: runtime.logout,
}));
