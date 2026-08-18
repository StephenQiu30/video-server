import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ProtectedRoute } from '@/components/auth/protected-route';

const runtime = vi.hoisted(() => ({
  auth: {
    loading: false,
    user: undefined as { role: API.UserRole } | undefined,
  },
  pathname: '/history',
  replace: vi.fn(),
}));

vi.mock('@/components/auth/auth-provider', () => ({
  useAuth: () => runtime.auth,
}));

vi.mock('next/navigation', () => ({
  usePathname: () => runtime.pathname,
  useRouter: () => ({ replace: runtime.replace }),
}));

describe('ProtectedRoute', () => {
  beforeEach(() => {
    runtime.auth = { loading: false, user: undefined };
    runtime.pathname = '/history';
    runtime.replace.mockReset();
    window.history.replaceState({}, '', '/');
  });

  it('restores the complete local destination for unauthenticated users', async () => {
    window.history.replaceState({}, '', '/history?page=2');
    render(
      <ProtectedRoute>
        <p>受保护内容</p>
      </ProtectedRoute>,
    );

    expect(screen.queryByText('受保护内容')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('正在前往可访问页面');
    await waitFor(() =>
      expect(runtime.replace).toHaveBeenCalledWith(
        '/user/login?redirect=%2Fhistory%3Fpage%3D2',
      ),
    );
  });

  it('keeps administrator routes hidden from regular users', async () => {
    runtime.auth = { loading: false, user: { role: 'user' } };
    render(
      <ProtectedRoute requireAdmin>
        <p>用户管理</p>
      </ProtectedRoute>,
    );

    expect(screen.queryByText('用户管理')).not.toBeInTheDocument();
    await waitFor(() => expect(runtime.replace).toHaveBeenCalledWith('/'));
  });

  it('renders protected content after an administrator is restored', () => {
    runtime.auth = { loading: false, user: { role: 'admin' } };
    render(
      <ProtectedRoute requireAdmin>
        <p>用户管理</p>
      </ProtectedRoute>,
    );

    expect(screen.getByText('用户管理')).toBeInTheDocument();
    expect(runtime.replace).not.toHaveBeenCalled();
  });
});
