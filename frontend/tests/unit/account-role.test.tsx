import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AccountView } from '@/components/account/account-view';
import { ApiError } from '@/lib/request-error';
import { render, renderWithToasts } from '../helpers/query-render';

const runtime = vi.hoisted(() => ({
  updateAccess: vi.fn(),
  updateUser: vi.fn(),
  setUser: vi.fn(),
  user: {
    id: 'owner',
    username: 'Stephen',
    email: 'owner@example.com',
    role: 'admin' as 'admin' | 'user',
    created_at: '2026-09-26T00:00:00Z',
    updated_at: '2026-09-26T00:00:00Z',
    avatar_version: null,
  },
}));

vi.mock('@/api/admin', () => ({ updateUserAccess: runtime.updateAccess }));
vi.mock('@/api/users', () => ({
  deleteCurrentUserAvatar: vi.fn(),
  updateCurrentUser: runtime.updateUser,
  uploadCurrentUserAvatar: vi.fn(),
}));
vi.mock('@/components/auth/auth-provider', async (importOriginal) => ({
  ...(await importOriginal()),
  useAuth: () => ({
    user: runtime.user,
    loading: false,
    setUser: runtime.setUser,
    refreshUser: vi.fn(),
  }),
}));

describe('account role editing', () => {
  beforeEach(() => {
    runtime.user.role = 'admin';
    runtime.updateAccess.mockReset();
    runtime.updateUser.mockReset();
    runtime.setUser.mockReset();
  });

  it('lets an administrator select a role and saves it through the admin API', async () => {
    runtime.updateAccess.mockResolvedValue({
      role: 'user',
      updated_at: '2026-09-26T01:00:00Z',
    });
    render(<AccountView />);

    fireEvent.click(screen.getByRole('combobox', { name: '账户身份' }));
    fireEvent.click(await screen.findByRole('option', { name: '普通用户' }));
    fireEvent.click(screen.getByRole('button', { name: '保存资料' }));

    await waitFor(() => {
      expect(runtime.updateAccess).toHaveBeenCalledWith(
        { user_id: 'owner' },
        { role: 'user' },
      );
    });
    expect(runtime.setUser).toHaveBeenCalledWith(
      expect.objectContaining({ role: 'user' }),
    );
    expect(runtime.updateUser).not.toHaveBeenCalled();
  });

  it('shows the role to regular users without letting them edit it', () => {
    runtime.user.role = 'user';
    render(<AccountView />);

    expect(screen.getByRole('combobox', { name: '账户身份' })).toBeDisabled();
    expect(screen.getByText('仅管理员可以修改账户身份。')).toBeVisible();
    expect(runtime.updateAccess).not.toHaveBeenCalled();
  });

  it('keeps the selected role and explains when the last admin cannot be removed', async () => {
    runtime.updateAccess.mockRejectedValue(
      new ApiError(409, 'last_admin_change', 'Conflict', 'Last admin'),
    );
    renderWithToasts(<AccountView />);

    fireEvent.click(screen.getByRole('combobox', { name: '账户身份' }));
    fireEvent.click(await screen.findByRole('option', { name: '普通用户' }));
    fireEvent.click(screen.getByRole('button', { name: '保存资料' }));

    expect(
      await screen.findByText('请先保留另一位启用的管理员，再修改当前身份。'),
    ).toBeVisible();
    expect(runtime.setUser).not.toHaveBeenCalled();
    expect(
      screen.getByRole('combobox', { name: '账户身份' }),
    ).toHaveTextContent('普通用户');
  });
});
