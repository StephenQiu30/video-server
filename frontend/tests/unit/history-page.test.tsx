import {
  act,
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
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
  push: vi.fn(),
  triggerBrowserDownload: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: runtime.push }),
}));

vi.mock('@/services/download', () => ({
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
  getDownloadHistory: runtime.getDownloadHistory,
  issueDownloadUrl: runtime.issueDownloadUrl,
  triggerBrowserDownload: runtime.triggerBrowserDownload,
}));

describe('download history', () => {
  beforeEach(() => {
    runtime.getDownloadHistory.mockReset();
    runtime.issueDownloadUrl.mockReset();
    runtime.push.mockReset();
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

  it('renders history rows and performs detail and file actions', async () => {
    runtime.getDownloadHistory.mockResolvedValue(history());
    runtime.issueDownloadUrl.mockResolvedValue({
      expires_at: '2026-08-09T10:05:00Z',
      url: 'https://objects.example/signed',
    });
    render(<DownloadHistoryView />);

    expect(await screen.findByText('示例视频')).toBeInTheDocument();
    expect(
      screen.getByText('共 1 项 · 已完成 1 · 进行中 0'),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '示例视频' }));
    expect(runtime.push).toHaveBeenCalledWith(
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
});

function historyItem(
  overrides: Partial<DownloadHistoryItem> = {},
): DownloadHistoryItem {
  return {
    created_at: '2026-08-09T10:00:00Z',
    error_code: null,
    finished_at: '2026-08-09T10:02:00Z',
    format_name: '1080p MP4',
    id: 'history-job-1',
    progress: 100,
    status: 'succeeded',
    thumbnail_url: null,
    title: '示例视频',
    updated_at: '2026-08-09T10:02:00Z',
    ...overrides,
  };
}

function history(): DownloadHistory {
  return {
    items: [historyItem()],
    page: 1,
    page_size: 20,
    summary: { active: 0, failed: 0, succeeded: 1, total: 1 },
    total: 1,
  };
}
