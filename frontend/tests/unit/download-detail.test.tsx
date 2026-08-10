import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import DownloadJobView from '@/components/download-job-view';
import { ApiError } from '@/requestErrorConfig';
import { analysisSkills } from '../fixtures/analysis-fixtures';
import { inspection, job } from '../fixtures/download-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';

const runtime = vi.hoisted(() => ({
  push: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: runtime.push }),
}));

describe('DownloadJobView', () => {
  beforeEach(() => {
    runtime.push.mockReset();
    window.history.replaceState({}, '', '/downloads/detail/');
  });

  it('polls until the job succeeds and exposes analysis', async () => {
    mockHttpResponses(job('running'), inspection, job('succeeded'));
    render(<DownloadJobView jobId={job().id} pollIntervalMs={5} />);

    expect((await screen.findAllByText('正在下载')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('下载已完成')).length).toBeGreaterThan(
      0,
    );
    expect(
      screen.getByRole('heading', { level: 1, name: inspection.title }),
    ).toBeInTheDocument();
    expect(screen.queryByText('Download status')).not.toBeInTheDocument();
    expect(screen.queryByText('AI analysis')).not.toBeInTheDocument();
    expect(screen.getByText('已完成')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'AI 智能分析' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回上一步' })).toHaveAttribute(
      'href',
      '/history',
    );
  });

  it('cancels an active download', async () => {
    mockHttpResponses(job('running'), inspection, job('cancelled'));
    render(<DownloadJobView jobId={job().id} pollIntervalMs={60_000} />);

    const trigger = await screen.findByRole('button', { name: '取消任务' });
    fireEvent.click(trigger);

    const dialog = await screen.findByRole('alertdialog', {
      name: '取消当前下载任务？',
    });
    expect(dialog).toHaveTextContent(
      '确认后将停止当前下载。取消后可在当前页面重新下载。',
    );
    expect(httpRequests()).toHaveLength(2);

    const keepDownloading = screen.getByRole('button', { name: '继续下载' });
    await waitFor(() => expect(keepDownloading).toHaveFocus());
    fireEvent.click(keepDownloading);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(httpRequests()).toHaveLength(2);

    fireEvent.click(trigger);
    fireEvent.click(
      await screen.findByRole('button', { name: '确认取消下载' }),
    );
    expect((await screen.findAllByText('任务已取消')).length).toBeGreaterThan(
      0,
    );
    expect(httpRequests()[2]?.url).toBe(`/api/downloads/${job().id}/cancel`);
  });

  it.each(['failed', 'cancelled'] as const)(
    'creates a new download when a %s task is retried',
    async (status) => {
      const retried = {
        ...job('queued'),
        id: '44444444-4444-4444-8444-444444444444',
      };
      mockHttpResponses(job(status), inspection, retried);
      render(<DownloadJobView jobId={job().id} pollIntervalMs={60_000} />);

      fireEvent.click(await screen.findByRole('button', { name: '重新下载' }));

      await waitFor(() =>
        expect(runtime.push).toHaveBeenCalledWith(
          `/downloads/detail?jobId=${retried.id}`,
        ),
      );
      expect(httpRequests()[2]).toMatchObject({
        method: 'POST',
        url: `/api/downloads/${job().id}/retry`,
        headers: { 'Idempotency-Key': expect.any(String) },
      });
    },
  );

  it('issues a short-lived URL for completed downloads', async () => {
    mockHttpResponses(job('succeeded'), inspection, analysisSkills, {
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
