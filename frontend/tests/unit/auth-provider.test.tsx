import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider, useAuth } from '@/components/auth/auth-provider';
import { ApiError } from '@/lib/request-error';

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

describe('AuthProvider', () => {
  beforeEach(() => {
    runtime.getCurrentUser.mockReset();
    runtime.logout.mockReset();
    runtime.resetSocket.mockReset();
    window.history.replaceState({}, '', '/');
    vi.unstubAllEnvs();
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

  it('clears local identity even when server logout fails', async () => {
    runtime.getCurrentUser.mockResolvedValue(user);
    runtime.logout.mockRejectedValue(new Error('stale session'));
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await screen.findByTestId('auth-user');

    fireEvent.click(screen.getByRole('button', { name: '退出' }));

    await waitFor(() =>
      expect(screen.getByTestId('auth-user')).toHaveAttribute(
        'data-user',
        'guest',
      ),
    );
    expect(runtime.logout).toHaveBeenCalledOnce();
    expect(runtime.resetSocket).toHaveBeenCalled();
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
  const { loading, refreshUser, signOut, user } = useAuth();
  return (
    <div>
      <p data-auth-state={loading ? 'loading' : 'ready'} role="status" />
      <p data-testid="auth-user" data-user={user?.username ?? 'guest'} />
      <button onClick={() => void signOut()} type="button">
        退出
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
