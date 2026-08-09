import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import DownloadJobView from '@/components/download-job-view';
import { ApiError } from '@/requestErrorConfig';
import { inspection, job } from '../fixtures/download-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';

describe('DownloadJobView', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/downloads/detail/');
  });

  it('polls until the job succeeds and exposes analysis', async () => {
    mockHttpResponses(job('running'), inspection, job('succeeded'));
    render(<DownloadJobView jobId={job().id} pollIntervalMs={5} />);

    expect((await screen.findAllByText('正在下载')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('下载已完成')).length).toBeGreaterThan(
      0,
    );
    expect(screen.getByText('已完成')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'AI 智能分析' }),
    ).toBeInTheDocument();
  });

  it('cancels an active download', async () => {
    mockHttpResponses(job('running'), inspection, job('cancelled'));
    render(<DownloadJobView jobId={job().id} pollIntervalMs={60_000} />);

    fireEvent.click(await screen.findByRole('button', { name: '取消任务' }));
    expect((await screen.findAllByText('任务已取消')).length).toBeGreaterThan(
      0,
    );
    expect(httpRequests()[2]?.url).toBe(`/api/downloads/${job().id}/cancel`);
  });

  it('issues a short-lived URL for completed downloads', async () => {
    mockHttpResponses(job('succeeded'), inspection, {
      url: 'https://objects.example/token',
      expires_at: '2026-08-06T10:05:00Z',
    });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
    render(<DownloadJobView jobId={job().id} />);

    fireEvent.click(
      await screen.findByRole('button', { name: '获取视频文件' }),
    );
    await waitFor(() => expect(click).toHaveBeenCalledOnce());
  });

  it('renders stable task errors without leaking details', async () => {
    mockHttpError(new ApiError(404, 'not_found', 'Not found', '任务不存在'));
    render(<DownloadJobView jobId={job().id} />);
    expect(await screen.findByText('任务不存在')).toBeInTheDocument();
  });
});
