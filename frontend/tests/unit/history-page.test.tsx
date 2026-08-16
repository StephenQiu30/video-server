import {
  act,
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import DownloadHistoryView from '@/components/download-history-view';
import { useDownloadHistory } from '@/hooks/useDownloadHistory';
import type {
  DownloadHistory,
  DownloadHistoryItem,
  DownloadHistoryQuery,
} from '@/types/video';

const runtime = vi.hoisted(() => ({
  getDownloadHistory: vi.fn(),
  issueDownloadUrl: vi.fn(),
  retryDownload: vi.fn(),
  triggerBrowserDownload: vi.fn(),
}));

vi.mock('next/navigation', () => ({}));

vi.mock('@/services/download', () => ({
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
  getDownloadHistory: runtime.getDownloadHistory,
  issueDownloadUrl: runtime.issueDownloadUrl,
  createIdempotencyKey: () => 'history-retry-key',
  retryDownload: runtime.retryDownload,
  triggerBrowserDownload: runtime.triggerBrowserDownload,
}));

describe('download history', () => {
  beforeEach(() => {
    runtime.getDownloadHistory.mockReset();
    runtime.issueDownloadUrl.mockReset();
    runtime.retryDownload.mockReset();
    runtime.triggerBrowserDownload.mockReset();
  });

  it('maps pagination, search, status, and refresh to the history facade', async () => {
    runtime.getDownloadHistory.mockResolvedValue(history());
    const initialQuery: DownloadHistoryQuery = {
      page: 1,
      page_size: 20,
    };
    const { result, rerender } = renderHook(
      ({ query }: { query: DownloadHistoryQuery }) => useDownloadHistory(query),
      { initialProps: { query: initialQuery } },
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(runtime.getDownloadHistory).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 20,
      search: undefined,
      status: undefined,
    });

    rerender({
      query: {
        page: 3,
        page_size: 20,
        search: '示例视频',
        status: 'succeeded',
      },
    });
    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenLastCalledWith({
        page: 3,
        page_size: 20,
        search: '示例视频',
        status: 'succeeded',
      }),
    );

    act(() => result.current.retry());
    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenCalledTimes(3),
    );
  });

  it('reserves the summary geometry while initial data loads', async () => {
    let resolveHistory!: (value: DownloadHistory) => void;
    runtime.getDownloadHistory.mockReturnValue(
      new Promise<DownloadHistory>((resolve) => {
        resolveHistory = resolve;
      }),
    );
    const { container } = render(<DownloadHistoryView />);

    const summary = container.querySelector(
      '[data-slot="download-history-summary"]',
    );
    expect(summary).toHaveClass('h-[1.125rem]');
    expect(summary).toHaveAttribute('aria-busy', 'true');
    expect(summary?.querySelector('[data-slot="skeleton"]')).toHaveClass(
      'h-full',
    );

    act(() => resolveHistory(history()));
    await waitFor(() => expect(summary).toHaveAttribute('aria-busy', 'false'));
    expect(summary).toHaveTextContent('共 1 项 · 已完成 1 · 进行中 0');
    expect(summary).toHaveClass('h-[1.125rem]');
  });

  it('renders history rows and performs detail and file actions', async () => {
    runtime.getDownloadHistory.mockResolvedValue(history());
    runtime.issueDownloadUrl.mockResolvedValue({
      expires_at: '2026-08-09T10:05:00Z',
      url: 'https://objects.example/signed',
    });
    const { container } = render(<DownloadHistoryView />);

    expect(await screen.findByText('示例视频')).toBeInTheDocument();
    expect(container.querySelector('.inner-page')).toHaveClass('inner-page');
    expect(
      screen.getByRole('heading', { level: 1, name: '下载历史' }),
    ).toBeInTheDocument();
    expect(screen.queryByText('02 / 下载记录')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回上一步' })).toHaveAttribute(
      'href',
      '/',
    );
    expect(screen.queryByText('任务记录')).not.toBeInTheDocument();
    expect(
      screen.getByText('共 1 项 · 已完成 1 · 进行中 0'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '示例视频' })).toHaveAttribute(
      'href',
      '/downloads/detail?jobId=history-job-1',
    );

    fireEvent.click(screen.getByRole('button', { name: '获取文件' }));
    await waitFor(() =>
      expect(runtime.triggerBrowserDownload).toHaveBeenCalledWith(
        'https://objects.example/signed',
      ),
    );
    expect(runtime.issueDownloadUrl).toHaveBeenCalledWith('history-job-1');
  });

  it('renders pending task actions as detail links', async () => {
    runtime.getDownloadHistory.mockResolvedValue(
      history({
        items: [historyItem({ progress: 42, status: 'running' })],
        summary: { active: 1, failed: 0, succeeded: 0, total: 1 },
      }),
    );
    render(<DownloadHistoryView />);

    const detailHref = '/downloads/detail?jobId=history-job-1';
    expect(
      await screen.findByRole('link', { name: '示例视频' }),
    ).toHaveAttribute('href', detailHref);
    expect(screen.getByRole('link', { name: '查看任务' })).toHaveAttribute(
      'href',
      detailHref,
    );
  });

  it('retries failed and expired-file records from history', async () => {
    runtime.getDownloadHistory.mockResolvedValue(
      history({
        items: [
          historyItem({
            file_available: false,
            file_expires_at: '2026-08-08T10:00:00Z',
            status: 'succeeded',
          }),
        ],
      }),
    );
    runtime.retryDownload.mockResolvedValue({ id: 'retried-job' });
    const assign = vi
      .spyOn(window.location, 'assign')
      .mockImplementation(() => undefined);
    render(<DownloadHistoryView />);

    fireEvent.click(await screen.findByRole('button', { name: '重新下载' }));

    await waitFor(() =>
      expect(runtime.retryDownload).toHaveBeenCalledWith(
        'history-job-1',
        'history-retry-key',
      ),
    );
    expect(assign).toHaveBeenCalledWith('/downloads/detail?jobId=retried-job');
  });

  it('changes pages through the shared pagination controls', async () => {
    runtime.getDownloadHistory.mockImplementation(
      async ({ page = 1 }: DownloadHistoryQuery) =>
        history({
          items: [historyItem({ id: `history-job-${page}` })],
          page,
          total: 21,
        }),
    );
    render(<DownloadHistoryView />);

    const pagination = await screen.findByRole('navigation', {
      name: '下载历史分页',
    });
    expect(within(pagination).getByText('1 / 2')).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(
      within(pagination).getByRole('button', { name: '上一页' }),
    ).toBeDisabled();
    expect(
      within(pagination).getByRole('button', { name: '上一页' }),
    ).toHaveClass('h-11');
    expect(within(pagination).getByText('1 / 2')).toHaveClass('h-11');

    fireEvent.click(within(pagination).getByRole('button', { name: '下一页' }));
    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 2 }),
      ),
    );
    expect(within(pagination).getByText('2 / 2')).toBeInTheDocument();
    expect(
      within(pagination).getByRole('button', { name: '下一页' }),
    ).toBeDisabled();
  });

  it('submits a trimmed title search from the accessible form', async () => {
    runtime.getDownloadHistory.mockResolvedValue(history());
    render(<DownloadHistoryView />);
    await screen.findByText('示例视频');

    const input = screen.getByRole('textbox', { name: '搜索下载历史' });
    fireEvent.change(input, { target: { value: '  示例视频  ' } });
    fireEvent.submit(input.closest('form') as HTMLFormElement);

    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 20,
        search: '示例视频',
        status: undefined,
      }),
    );
  });

  it('submits the search when the colored search icon is clicked', async () => {
    runtime.getDownloadHistory.mockResolvedValue(history());
    render(<DownloadHistoryView />);
    await screen.findByText('示例视频');

    const input = screen.getByRole('textbox', { name: '搜索下载历史' });
    fireEvent.change(input, { target: { value: ' 夹克  ' } });
    fireEvent.click(screen.getByRole('button', { name: '搜索下载历史' }));

    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 20,
        search: '夹克',
        status: undefined,
      }),
    );
  });
});

function historyItem(
  overrides: Partial<DownloadHistoryItem> = {},
): DownloadHistoryItem {
  return {
    created_at: '2026-08-09T10:00:00Z',
    error_code: null,
    finished_at: '2026-08-09T10:02:00Z',
    file_available: true,
    file_expires_at: '2026-08-16T10:02:00Z',
    format_name: '1080p MP4',
    id: 'history-job-1',
    progress: 100,
    source_kind: 'remote_provider',
    source_label: '链接下载',
    status: 'succeeded',
    thumbnail_url: null,
    title: '示例视频',
    updated_at: '2026-08-09T10:02:00Z',
    ...overrides,
  };
}

function history(overrides: Partial<DownloadHistory> = {}): DownloadHistory {
  return {
    items: [historyItem()],
    page: 1,
    page_size: 20,
    summary: { active: 0, failed: 0, succeeded: 1, total: 1 },
    total: 1,
    ...overrides,
  };
}
