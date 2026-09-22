import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { AuthProvider } from '@/components/auth/auth-provider';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { ApiError } from '@/lib/request-error';

const runtime = vi.hoisted(() => ({ me: vi.fn(), replace: vi.fn() }));
vi.mock('@/api/auth', async (original) => ({
  ...(await original<typeof import('@/api/auth')>()),
  getCurrentUser: runtime.me,
}));
vi.mock('next/navigation', () => ({
  usePathname: () => '/history',
  useRouter: () => ({ replace: runtime.replace }),
}));

beforeEach(() => {
  runtime.me.mockReset();
  runtime.replace.mockReset();
  window.history.replaceState({}, '', '/history?filter=active');
});

it('keeps the protected route on recovery failure and retries in place', async () => {
  runtime.me.mockRejectedValueOnce(
    new ApiError(503, 'unavailable', '', '服务暂不可用'),
  );
  runtime.me.mockResolvedValueOnce({ id: 'member', role: 'user' });
  render(
    <AuthProvider>
      <ProtectedRoute>
        <p>下载记录内容</p>
      </ProtectedRoute>
    </AuthProvider>,
  );
  expect(await screen.findByRole('alert')).toHaveTextContent(
    '暂时无法确认登录状态',
  );
  expect(runtime.replace).not.toHaveBeenCalled();
  expect(screen.queryByText('下载记录内容')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '重试' }));
  expect(await screen.findByText('下载记录内容')).toBeInTheDocument();
  expect(runtime.replace).not.toHaveBeenCalled();
});

it('redirects only after confirmed expiry and preserves the current destination', async () => {
  runtime.me.mockRejectedValueOnce(
    new ApiError(401, 'unauthenticated', '', '会话失效'),
  );
  render(
    <AuthProvider>
      <ProtectedRoute>
        <p>下载记录内容</p>
      </ProtectedRoute>
    </AuthProvider>,
  );
  await waitFor(() =>
    expect(runtime.replace).toHaveBeenCalledWith(
      '/user/login?redirect=%2Fhistory%3Ffilter%3Dactive',
    ),
  );
  expect(screen.queryByText('下载记录内容')).not.toBeInTheDocument();
});
