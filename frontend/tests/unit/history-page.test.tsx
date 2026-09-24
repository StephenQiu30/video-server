import { type QueryClient, useQueryClient } from '@tanstack/react-query';
import {
  act,
  fireEvent,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { type ReactNode, useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DownloadHistoryView from '@/components/downloads/download-history-view';
import { useDownloadHistory } from '@/components/downloads/use-download-history';
import { privateQueryKey } from '@/lib/query-keys';
import { render, renderHook } from '../helpers/query-render';

const runtime = vi.hoisted(() => ({
  deleteDownload: vi.fn(),
  getDownloadHistory: vi.fn(),
  issueDownloadUrl: vi.fn(),
  retryDownload: vi.fn(),
  triggerBrowserDownload: vi.fn(),
  push: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: runtime.push }),
}));

describe('download history', () => {
  beforeEach(() => {
    runtime.deleteDownload.mockReset();
    runtime.getDownloadHistory.mockReset();
    runtime.issueDownloadUrl.mockReset();
    runtime.retryDownload.mockReset();
    runtime.triggerBrowserDownload.mockReset();
    runtime.push.mockReset();
  });

  it('maps pagination, search, status, and refresh to the history facade', async () => {
    runtime.getDownloadHistory.mockResolvedValue(history());
    const initialQuery: API.getDownloadHistoryParams = {
      page: 1,
      page_size: 20,
    };
    const { result, rerender } = renderHook(
      ({ query }: { query: API.getDownloadHistoryParams }) =>
        useDownloadHistory(query),
      { initialProps: { query: initialQuery } },
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(runtime.getDownloadHistory).toHaveBeenLastCalledWith(
      {
        page: 1,
        page_size: 20,
        search: undefined,
        status: undefined,
      },
      { signal: expect.any(AbortSignal) },
    );

    rerender({
      query: {
        page: 3,
        page_size: 20,
        search: '示例视频',
        status: 'succeeded',
      },
    });
    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenLastCalledWith(
        {
          page: 3,
          page_size: 20,
          search: '示例视频',
          status: 'succeeded',
        },
        { signal: expect.any(AbortSignal) },
      ),
    );

    act(() => result.current.retry());
    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenCalledTimes(3),
    );
  });

  it('exposes loading and computed summary states', async () => {
    let resolveHistory!: (value: API.DownloadHistoryResponse) => void;
    runtime.getDownloadHistory.mockReturnValue(
      new Promise<API.DownloadHistoryResponse>((resolve) => {
        resolveHistory = resolve;
      }),
    );
    const { container } = render(<DownloadHistoryView />);

    const summary = container.querySelector(
      '[data-slot="download-history-summary"]',
    );
    expect(summary).toHaveAttribute('aria-busy', 'true');
    expect(
      summary?.querySelector('[data-slot="skeleton"]'),
    ).toBeInTheDocument();

    act(() => resolveHistory(history()));
    await waitFor(() => expect(summary).toHaveAttribute('aria-busy', 'false'));
    expect(summary).toHaveTextContent('共 1 项 · 已完成 1 · 进行中 0');
  });

  it('renders history rows and performs detail and file actions', async () => {
    runtime.getDownloadHistory.mockResolvedValue(history());
    runtime.issueDownloadUrl.mockResolvedValue({
      expires_at: '2026-08-09T10:05:00Z',
      filename: '示例视频.mp4',
      url: 'https://objects.example/signed',
    });
    render(<DownloadHistoryView />);

    expect(
      await screen.findByRole('link', { name: '示例视频' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回上一步' })).toHaveAttribute(
      'href',
      '/',
    );
    expect(screen.getByRole('link', { name: '解析新链接' })).toHaveAttribute(
      'href',
      '/',
    );
    expect(
      screen.getByText('共 1 项 · 已完成 1 · 进行中 0'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '示例视频' })).toHaveAttribute(
      'href',
      '/downloads/detail?jobId=history-job-1',
    );
    const detailLink = screen.getByRole('link', { name: '示例视频' });
    expect(
      within(detailLink).getByRole('img', { name: '示例视频（暂无封面）' }),
    ).toBeVisible();
    expect(detailLink).toHaveTextContent('链接下载');
    expect(screen.getAllByText('链接下载')).toHaveLength(2);

    fireEvent.click(screen.getByRole('button', { name: '获取文件' }));
    await waitFor(() =>
      expect(runtime.triggerBrowserDownload).toHaveBeenCalledWith(
        'https://objects.example/signed',
        '示例视频.mp4',
      ),
    );
    expect(runtime.issueDownloadUrl).toHaveBeenCalledWith(
      { job_id: 'history-job-1', preview: false },
      { headers: { 'X-FrameFetch-Download-Client': 'local-web' } },
    );
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

  it('confirms deletion and refreshes the download history', async () => {
    runtime.getDownloadHistory.mockResolvedValue(history());
    runtime.deleteDownload.mockResolvedValue(undefined);
    let client!: QueryClient;
    function Cache({ children }: { children: ReactNode }) {
      client = useQueryClient();
      return children;
    }
    render(<DownloadHistoryView />, { wrapper: Cache });
    const detailKey = privateQueryKey('download', 'history-job-1');
    const analysisKey = privateQueryKey('analysis', 'video', 'history-job-1');
    client.setQueryData(detailKey, { id: 'history-job-1' });
    client.setQueryData(analysisKey, { id: 'analysis-1' });

    fireEvent.click(
      await screen.findByRole('button', { name: '删除下载记录' }),
    );
    expect(
      await screen.findByRole('alertdialog', { name: '删除任务与文件？' }),
    ).toHaveTextContent(
      '下载记录、视频文件、本地上传源文件和私有封面将永久删除',
    );
    fireEvent.click(screen.getByRole('button', { name: '确认删除' }));

    await waitFor(() =>
      expect(runtime.deleteDownload).toHaveBeenCalledWith({
        job_id: 'history-job-1',
      }),
    );
    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenCalledTimes(2),
    );
    expect(client.getQueryData(detailKey)).toBeNull();
    expect(client.getQueryData(analysisKey)).toBeUndefined();
  });

  it('returns to the last available page after deleting its final record', async () => {
    let total = 21;
    runtime.getDownloadHistory.mockImplementation(({ page }) =>
      Promise.resolve(history({ page, total })),
    );
    runtime.deleteDownload.mockImplementation(async () => {
      total = 20;
    });
    render(<DownloadHistoryView />);
    fireEvent.click(await screen.findByRole('button', { name: '下一页' }));
    await screen.findByText('2 / 2');
    fireEvent.click(screen.getByRole('button', { name: '删除下载记录' }));
    fireEvent.click(await screen.findByRole('button', { name: '确认删除' }));
    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 1 }),
        expect.anything(),
      ),
    );
    expect(screen.getByRole('textbox', { name: '搜索下载记录' })).toHaveValue(
      '',
    );
  });

  it('retries failed and expired-file records from history', async () => {
    runtime.getDownloadHistory.mockResolvedValue(
      history({
        items: [
          historyItem({
            file_available: false,
            status: 'succeeded',
          }),
        ],
      }),
    );
    runtime.retryDownload.mockResolvedValue({ id: 'retried-job' });
    render(<DownloadHistoryView />);

    fireEvent.click(await screen.findByRole('button', { name: '重新下载' }));

    await waitFor(() =>
      expect(runtime.retryDownload).toHaveBeenCalledWith(
        { job_id: 'history-job-1' },
        { headers: { 'Idempotency-Key': 'history-retry-key' } },
      ),
    );
    expect(runtime.push).toHaveBeenCalledWith(
      '/downloads/detail?jobId=retried-job',
    );
  });

  it('does not navigate after a history retry completes on another page', async () => {
    runtime.getDownloadHistory.mockResolvedValue(
      history({
        items: [historyItem({ status: 'failed', file_available: false })],
      }),
    );
    let resolveRetry!: (value: { id: string }) => void;
    runtime.retryDownload.mockReturnValue(
      new Promise((resolve) => {
        resolveRetry = resolve;
      }),
    );
    function Routes() {
      const [visible, setVisible] = useState(true);
      return (
        <>
          <button type="button" onClick={() => setVisible(!visible)}>
            Navigate away
          </button>
          {visible && <DownloadHistoryView />}
        </>
      );
    }
    render(<Routes />);
    fireEvent.click(await screen.findByRole('button', { name: '重新下载' }));
    await waitFor(() => expect(runtime.retryDownload).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByText('Navigate away'));
    await act(async () => resolveRetry({ id: 'retried-job' }));
    expect(runtime.push).not.toHaveBeenCalled();
  });

  it('changes pages through the shared pagination controls', async () => {
    runtime.getDownloadHistory.mockImplementation(
      async ({ page = 1 }: API.getDownloadHistoryParams) =>
        history({
          items: [historyItem({ id: `history-job-${page}` })],
          page,
          total: 21,
        }),
    );
    render(<DownloadHistoryView />);

    const pagination = await screen.findByRole('navigation', {
      name: '下载记录分页',
    });
    expect(within(pagination).getByText('1 / 2')).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(
      within(pagination).getByRole('button', { name: '上一页' }),
    ).toBeDisabled();

    fireEvent.click(within(pagination).getByRole('button', { name: '下一页' }));
    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 2 }),
        { signal: expect.any(AbortSignal) },
      ),
    );
    expect(
      within(pagination).getByRole('button', { name: '下一页' }),
    ).toBeDisabled();
  });

  it('submits a trimmed title search from the keyboard', async () => {
    runtime.getDownloadHistory.mockResolvedValue(history());
    render(<DownloadHistoryView />);
    await screen.findByRole('link', { name: '示例视频' });

    const input = screen.getByRole('textbox', { name: '搜索下载记录' });
    fireEvent.change(input, { target: { value: '  示例视频  ' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenLastCalledWith(
        {
          page: 1,
          page_size: 20,
          search: '示例视频',
          status: undefined,
        },
        { signal: expect.any(AbortSignal) },
      ),
    );
  });

  it('uses one consistent control height for the filter toolbar', async () => {
    runtime.getDownloadHistory.mockResolvedValue(history());
    const { container } = render(<DownloadHistoryView />);
    await screen.findByRole('link', { name: '示例视频' });

    const fieldGroup = container.querySelector('[data-slot="field-group"]');
    const inputGroup = container.querySelector('[data-slot="input-group"]');
    const selectTrigger = container.querySelector(
      '[data-slot="select-trigger"]',
    );
    const refreshButton = screen.getByRole('button', { name: '刷新' });

    expect(fieldGroup).toHaveClass('grid', 'gap-3');
    expect(inputGroup).toHaveClass('h-8');
    expect(selectTrigger).toHaveAttribute('data-size', 'default');
    expect(refreshButton).toHaveAttribute('data-size', 'default');
  });

  it('submits the search when the colored search icon is clicked', async () => {
    runtime.getDownloadHistory.mockResolvedValue(history());
    render(<DownloadHistoryView />);
    await screen.findByRole('link', { name: '示例视频' });

    const input = screen.getByRole('textbox', { name: '搜索下载记录' });
    fireEvent.change(input, { target: { value: ' 夹克  ' } });
    fireEvent.click(screen.getByRole('button', { name: '搜索下载记录' }));

    await waitFor(() =>
      expect(runtime.getDownloadHistory).toHaveBeenLastCalledWith(
        {
          page: 1,
          page_size: 20,
          search: '夹克',
          status: undefined,
        },
        { signal: expect.any(AbortSignal) },
      ),
    );
  });
});

function historyItem(
  overrides: Partial<API.DownloadHistoryItemResponse> = {},
): API.DownloadHistoryItemResponse {
  return {
    created_at: '2026-08-09T10:00:00Z',
    error_code: null,
    finished_at: '2026-08-09T10:02:00Z',
    file_available: true,
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

function history(
  overrides: Partial<API.DownloadHistoryResponse> = {},
): API.DownloadHistoryResponse {
  return {
    items: [historyItem()],
    page: 1,
    page_size: 20,
    summary: { active: 0, failed: 0, succeeded: 1, total: 1 },
    total: 1,
    ...overrides,
  };
}

vi.mock('@/lib/request-error', async (original) => ({
  ...(await original<typeof import('@/lib/request-error')>()),
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
}));
vi.mock('@/api/downloads', async (original) => ({
  ...(await original<typeof import('@/api/downloads')>()),
  getDownloadHistory: runtime.getDownloadHistory,
  deleteDownload: runtime.deleteDownload,
  issueDownloadUrl: runtime.issueDownloadUrl,
  retryDownload: runtime.retryDownload,
}));
vi.mock('@/lib/uuid', async (original) => ({
  ...(await original<typeof import('@/lib/uuid')>()),
  createUuid: () => 'history-retry-key',
}));
vi.mock('@/lib/browser-download', async (original) => ({
  ...(await original<typeof import('@/lib/browser-download')>()),
  triggerBrowserDownload: runtime.triggerBrowserDownload,
}));
