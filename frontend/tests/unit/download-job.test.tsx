import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { request } from '@umijs/max';
import { describe, expect, it, vi } from 'vitest';

import { DownloadJobPage } from '@/pages/DownloadJob';
import { ApiError } from '@/requestErrorConfig';
import { inspection, job } from './download-fixtures';

const requestMock = vi.mocked(request);

describe('DownloadJobPage', () => {
  it('polls serially until the job succeeds', async () => {
    requestMock
      .mockResolvedValueOnce(job('running'))
      .mockResolvedValueOnce(inspection)
      .mockResolvedValueOnce(job('succeeded'));

    render(<DownloadJobPage jobId={job().id} pollIntervalMs={5} />);

    expect(await screen.findByText('下载中')).toBeInTheDocument();
    expect(await screen.findByText('下载已完成')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'AI 智能分析' }),
    ).toBeInTheDocument();
    expect(requestMock).toHaveBeenCalledTimes(3);
  });

  it('cancels an active job', async () => {
    requestMock
      .mockResolvedValueOnce(job('running'))
      .mockResolvedValueOnce(inspection)
      .mockResolvedValueOnce(job('cancelled'));
    render(<DownloadJobPage jobId={job().id} pollIntervalMs={60_000} />);

    fireEvent.click(await screen.findByRole('button', { name: '取消任务' }));

    expect(await screen.findByText('任务已取消')).toBeInTheDocument();
    expect(requestMock).toHaveBeenNthCalledWith(
      3,
      `/api/v1/downloads/${job().id}/cancel`,
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('requests a short-lived URL and triggers the file download', async () => {
    requestMock
      .mockResolvedValueOnce(job('succeeded'))
      .mockResolvedValueOnce(inspection)
      .mockResolvedValueOnce({
        url: 'https://objects.example/token',
        expires_at: '2026-08-06T10:05:00Z',
      });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
    render(<DownloadJobPage jobId={job().id} />);

    fireEvent.click(await screen.findByRole('button', { name: '获取文件' }));

    await waitFor(() => expect(click).toHaveBeenCalledOnce());
    expect(requestMock).toHaveBeenNthCalledWith(
      3,
      `/api/v1/downloads/${job().id}/download-url`,
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('shows request errors and retries on demand', async () => {
    requestMock
      .mockRejectedValueOnce(
        new ApiError(404, 'not_found', 'Not found', '任务不存在'),
      )
      .mockResolvedValueOnce(job('queued'))
      .mockResolvedValueOnce(inspection);
    render(<DownloadJobPage jobId={job().id} />);

    expect(await screen.findByText('任务不存在')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /重\s*试/ }));

    expect(await screen.findByText('等待处理')).toBeInTheDocument();
    expect(requestMock).toHaveBeenCalledTimes(3);
  });

  it('renders a terminal failure and its stable fallback code', async () => {
    const failed = { ...job('failed'), error_code: null };
    requestMock.mockResolvedValueOnce(failed).mockResolvedValueOnce(inspection);

    render(<DownloadJobPage jobId={failed.id} />);

    expect(await screen.findByText('下载失败')).toBeInTheDocument();
    expect(screen.getByText('错误代码：unknown_error')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '取消任务' }),
    ).not.toBeInTheDocument();
  });

  it('reports cancel failures without losing the current job', async () => {
    requestMock
      .mockResolvedValueOnce(job('running'))
      .mockResolvedValueOnce(inspection)
      .mockRejectedValueOnce(
        new ApiError(409, 'not_cancellable', '冲突', '任务无法取消'),
      );
    render(<DownloadJobPage jobId={job().id} pollIntervalMs={60_000} />);

    fireEvent.click(await screen.findByRole('button', { name: '取消任务' }));

    expect(await screen.findByText('任务无法取消')).toBeInTheDocument();
    expect(screen.getByText('下载中')).toBeInTheDocument();
  });

  it('reports download-url failures', async () => {
    requestMock
      .mockResolvedValueOnce(job('succeeded'))
      .mockResolvedValueOnce(inspection)
      .mockRejectedValueOnce(
        new ApiError(503, 'storage_unavailable', '不可用', '文件暂不可用'),
      );
    render(<DownloadJobPage jobId={job().id} />);

    fireEvent.click(await screen.findByRole('button', { name: '获取文件' }));

    expect(await screen.findByText('文件暂不可用')).toBeInTheDocument();
  });
});
