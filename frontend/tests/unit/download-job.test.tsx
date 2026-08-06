import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import DownloadJobPage from '@/pages/DownloadJob';
import { job, jsonResponse } from './download-fixtures';

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('DownloadJobPage', () => {
  it('polls serially until the job succeeds', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(job('running')))
      .mockResolvedValueOnce(jsonResponse(job('succeeded')));
    vi.stubGlobal('fetch', fetchMock);

    render(<DownloadJobPage jobId={job().id} pollIntervalMs={5} />);

    expect(await screen.findByText('下载中')).toBeInTheDocument();
    expect(await screen.findByText('下载已完成')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'AI 智能分析' }),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('cancels an active job', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(job('running')))
      .mockResolvedValueOnce(jsonResponse(job('cancelled')));
    vi.stubGlobal('fetch', fetchMock);
    render(<DownloadJobPage jobId={job().id} pollIntervalMs={60_000} />);

    fireEvent.click(await screen.findByRole('button', { name: '取消任务' }));

    expect(await screen.findByText('任务已取消')).toBeInTheDocument();
    expect(fetchMock.mock.calls[1][0]).toBe(
      `/api/v1/downloads/${job().id}/cancel`,
    );
  });

  it('requests a short-lived URL and triggers the file download', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(job('succeeded')))
      .mockResolvedValueOnce(
        jsonResponse({
          url: 'https://objects.example/token',
          expires_at: '2026-08-06T10:05:00Z',
        }),
      );
    vi.stubGlobal('fetch', fetchMock);
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
    render(<DownloadJobPage jobId={job().id} />);

    fireEvent.click(await screen.findByRole('button', { name: '获取文件' }));

    await waitFor(() => expect(click).toHaveBeenCalledOnce());
    expect(fetchMock.mock.calls[1][0]).toBe(
      `/api/v1/downloads/${job().id}/download-url`,
    );
  });

  it('shows RFC9457 errors and retries on demand', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(
          {
            status: 404,
            code: 'not_found',
            title: 'Not found',
            detail: '任务不存在',
          },
          404,
        ),
      )
      .mockResolvedValueOnce(jsonResponse(job('queued')));
    vi.stubGlobal('fetch', fetchMock);
    render(<DownloadJobPage jobId={job().id} />);

    expect(await screen.findByText('任务不存在')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /重\s*试/ }));

    expect(await screen.findByText('等待处理')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('renders a terminal failure and its stable fallback code', async () => {
    const failed = { ...job('failed'), error_code: null };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(failed)));

    render(<DownloadJobPage jobId={failed.id} />);

    expect(await screen.findByText('下载失败')).toBeInTheDocument();
    expect(screen.getByText('错误代码：unknown_error')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '取消任务' }),
    ).not.toBeInTheDocument();
  });

  it('reports cancel failures without losing the current job', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(job('running')))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            status: 409,
            code: 'not_cancellable',
            title: '冲突',
            detail: '任务无法取消',
          },
          409,
        ),
      );
    vi.stubGlobal('fetch', fetchMock);
    render(<DownloadJobPage jobId={job().id} pollIntervalMs={60_000} />);

    fireEvent.click(await screen.findByRole('button', { name: '取消任务' }));

    expect(await screen.findByText('任务无法取消')).toBeInTheDocument();
    expect(screen.getByText('下载中')).toBeInTheDocument();
  });

  it('reports download-url failures', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(job('succeeded')))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            status: 503,
            code: 'storage_unavailable',
            title: '不可用',
            detail: '文件暂不可用',
          },
          503,
        ),
      );
    vi.stubGlobal('fetch', fetchMock);
    render(<DownloadJobPage jobId={job().id} />);

    fireEvent.click(await screen.findByRole('button', { name: '获取文件' }));

    expect(await screen.findByText('文件暂不可用')).toBeInTheDocument();
  });
});
