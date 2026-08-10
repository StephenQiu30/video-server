import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider, useAuth } from '@/components/auth-provider';

const runtime = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  logout: vi.fn(),
  resetSocket: vi.fn(),
}));

vi.mock('@/services/auth', () => ({
  getCurrentUser: runtime.getCurrentUser,
  logout: runtime.logout,
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

    expect(screen.getByRole('status')).toHaveTextContent('loading');
    expect(await screen.findByText('video_user')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('ready');
    expect(runtime.getCurrentUser).toHaveBeenCalledOnce();
  });

  it('uses the built-in user for development design inspection without a request', async () => {
    vi.stubEnv('NODE_ENV', 'development');
    window.history.replaceState({}, '', '/?design=inspection');
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    expect(await screen.findByText('设计预览')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('ready');
    expect(runtime.getCurrentUser).not.toHaveBeenCalled();
  });

  it('clears local identity even when server logout fails', async () => {
    runtime.getCurrentUser.mockResolvedValue(user);
    runtime.logout.mockRejectedValue(new Error('stale session'));
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await screen.findByText('video_user');

    fireEvent.click(screen.getByRole('button', { name: '退出' }));

    await waitFor(() => expect(screen.getByText('guest')).toBeInTheDocument());
    expect(runtime.logout).toHaveBeenCalledOnce();
    expect(runtime.resetSocket).toHaveBeenCalled();
  });
});

function AuthProbe() {
  const { loading, signOut, user } = useAuth();
  return (
    <div>
      <p role="status">{loading ? 'loading' : 'ready'}</p>
      <p>{user?.username ?? 'guest'}</p>
      <button onClick={() => void signOut()} type="button">
        退出
      </button>
    </div>
  );
}
