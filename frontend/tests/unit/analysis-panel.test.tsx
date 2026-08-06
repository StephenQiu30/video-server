import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import AnalysisPanel from '@/features/analysis/AnalysisPanel';
import { analysisJob } from './analysis-fixtures';
import { job, jsonResponse } from './download-fixtures';

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('AnalysisPanel', () => {
  it('offers the minimum profile and output-language configuration', () => {
    render(<AnalysisPanel downloadId={job().id} />);

    expect(
      screen.getByRole('heading', { name: 'AI 智能分析' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('分析模板')).toHaveValue('standard-v1');
    expect(screen.getByLabelText('输出语言')).toHaveValue('zh-CN');
    expect(screen.getByRole('button', { name: '开始 AI 分析' })).toBeEnabled();
  });

  it('creates, polls serially, and renders every structured result section', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(analysisJob('running'), 202))
      .mockResolvedValueOnce(jsonResponse(analysisJob('succeeded')));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn().mockReturnValue('analysis-key'),
    });
    render(<AnalysisPanel downloadId={job().id} pollIntervalMs={5} />);

    fireEvent.change(screen.getByLabelText('输出语言'), {
      target: { value: 'en-US' },
    });
    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));

    expect(await screen.findByText('分析中')).toBeInTheDocument();
    expect(await screen.findByText('分析已完成')).toBeInTheDocument();
    expect(
      screen.getByText('如何构建可靠的视频处理流水线'),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '摘要' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '关键要点' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '行动建议' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '章节' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '思维导图' }),
    ).toBeInTheDocument();
    expect(screen.getByText('视频下载')).toBeInTheDocument();
    expect(screen.getByText('AI 分析')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('cancels an active analysis task', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(analysisJob('running'), 202))
      .mockResolvedValueOnce(jsonResponse(analysisJob('cancelled')));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn().mockReturnValue('analysis-key'),
    });
    render(<AnalysisPanel downloadId={job().id} pollIntervalMs={60_000} />);

    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));
    fireEvent.click(await screen.findByRole('button', { name: '取消分析' }));

    expect(await screen.findByText('分析已取消')).toBeInTheDocument();
    expect(fetchMock.mock.calls[1][0]).toBe(
      `/api/v1/analyses/${analysisJob().id}/cancel`,
    );
  });

  it('shows a stable task error and permits a fresh analysis', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(analysisJob('failed'), 202)),
    );
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn().mockReturnValue('analysis-key'),
    });
    render(<AnalysisPanel downloadId={job().id} />);

    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));

    expect(await screen.findByText('分析失败')).toBeInTheDocument();
    expect(
      screen.getByText('错误代码：analysis_provider_failed'),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重新分析' }));
    expect(
      screen.getByRole('button', { name: '开始 AI 分析' }),
    ).toBeInTheDocument();
  });

  it('shows RFC9457 creation errors and keeps retries idempotent', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(
          {
            status: 503,
            code: 'analysis_unavailable',
            title: '服务不可用',
            detail: 'AI 分析服务暂时不可用',
          },
          503,
        ),
      )
      .mockResolvedValueOnce(jsonResponse(analysisJob(), 202));
    vi.stubGlobal('fetch', fetchMock);
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

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const firstHeaders = fetchMock.mock.calls[0][1]?.headers as Record<
      string,
      string
    >;
    const secondHeaders = fetchMock.mock.calls[1][1]?.headers as Record<
      string,
      string
    >;
    expect(firstHeaders['Idempotency-Key']).toBe('stable-key');
    expect(secondHeaders['Idempotency-Key']).toBe('stable-key');
  });
});
