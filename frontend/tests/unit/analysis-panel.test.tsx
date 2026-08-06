import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { request } from '@umijs/max';
import { describe, expect, it, vi } from 'vitest';

import AnalysisPanel from '@/components/AnalysisPanel';
import { ApiError } from '@/requestErrorConfig';
import { analysisJob } from './analysis-fixtures';
import { job } from './download-fixtures';

const requestMock = vi.mocked(request);

describe('AnalysisPanel', () => {
  it('offers the minimum profile and output-language configuration', () => {
    render(<AnalysisPanel downloadId={job().id} />);

    expect(
      screen.getByRole('heading', { name: 'AI 智能分析' }),
    ).toBeInTheDocument();
    expect(screen.getByText('标准分析')).toBeInTheDocument();
    expect(screen.getByText('简体中文')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '开始 AI 分析' })).toBeEnabled();
  });

  it('creates, polls serially, and renders every structured result section', async () => {
    requestMock
      .mockResolvedValueOnce(analysisJob('running'))
      .mockResolvedValueOnce(analysisJob('succeeded'));
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn().mockReturnValue('analysis-key'),
    });
    render(<AnalysisPanel downloadId={job().id} pollIntervalMs={5} />);

    fireEvent.mouseDown(screen.getByLabelText('输出语言'));
    fireEvent.click(await screen.findByText('English'));
    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));

    expect(await screen.findByText('分析已完成')).toBeInTheDocument();
    expect(
      screen.getByText('如何构建可靠的视频处理流水线'),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '摘要' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '关键要点' }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: '行动项' }));
    expect(
      screen.getByRole('heading', { name: '行动建议' }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: '摘要' }));
    expect(screen.getByRole('heading', { name: '章节' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: '思维导图' }));
    expect(
      screen.getByRole('heading', { name: '思维导图' }),
    ).toBeInTheDocument();
    expect(screen.getAllByText('视频下载').length).toBeGreaterThan(0);
    expect(screen.getAllByText('AI 分析').length).toBeGreaterThan(0);
    expect(requestMock).toHaveBeenCalledTimes(2);
  });

  it('cancels an active analysis task', async () => {
    requestMock
      .mockResolvedValueOnce(analysisJob('running'))
      .mockResolvedValueOnce(analysisJob('cancelled'));
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn().mockReturnValue('analysis-key'),
    });
    render(<AnalysisPanel downloadId={job().id} pollIntervalMs={60_000} />);

    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));
    fireEvent.click(await screen.findByRole('button', { name: '取消分析' }));

    expect(await screen.findByText('分析已取消')).toBeInTheDocument();
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      `/api/v1/analyses/${analysisJob().id}/cancel`,
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('shows a stable task error and permits a fresh analysis', async () => {
    requestMock.mockResolvedValue(analysisJob('failed'));
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn().mockReturnValue('analysis-key'),
    });
    render(<AnalysisPanel downloadId={job().id} />);

    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));

    expect(await screen.findByText('分析失败')).toBeInTheDocument();
    expect(
      screen.getByText('错误代码：provider_unavailable'),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重新分析' }));
    expect(
      screen.getByRole('button', { name: '开始 AI 分析' }),
    ).toBeInTheDocument();
  });

  it('shows creation errors and keeps retries idempotent', async () => {
    requestMock
      .mockRejectedValueOnce(
        new ApiError(
          503,
          'analysis_unavailable',
          '服务不可用',
          'AI 分析服务暂时不可用',
        ),
      )
      .mockResolvedValueOnce(analysisJob());
    vi.stubGlobal('crypto', {
      randomUUID: vi
        .fn()
        .mockReturnValueOnce('stable-key')
        .mockReturnValueOnce('unused-key'),
    });
    render(<AnalysisPanel downloadId={job().id} />);

    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));
    expect(
      await screen.findByText('AI 分析服务暂时不可用'),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));

    await waitFor(() => expect(requestMock).toHaveBeenCalledTimes(2));
    expect(requestHeader(0, 'Idempotency-Key')).toBe('stable-key');
    expect(requestHeader(1, 'Idempotency-Key')).toBe('stable-key');
  });
});

function requestHeader(index: number, name: string) {
  const [, options] = requestMock.mock.calls[index] as unknown as [
    string,
    {
      headers?: Record<string, string>;
    },
  ];
  return options.headers?.[name];
}
