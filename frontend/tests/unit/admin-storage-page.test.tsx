import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AdminStorageView } from '@/components/admin/admin-storage-view';

const runtime = vi.hoisted(() => ({
  cleanupStoredFiles: vi.fn(),
  listStoredFiles: vi.fn(),
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

vi.mock('@/services/storage-files', () => ({
  cleanupStoredFiles: runtime.cleanupStoredFiles,
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
  listStoredFiles: runtime.listStoredFiles,
}));

describe('administrator storage management', () => {
  beforeEach(() => {
    runtime.cleanupStoredFiles.mockReset();
    runtime.listStoredFiles.mockReset();
  });

  it('paginates persistent files and cleans files older than 30 days by default', async () => {
    runtime.listStoredFiles.mockImplementation(async ({ page = 1 }) => ({
      items: [storedFile({ id: `file-${page}`, name: `视频 ${page}` })],
      page,
      page_size: 20,
      total: 21,
    }));
    runtime.cleanupStoredFiles.mockResolvedValue({
      failed_resources: 0,
      freed_bytes: 1_024,
      older_than_days: 30,
      removed_objects: 2,
      removed_resources: 1,
    });
    render(<AdminStorageView />);

    expect(await screen.findByText('视频 1')).toHaveClass(
      'w-full',
      'min-w-0',
      'truncate',
    );
    expect(runtime.listStoredFiles).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 20,
    });
    expect(screen.getByText(/默认持久保存/)).toBeInTheDocument();

    const pagination = screen.getByRole('navigation', { name: '文件列表分页' });
    fireEvent.click(within(pagination).getByRole('button', { name: '下一页' }));
    await waitFor(() =>
      expect(runtime.listStoredFiles).toHaveBeenLastCalledWith({
        page: 2,
        page_size: 20,
      }),
    );
    expect(await screen.findByText('视频 2')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '清理历史文件' }));
    const dialog = await screen.findByRole('alertdialog', {
      name: '清理历史文件？',
    });
    expect(within(dialog).getByLabelText('清理多少天前的文件')).toHaveValue(30);
    fireEvent.click(within(dialog).getByRole('button', { name: '确认清理' }));

    await waitFor(() =>
      expect(runtime.cleanupStoredFiles).toHaveBeenCalledWith(30),
    );
    expect(
      await screen.findByText('已清理 1 项资源、2 个对象；0 项清理失败。'),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(runtime.listStoredFiles).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 20,
      }),
    );
  });
});

function storedFile(
  overrides: Partial<API.StoredFileResponse> = {},
): API.StoredFileResponse {
  return {
    category: 'video',
    created_at: '2026-07-01T10:00:00Z',
    id: 'file-1',
    name: '视频 1',
    object_count: 1,
    size_bytes: 1_024,
    ...overrides,
  };
}
