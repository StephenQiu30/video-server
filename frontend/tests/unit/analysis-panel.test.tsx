import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import AnalysisPanel from '@/components/analysis-panel';
import { ApiError } from '@/requestErrorConfig';
import { analysisJob } from '../fixtures/analysis-fixtures';
import { job } from '../fixtures/download-fixtures';
import { mockHttpError, mockHttpResponses } from '../helpers/http';

describe('AnalysisPanel', () => {
  it('offers a focused profile and language configuration', () => {
    render(<AnalysisPanel downloadId={job().id} />);
    expect(
      screen.getByRole('heading', { name: 'AI 智能分析' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('分析模板')).toBeInTheDocument();
    expect(screen.getByLabelText('输出语言')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '开始 AI 分析' })).toBeEnabled();
  });

  it('creates, polls and renders a structured result', async () => {
    mockHttpResponses(analysisJob('running'), analysisJob('succeeded'));
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => 'analysis-key') });
    render(<AnalysisPanel downloadId={job().id} pollIntervalMs={5} />);

    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));
    expect(await screen.findByText('分析已完成')).toBeInTheDocument();
    expect(
      screen.getByText('如何构建可靠的视频处理流水线'),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '摘要' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '行动项' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '思维导图' })).toBeInTheDocument();
  });

  it('cancels an active analysis task', async () => {
    mockHttpResponses(analysisJob('running'), analysisJob('cancelled'));
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => 'analysis-key') });
    render(<AnalysisPanel downloadId={job().id} pollIntervalMs={60_000} />);

    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));
    fireEvent.click(await screen.findByRole('button', { name: '取消分析' }));
    expect(await screen.findByText('分析已取消')).toBeInTheDocument();
  });

  it('shows safe creation errors', async () => {
    mockHttpError(
      new ApiError(
        503,
        'analysis_unavailable',
        '服务不可用',
        'AI 分析服务暂时不可用',
      ),
    );
    render(<AnalysisPanel downloadId={job().id} />);
    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));
    expect(
      await screen.findByText('AI 分析服务暂时不可用'),
    ).toBeInTheDocument();
  });
});
