import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import DownloadJobView from '@/components/downloads/download-job-view';
import { ApiError } from '@/lib/request-error';
import { analysisSkills } from '../fixtures/analysis-fixtures';
import { inspection, job } from '../fixtures/download-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';
import { emitTaskUpdate } from '../helpers/websocket';

const runtime = vi.hoisted(() => ({
  preview: {
    error: null as string | null,
    loading: false,
    reload: vi.fn(),
    reportPlaybackError: vi.fn(),
    source: 'data:video/mp4;base64,AAAA' as string | null,
  },
  push: vi.fn(),
}));

const signedVideoUrl = {
  url: 'https://objects.example/token',
  expires_at: '2026-08-06T10:05:00Z',
};

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: runtime.push }),
}));

vi.mock('@/hooks/useVideoPreviewSource', () => ({
  useVideoPreviewSource: () => runtime.preview,
}));

describe('DownloadJobView', () => {
  beforeEach(() => {
    runtime.preview.error = null;
    runtime.preview.loading = false;
    runtime.preview.reload.mockReset();
    runtime.preview.source = 'data:video/mp4;base64,AAAA';
    runtime.push.mockReset();
    window.history.replaceState({}, '', '/downloads/detail/');
  });

  it('uses WebSocket state until the job succeeds and exposes analysis', async () => {
    mockHttpResponses(job('running'), job('succeeded'), analysisSkills, null);
    render(<DownloadJobView jobId={job().id} pollIntervalMs={5} />);

    expect((await screen.findAllByText('正在下载')).length).toBeGreaterThan(0);
    emitTaskUpdate('download', job('running').id, 2);
    expect((await screen.findAllByText('下载已完成')).length).toBeGreaterThan(
      0,
    );
    expect(
      screen.getByRole('heading', { level: 1, name: inspection.title }),
    ).toBeInTheDocument();
    expect(screen.queryByText('Download status')).not.toBeInTheDocument();
    expect(screen.queryByText('AI analysis')).not.toBeInTheDocument();
    expect(screen.getByText('持久保存')).toBeInTheDocument();
    expect(screen.queryByText('100%')).not.toBeInTheDocument();
    expect(
      screen.getByRole('region', {
        name: `${inspection.title}视频预览`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'AI 智能分析' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回上一步' })).toHaveAttribute(
      'href',
      '/history',
    );
  });

  it('cancels an active download', async () => {
    mockHttpResponses(job('running'), job('cancelled'));
    render(<DownloadJobView jobId={job().id} pollIntervalMs={60_000} />);

    const trigger = await screen.findByRole('button', { name: '取消任务' });
    fireEvent.click(trigger);

    const dialog = await screen.findByRole('alertdialog', {
      name: '取消当前下载任务？',
    });
    expect(dialog).toHaveTextContent(
      '确认后将停止当前下载。取消后可在当前页面重新下载。',
    );
    expect(httpRequests()).toHaveLength(1);

    const keepDownloading = screen.getByRole('button', { name: '继续下载' });
    await waitFor(() => expect(keepDownloading).toHaveFocus());
    fireEvent.click(keepDownloading);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(httpRequests()).toHaveLength(1);

    fireEvent.click(trigger);
    fireEvent.click(
      await screen.findByRole('button', { name: '确认取消下载' }),
    );
    expect((await screen.findAllByText('任务已取消')).length).toBeGreaterThan(
      0,
    );
    expect(httpRequests()[1]?.url).toBe(`/api/downloads/${job().id}/cancel`);
  });

  it.each(['failed', 'cancelled'] as const)(
    'creates a new download when a %s task is retried',
    async (status) => {
      const retried = {
        ...job('queued'),
        id: '44444444-4444-4444-8444-444444444444',
      };
      mockHttpResponses(job(status), retried);
      render(<DownloadJobView jobId={job().id} pollIntervalMs={60_000} />);

      fireEvent.click(await screen.findByRole('button', { name: '重新下载' }));

      await waitFor(() =>
        expect(runtime.push).toHaveBeenCalledWith(
          `/downloads/detail?jobId=${retried.id}`,
        ),
      );
      expect(httpRequests()[1]).toMatchObject({
        method: 'POST',
        url: `/api/downloads/${job().id}/retry`,
        headers: { 'Idempotency-Key': expect.any(String) },
      });
    },
  );

  it('shows a Chinese message for a failed download', async () => {
    mockHttpResponses(job('failed'));
    render(<DownloadJobView jobId={job().id} pollIntervalMs={60_000} />);

    expect(
      await screen.findByText('视频下载超时，请稍后重试。'),
    ).toBeInTheDocument();
    expect(screen.queryByText('download_timeout')).not.toBeInTheDocument();
  });

  it('issues a short-lived URL for completed downloads', async () => {
    mockHttpResponses(job('succeeded'), analysisSkills, null, signedVideoUrl);
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
    render(<DownloadJobView jobId={job().id} />);

    fireEvent.click(
      await screen.findByRole('button', { name: '获取视频文件' }),
    );
    await waitFor(() => expect(click).toHaveBeenCalledOnce());
  });

  it('offers a new download when a completed file has been cleaned', async () => {
    mockHttpResponses(
      { ...job('succeeded'), file_available: false },
      analysisSkills,
      null,
    );
    render(<DownloadJobView jobId={job().id} />);

    expect(
      await screen.findByRole('button', { name: '重新下载' }),
    ).toBeInTheDocument();
    expect(screen.getByText('视频文件已清理')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '获取视频文件' }),
    ).not.toBeInTheDocument();
  });

  it('offers to reload an unavailable preview', async () => {
    runtime.preview.error = '预览地址已失效。';
    runtime.preview.source = null;
    mockHttpResponses(job('succeeded'), analysisSkills, null);
    render(<DownloadJobView jobId={job().id} />);

    expect(await screen.findByText('暂时无法预览视频')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重新加载预览' }));
    expect(runtime.preview.reload).toHaveBeenCalledOnce();
  });

  it('keeps a completed task usable after inspection metadata expires', async () => {
    mockHttpResponses(job('succeeded'), analysisSkills, null);
    render(<DownloadJobView jobId={job().id} />);

    await screen.findByRole('heading', { level: 1, name: inspection.title });
    expect(
      screen.queryByText(
        '原始媒体信息已过期，下载任务和已生成文件仍可继续使用。',
      ),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '下载已完成' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('region', {
        name: `${inspection.title}视频预览`,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText('1920×1080')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'AI 智能分析' }),
    ).toBeInTheDocument();
  });

  it('renders stable task errors without leaking details', async () => {
    mockHttpError(new ApiError(404, 'not_found', 'Not found', '任务不存在'));
    render(<DownloadJobView jobId={job().id} />);
    expect(
      await screen.findByText('任务或相关资源不存在，请返回下载记录确认。'),
    ).toBeInTheDocument();
  });
});
