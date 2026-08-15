import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import DownloadWorkspace from '@/components/download-workspace';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ApiError } from '@/services/download';
import { URL_MESSAGE } from '@/utils/validation';
import {
  inspection,
  job,
  reportedDouyinShareMessage,
} from '../fixtures/download-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';

vi.mock('next/navigation', () => ({}));

describe('DownloadWorkspace', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/');
  });

  it('starts with one focused, accessible inspection form', () => {
    renderWorkspace();

    expect(
      screen.getByRole('heading', { name: /把素材，\s*带回本地。/u }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/^\d{2} \/ /u)).not.toBeInTheDocument();
    expect(screen.queryByText('Public media workflow')).not.toBeInTheDocument();
    expect(screen.queryByText('02 / 选择画质')).not.toBeInTheDocument();
    expect(screen.queryByText('03 / 创建任务')).not.toBeInTheDocument();
    expect(screen.getByLabelText('公开视频地址')).toBeInTheDocument();
    expect(screen.queryByText('⌘V')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '解析媒体' })).toBeEnabled();
    expect(screen.getByRole('tab', { name: '链接解析' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(screen.getByRole('tab', { name: '本地视频' })).toBeEnabled();
    expect(screen.getByRole('tab', { name: '剧本文档' })).toBeEnabled();
    expect(
      screen.queryByRole('region', { name: '解析结果' }),
    ).not.toBeInTheDocument();
  });

  it('offers screenplay import from the same home intake', async () => {
    renderWorkspace();

    fireEvent.mouseDown(screen.getByRole('tab', { name: '剧本文档' }), {
      button: 0,
      ctrlKey: false,
    });
    expect(screen.getByLabelText('选择剧本文档文件')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '上传并解析' }));
    expect(
      await screen.findByText('请先选择一份剧本文档。'),
    ).toBeInTheDocument();
  });

  it('rejects an invalid address before making an API request', async () => {
    renderWorkspace();

    const input = screen.getByLabelText('公开视频地址');
    fireEvent.change(input, {
      target: { value: 'file:///tmp/private-video' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    const error = await screen.findByText(URL_MESSAGE);
    expect(error).toHaveAttribute('id', 'download-workspace-error');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute(
      'aria-describedby',
      'download-workspace-error',
    );
    expect(httpRequests()).toHaveLength(0);
  });

  it('normalizes the reported Douyin share message before inspection', async () => {
    mockHttpResponses(inspection);
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: reportedDouyinShareMessage },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(httpRequests()[0]).toMatchObject({
      data: { url: 'https://v.douyin.com/Tq0eYJRMYRk/' },
      method: 'POST',
      url: '/api/inspections',
    });
  });

  it('does not mark the URL field invalid when inspection fails downstream', async () => {
    mockHttpError(
      new ApiError(504, 'inspection_timeout', '解析超时', '媒体解析超时。'),
    );
    renderWorkspace();

    const input = screen.getByLabelText('公开视频地址');
    fireEvent.change(input, {
      target: { value: 'https://media.example/slow' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(
      await screen.findByText('读取视频信息超时，请稍后重试。'),
    ).toBeInTheDocument();
    expect(input).not.toHaveAttribute('aria-invalid');
    expect(input).not.toHaveAttribute('aria-describedby');
  });

  it('does not mark the URL field invalid when task creation fails', async () => {
    mockHttpResponses(inspection);
    mockHttpError(
      new ApiError(503, 'download_failed', '创建失败', '任务创建失败。'),
    );
    renderWorkspace();

    const input = screen.getByLabelText('公开视频地址');
    fireEvent.change(input, {
      target: { value: 'https://media.example/owned' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
    await screen.findByText(inspection.title);
    fireEvent.click(screen.getByRole('button', { name: '创建下载任务' }));

    expect(await screen.findByText('任务创建失败。')).toBeInTheDocument();
    expect(input).not.toHaveAttribute('aria-invalid');
    expect(input).not.toHaveAttribute('aria-describedby');
  });

  it('inspects a public URL, creates a download, and opens its Next route', async () => {
    mockHttpResponses(inspection, job());
    const assign = vi
      .spyOn(window.location, 'assign')
      .mockImplementation(() => undefined);
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: ' https://media.example/owned ' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '画质预设' }),
    ).toBeInTheDocument();
    expect(screen.getByText('体积优先')).toBeInTheDocument();
    expect(screen.getByRole('radio')).toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: '创建下载任务' }));

    await waitFor(() =>
      expect(assign).toHaveBeenCalledWith(
        `/downloads/detail?jobId=${encodeURIComponent(job().id)}`,
      ),
    );
    expect(httpRequests()).toMatchObject([
      {
        data: { url: 'https://media.example/owned' },
        headers: { 'Idempotency-Key': expect.any(String) },
        method: 'POST',
        url: '/api/inspections',
      },
      {
        data: {
          format_id: inspection.formats[0].id,
          inspection_id: inspection.id,
        },
        headers: { 'Idempotency-Key': expect.any(String) },
        method: 'POST',
        url: '/api/downloads',
      },
    ]);
  });
});

function renderWorkspace() {
  return render(
    <TooltipProvider>
      <DownloadWorkspace />
    </TooltipProvider>,
  );
}
