import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ProviderCatalogScreen } from '@/components/admin-provider-catalog/provider-catalog-screen';
import { AdminProviderCatalogView } from '@/components/admin-provider-catalog-view';

const runtime = vi.hoisted(() => ({
  create: vi.fn(),
  delete: vi.fn(),
  list: vi.fn(),
  update: vi.fn(),
}));

vi.mock('@/services/provider-catalog', () => ({
  createProviderCatalogEntry: runtime.create,
  deleteProviderCatalogEntry: runtime.delete,
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
  listProviderCatalogEntries: runtime.list,
  updateProviderCatalogEntry: runtime.update,
}));

describe('administrator provider catalog management', () => {
  beforeEach(() => {
    runtime.create.mockReset();
    runtime.delete.mockReset();
    runtime.list.mockReset();
    runtime.update.mockReset();
    runtime.list.mockResolvedValue({ items: [youtube(), custom()] });
    runtime.create.mockResolvedValue(custom({ key: 'new_video' }));
    runtime.update.mockResolvedValue(custom({ display_name: '新名称' }));
    runtime.delete.mockResolvedValue(undefined);
  });

  it('maps create, edit, visibility and delete actions to the admin API', async () => {
    render(<AdminProviderCatalogView />);

    expect(
      await screen.findByRole('heading', { level: 1, name: '平台目录' }),
    ).toBeInTheDocument();
    expect(screen.getAllByText('系统已注册')[0]).toBeInTheDocument();
    expect(screen.getAllByText('仅目录')[0]).toBeInTheDocument();
    const desktopTable = screen.getByRole('table', { name: '平台目录列表' });
    expect(
      within(desktopTable).getByRole('columnheader', { name: '排序' }),
    ).toHaveClass('text-right');
    expect(
      within(
        within(desktopTable).getByRole('row', { name: /YouTube youtube/ }),
      ).getAllByRole('cell')[3],
    ).toHaveClass('text-right', 'tabular-nums');

    fireEvent.click(screen.getByRole('button', { name: '新增平台' }));
    let dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('目录键'), {
      target: { value: 'new_video' },
    });
    fireEvent.change(within(dialog).getByLabelText('显示名称'), {
      target: { value: 'New Video' },
    });
    fireEvent.change(within(dialog).getByLabelText('排序值'), {
      target: { value: '25' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: '新增平台' }));
    await waitFor(() =>
      expect(runtime.create).toHaveBeenCalledWith({
        display_name: 'New Video',
        is_visible: true,
        key: 'new_video',
        sort_order: 25,
      }),
    );

    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
    );
    fireEvent.click(
      screen.getAllByRole('button', { name: '编辑平台 Custom Video' })[0],
    );
    dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByLabelText('目录键')).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText('显示名称'), {
      target: { value: '新名称' },
    });
    fireEvent.click(within(dialog).getByLabelText('公开显示'));
    fireEvent.click(within(dialog).getByRole('button', { name: '保存更改' }));
    await waitFor(() =>
      expect(runtime.update).toHaveBeenCalledWith('custom', {
        display_name: '新名称',
        is_visible: false,
        sort_order: 90,
      }),
    );

    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
    );
    fireEvent.click(
      screen.getAllByRole('button', { name: '删除平台 Custom Video' })[0],
    );
    const alert = await screen.findByRole('alertdialog');
    expect(alert).toHaveTextContent('系统下载 Profile 不会因此被删除');
    fireEvent.click(within(alert).getByRole('button', { name: '确认删除' }));
    await waitFor(() => expect(runtime.delete).toHaveBeenCalledWith('custom'));
  });

  it('keeps the current catalog mounted during a background reload', () => {
    const actions = {
      onCreate: vi.fn(),
      onDelete: vi.fn(),
      onEdit: vi.fn(),
      onRetry: vi.fn(),
    };
    const { rerender } = render(
      <ProviderCatalogScreen
        {...actions}
        notice=""
        result={{ error: '', items: [youtube(), custom()], loading: false }}
      />,
    );

    rerender(
      <ProviderCatalogScreen
        {...actions}
        notice=""
        result={{ error: '', items: [youtube(), custom()], loading: true }}
      />,
    );

    expect(screen.getAllByText('YouTube')).toHaveLength(2);
    expect(screen.getAllByText('Custom Video')).toHaveLength(2);
    expect(
      screen.queryByRole('status', { name: '正在加载平台目录' }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '平台目录' }).closest('section'),
    ).toHaveAttribute('aria-busy', 'true');
  });
});

function youtube(): API.ProviderCatalogEntryResponse {
  return custom({
    display_name: 'YouTube',
    key: 'youtube',
    sort_order: 10,
    system_registered: true,
    system_status: 'verified',
  });
}

function custom(
  overrides: Partial<API.ProviderCatalogEntryResponse> = {},
): API.ProviderCatalogEntryResponse {
  return {
    created_at: '2026-08-12T10:00:00Z',
    display_name: 'Custom Video',
    is_visible: true,
    key: 'custom',
    sort_order: 90,
    system_registered: false,
    system_status: 'unsupported',
    updated_at: '2026-08-12T10:00:00Z',
    ...overrides,
  };
}
