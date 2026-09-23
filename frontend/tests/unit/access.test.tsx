import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ProtectedRoute } from '@/components/auth/protected-route';

const runtime = vi.hoisted(() => ({
  auth: {
    loading: false,
    status: 'anonymous',
    user: undefined as { role: API.UserRole } | undefined,
  },
  pathname: '/history',
  replace: vi.fn(),
}));

vi.mock('@/components/auth/auth-provider', async (importOriginal) => ({
  ...(await importOriginal()),
  useAuth: () => runtime.auth,
}));

vi.mock('next/navigation', () => ({
  usePathname: () => runtime.pathname,
  useRouter: () => ({ replace: runtime.replace }),
}));

describe('ProtectedRoute', () => {
  beforeEach(() => {
    runtime.auth = { loading: false, status: 'anonymous', user: undefined };
    runtime.pathname = '/history';
    runtime.replace.mockReset();
    window.history.replaceState({}, '', '/');
  });

  it('restores the complete local destination for unauthenticated users', async () => {
    window.history.replaceState({}, '', '/history?page=2');
    render(
      <ProtectedRoute>
        <p data-testid="protected-content" />
      </ProtectedRoute>,
    );

    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toBeInTheDocument();
    await waitFor(() =>
      expect(runtime.replace).toHaveBeenCalledWith(
        '/user/login?redirect=%2Fhistory%3Fpage%3D2',
      ),
    );
  });

  it('keeps administrator routes hidden from regular users', async () => {
    runtime.auth = {
      loading: false,
      status: 'authenticated',
      user: { role: 'user' },
    };
    render(
      <ProtectedRoute requireAdmin>
        <p data-testid="admin-content" />
      </ProtectedRoute>,
    );

    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
    await waitFor(() => expect(runtime.replace).toHaveBeenCalledWith('/'));
  });

  it('renders protected content after an administrator is restored', () => {
    runtime.auth = {
      loading: false,
      status: 'authenticated',
      user: { role: 'admin' },
    };
    render(
      <ProtectedRoute requireAdmin>
        <p data-testid="admin-content" />
      </ProtectedRoute>,
    );

    expect(screen.getByTestId('admin-content')).toBeInTheDocument();
    expect(runtime.replace).not.toHaveBeenCalled();
  });
});
