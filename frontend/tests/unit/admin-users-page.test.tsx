import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AdminUsersView } from '@/components/admin/admin-users-view';

const runtime = vi.hoisted(() => ({
  listUsers: vi.fn(),
  updateUserAccess: vi.fn(),
  user: {
    created_at: '2026-08-09T10:00:00Z',
    email: 'owner@example.com',
    id: 'owner-id',
    role: 'admin' as const,
    updated_at: '2026-08-09T10:00:00Z',
    username: 'owner',
  },
}));

vi.mock('@/components/auth/auth-provider', () => ({
  useAuth: () => ({ loading: false, user: runtime.user }),
}));

describe('administrator user management', () => {
  beforeEach(() => {
    runtime.listUsers.mockReset();
    runtime.updateUserAccess.mockReset();
    runtime.updateUserAccess.mockResolvedValue(managedUser());
  });

  it('keeps self-edit disabled and maps search, pagination and save actions', async () => {
    runtime.listUsers.mockImplementation(async ({ page = 1 }) => ({
      items:
        page === 1 ? [owner(), managedUser()] : [managedUser({ id: 'next' })],
      page,
      page_size: 20,
      total: 21,
    }));
    render(<AdminUsersView />);

    await screen.findAllByText('owner');
    expect(screen.getByRole('link', { name: '返回上一步' })).toHaveAttribute(
      'href',
      '/account',
    );
    expect(runtime.listUsers).toHaveBeenLastCalledWith({
      is_active: undefined,
      page: 1,
      page_size: 20,
      role: undefined,
      search: undefined,
    });
    for (const button of screen.getAllByRole('button', {
      name: '管理用户 owner',
    })) {
      expect(button).toBeDisabled();
    }

    const search = screen.getByRole('textbox', { name: '搜索用户名或邮箱' });
    fireEvent.change(search, { target: { value: '  editor  ' } });
    fireEvent.submit(search.closest('form') as HTMLFormElement);
    await waitFor(() =>
      expect(runtime.listUsers).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 1, search: 'editor' }),
      ),
    );

    fireEvent.click(
      screen.getAllByRole('button', { name: '管理用户 editor' })[0],
    );
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(
      within(dialog).getByRole('spinbutton', { name: '24 小时任务数' }),
      { target: { value: '75' } },
    );
    fireEvent.change(
      within(dialog).getByRole('spinbutton', {
        name: '24 小时处理量（GiB）',
      }),
      { target: { value: '0.5' } },
    );
    fireEvent.click(within(dialog).getByRole('button', { name: '保存更改' }));
    await waitFor(() =>
      expect(runtime.updateUserAccess).toHaveBeenCalledWith(
        { user_id: 'editor-id' },
        {
          is_active: true,
          role: 'user',
          quota: {
            daily_analysis_attempts: null,
            daily_bytes: 536870912,
            daily_tasks: 75,
            exempt: false,
            max_active_per_owner: null,
            storage_bytes: null,
          },
        },
      ),
    );

    const pagination = screen.getByRole('navigation', { name: '用户列表分页' });
    expect(within(pagination).getByText('1 / 2')).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(
      within(pagination).getByRole('button', { name: '上一页' }),
    ).toBeDisabled();
    fireEvent.click(within(pagination).getByRole('button', { name: '下一页' }));
    await waitFor(() =>
      expect(runtime.listUsers).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 2, search: 'editor' }),
      ),
    );
    const updatedPagination = screen.getByRole('navigation', {
      name: '用户列表分页',
    });
    expect(within(updatedPagination).getByText('2 / 2')).toBeInTheDocument();
    expect(
      within(updatedPagination).getByRole('button', { name: '下一页' }),
    ).toBeDisabled();
  });

  it('ignores a stale list response after the query changes', async () => {
    const first = deferred<API.ManagedUserListResponse>();
    const second = deferred<API.ManagedUserListResponse>();
    runtime.listUsers
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    render(<AdminUsersView />);

    const search = screen.getByRole('textbox', { name: '搜索用户名或邮箱' });
    fireEvent.change(search, { target: { value: 'fresh' } });
    fireEvent.submit(search.closest('form') as HTMLFormElement);
    await waitFor(() => expect(runtime.listUsers).toHaveBeenCalledTimes(2));

    await act(async () =>
      second.resolve(result([managedUser({ username: 'fresh' })])),
    );
    expect(await screen.findAllByText('fresh')).toHaveLength(2);
    await act(async () =>
      first.resolve(result([managedUser({ username: 'stale' })])),
    );
    expect(screen.queryByText('stale')).not.toBeInTheDocument();
  });

  it('keeps the current rows mounted while a search refresh is pending', async () => {
    const refresh = deferred<API.ManagedUserListResponse>();
    runtime.listUsers
      .mockResolvedValueOnce(result([managedUser()]))
      .mockReturnValueOnce(refresh.promise);
    render(<AdminUsersView />);

    expect(await screen.findAllByText('editor')).toHaveLength(2);
    const search = screen.getByRole('textbox', { name: '搜索用户名或邮箱' });
    fireEvent.change(search, { target: { value: 'fresh' } });
    fireEvent.submit(search.closest('form') as HTMLFormElement);
    await waitFor(() => expect(runtime.listUsers).toHaveBeenCalledTimes(2));

    expect(screen.getAllByText('editor')).toHaveLength(2);
    expect(
      screen.queryByRole('status', { name: '正在加载用户列表' }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '用户管理' }).closest('[aria-busy]'),
    ).toHaveAttribute('aria-busy', 'true');

    await act(async () =>
      refresh.resolve(result([managedUser({ username: 'fresh' })])),
    );
    expect(await screen.findAllByText('fresh')).toHaveLength(2);
  });
});

function owner(): API.ManagedUserResponse {
  return managedUser({
    email: runtime.user.email,
    id: runtime.user.id,
    role: 'admin',
    username: runtime.user.username,
  });
}

function managedUser(
  overrides: Partial<API.ManagedUserResponse> = {},
): API.ManagedUserResponse {
  return {
    created_at: '2026-08-09T10:00:00Z',
    email: 'editor@example.com',
    id: 'editor-id',
    is_active: true,
    role: 'user',
    updated_at: '2026-08-09T10:00:00Z',
    username: 'editor',
    ...overrides,
    quota: overrides.quota ?? { exempt: false },
  };
}

function result(items: API.ManagedUserResponse[]): API.ManagedUserListResponse {
  return { items, page: 1, page_size: 20, total: items.length };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

vi.mock('@/lib/request-error', async (original) => ({
  ...(await original<typeof import('@/lib/request-error')>()),
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
}));
vi.mock('@/api/admin', async (original) => ({
  ...(await original<typeof import('@/api/admin')>()),
  listUsers: runtime.listUsers,
  updateUserAccess: runtime.updateUserAccess,
}));
