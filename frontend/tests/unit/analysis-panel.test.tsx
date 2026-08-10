import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import AnalysisPanel from '@/components/analysis-panel';
import AnalysisReportPreview from '@/components/analysis-report-preview';
import AnalysisResultView from '@/components/analysis-result-view';
import { httpClient } from '@/lib/request';
import { ApiError } from '@/lib/request-error';
import type { AnalysisJob } from '@/types/video';
import {
  analysisJob,
  analysisResult,
  analysisSkills,
} from '../fixtures/analysis-fixtures';
import { job } from '../fixtures/download-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';
import { emitTaskUpdate } from '../helpers/websocket';

describe('AnalysisPanel', () => {
  beforeEach(() => {
    mockHttpResponses(analysisSkills, null);
  });

  it('loads analysis skills and exposes an editable prompt', async () => {
    render(<AnalysisPanel downloadId={job().id} />);
    expect(
      screen.getByRole('heading', { name: 'AI 智能分析' }),
    ).toBeInTheDocument();
    expect(screen.queryByText('AI analysis')).not.toBeInTheDocument();
    expect(await screen.findByLabelText('分析 Skill')).toHaveAttribute(
      'id',
      'analysis-skill',
    );
    expect(screen.getByLabelText('输出语言')).toHaveAttribute(
      'id',
      'analysis-language',
    );
    expect(screen.getByLabelText('分析提示词')).toHaveValue(
      '逐镜头分析画面、叙事作用和高光价值。',
    );
    expect(screen.getByText('导演拉片')).toBeInTheDocument();
    expect(screen.queryByText('0/4000')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '开始 AI 分析' })).toBeEnabled();
  });

  it('restores the latest persisted analysis after a page load', async () => {
    vi.mocked(httpClient.request).mockReset();
    mockHttpResponses(analysisSkills, analysisJob('succeeded'));

    render(<AnalysisPanel downloadId={job().id} />);

    expect(await screen.findByText('第 1 次执行已完成')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '导出 DOCX' })).toHaveAttribute(
      'href',
      `/api/analyses/${analysisJob('succeeded').id}/report.docx`,
    );
  });

  it('creates, receives WebSocket state and renders a structured result', async () => {
    mockHttpResponses(analysisJob('running'), analysisJob('succeeded'));
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => 'analysis-key') });
    render(<AnalysisPanel downloadId={job().id} pollIntervalMs={5} />);

    fireEvent.change(await screen.findByLabelText('分析提示词'), {
      target: { value: '重点识别产品功能演示。' },
    });
    fireEvent.click(screen.getByRole('button', { name: '开始 AI 分析' }));
    await screen.findByText('正在分析');
    emitTaskUpdate('analysis', analysisJob('running').id, 2);
    expect(await screen.findByText('第 1 次执行已完成')).toBeInTheDocument();
    expect(httpRequests()[2]?.data).toEqual({
      skill_id: 'director-breakdown',
      output_language: 'zh-CN',
      custom_prompt: '重点识别产品功能演示。',
    });
    expect(screen.getByText('可靠的视频处理流水线')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '视觉摘要' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '分镜' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '高光' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '资产' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '报告预览' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '导出 DOCX' })).toHaveAttribute(
      'href',
      `/api/analyses/${analysisJob('succeeded').id}/report.docx`,
    );
    expect(screen.getByRole('link', { name: '导出 Markdown' })).toHaveAttribute(
      'href',
      `/api/analyses/${analysisJob('succeeded').id}/report.md`,
    );

    const reportTab = screen.getByRole('tab', { name: '报告预览' });
    fireEvent.mouseDown(reportTab, { button: 0, ctrlKey: false });
    fireEvent.click(reportTab);
    const preview = await screen.findByLabelText('Markdown 分析报告预览');
    expect(within(preview).getByText('一、基础信息')).toBeInTheDocument();
  });

  it('renders Markdown without executable HTML or outbound links', () => {
    render(
      <AnalysisReportPreview
        markdown={
          '# 报告\n\n<script>x</script>\n\n[外链](https://invalid.example)'
        }
      />,
    );

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(document.querySelector('script')).not.toBeInTheDocument();
    expect(screen.getByText('外链')).toBeInTheDocument();
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

    fireEvent.click(
      await screen.findByRole('button', { name: '开始 AI 分析' }),
    );
    const trigger = await screen.findByRole('button', { name: '取消分析' });
    fireEvent.click(trigger);

    expect(
      await screen.findByRole('alertdialog', {
        name: '取消当前分析任务？',
      }),
    ).toHaveTextContent('确认后将停止当前分析。你之后仍可重新发起分析任务。');
    expect(httpRequests()).toHaveLength(3);

    const keepAnalyzing = screen.getByRole('button', { name: '继续分析' });
    await waitFor(() => expect(keepAnalyzing).toHaveFocus());
    fireEvent.click(keepAnalyzing);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(httpRequests()).toHaveLength(3);

    fireEvent.click(trigger);
    fireEvent.click(
      await screen.findByRole('button', { name: '确认取消分析' }),
    );
    expect(await screen.findByText('分析已取消')).toBeInTheDocument();
    expect(httpRequests()[3]?.url).toContain('/cancel');
  });

  it('retries the same analysis id with an idempotency key', async () => {
    const failed = analysisJob('failed');
    const retried = {
      ...analysisJob('queued'),
      id: failed.id,
      run_id: '66666666-6666-4666-8666-666666666666',
      run_no: 2,
      run_trigger: 'manual_retry',
      version: failed.version + 1,
    } satisfies AnalysisJob;
    mockHttpResponses(failed, retried);
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => 'stable-action-key') });
    render(<AnalysisPanel downloadId={job().id} pollIntervalMs={60_000} />);

    fireEvent.click(
      await screen.findByRole('button', { name: '开始 AI 分析' }),
    );
    fireEvent.click(await screen.findByRole('button', { name: '重试分析' }));

    expect(await screen.findByText(/第 2 次执行/)).toBeInTheDocument();
    const retryRequest = httpRequests()[3];
    expect(retryRequest?.url).toContain(`/analyses/${failed.id}/retry`);
    expect(retryRequest?.headers?.['Idempotency-Key']).toBe(
      'stable-action-key',
    );
    expect(retried.id).toBe(failed.id);
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
    fireEvent.click(
      await screen.findByRole('button', { name: '开始 AI 分析' }),
    );
    expect(
      await screen.findByText('AI 分析服务暂时不可用'),
    ).toBeInTheDocument();
  });
});
