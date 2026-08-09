import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import AnalysisPanel from '@/components/analysis-panel';
import AnalysisResultView from '@/components/analysis-result-view';
import { ApiError } from '@/requestErrorConfig';
import { analysisJob, analysisResult } from '../fixtures/analysis-fixtures';
import { job } from '../fixtures/download-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';

describe('AnalysisPanel', () => {
  it('offers a focused profile and language configuration', () => {
    render(<AnalysisPanel downloadId={job().id} />);
    expect(
      screen.getByRole('heading', { name: 'AI 智能分析' }),
    ).toBeInTheDocument();
    expect(screen.queryByText('AI analysis')).not.toBeInTheDocument();
    expect(screen.getByLabelText('分析模板')).toHaveAttribute(
      'id',
      'analysis-profile',
    );
    expect(screen.getByLabelText('输出语言')).toHaveAttribute(
      'id',
      'analysis-language',
    );
    expect(screen.getByRole('button', { name: '开始 AI 分析' })).toBeEnabled();
  });

  it('creates, polls and renders a structured result', async () => {
    mockHttpResponses(analysisJob('running'), analysisJob('succeeded'));
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => 'analysis-key') });
    render(<AnalysisPanel downloadId={job().id} pollIntervalMs={5} />);

    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));
    expect(await screen.findByText('分析已完成')).toBeInTheDocument();
    expect(screen.getByText('可靠的视频处理流水线')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '视觉摘要' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '分镜' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '高光' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '资产' })).toBeInTheDocument();
  });

  it('exposes shot timestamps for a video player integration', () => {
    const onSelectTime = vi.fn();
    render(
      <AnalysisResultView
        onSelectTime={onSelectTime}
        result={analysisResult}
      />,
    );

    fireEvent.click(screen.getAllByRole('button', { name: '0:30' })[0]);
    expect(onSelectTime).toHaveBeenCalledWith(30_000);
  });

  it('renders empty highlight and asset states', async () => {
    render(
      <AnalysisResultView
        result={{ ...analysisResult, assets: [], highlights: [] }}
      />,
    );

    const highlightsTab = screen.getByRole('tab', { name: '高光' });
    fireEvent.mouseDown(highlightsTab, { button: 0, ctrlKey: false });
    fireEvent.click(highlightsTab);
    expect(
      await screen.findByText('未识别出独立视觉高光。'),
    ).toBeInTheDocument();
    const assetsTab = screen.getByRole('tab', { name: '资产' });
    fireEvent.mouseDown(assetsTab, { button: 0, ctrlKey: false });
    fireEvent.click(assetsTab);
    expect(
      await screen.findByText('未识别出可复用的视觉资产。'),
    ).toBeInTheDocument();
  });

  it('cancels an active analysis task', async () => {
    mockHttpResponses(analysisJob('running'), analysisJob('cancelled'));
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => 'analysis-key') });
    render(<AnalysisPanel downloadId={job().id} pollIntervalMs={60_000} />);

    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));
    const trigger = await screen.findByRole('button', { name: '取消分析' });
    fireEvent.click(trigger);

    expect(
      await screen.findByRole('alertdialog', {
        name: '取消当前分析任务？',
      }),
    ).toHaveTextContent('确认后将停止当前分析。你之后仍可重新发起分析任务。');
    expect(httpRequests()).toHaveLength(1);

    const keepAnalyzing = screen.getByRole('button', { name: '继续分析' });
    await waitFor(() => expect(keepAnalyzing).toHaveFocus());
    fireEvent.click(keepAnalyzing);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(httpRequests()).toHaveLength(1);

    fireEvent.click(trigger);
    fireEvent.click(
      await screen.findByRole('button', { name: '确认取消分析' }),
    );
    expect(await screen.findByText('分析已取消')).toBeInTheDocument();
    expect(httpRequests()[1]?.url).toContain('/cancel');
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
