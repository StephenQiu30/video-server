import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ScreenplayAnalysisPanel from '@/components/screenplay/screenplay-analysis-panel';
import { httpClient } from '@/lib/request';
import {
  screenplayAnalysisJob,
  screenplaySkills,
} from '../fixtures/screenplay-analysis-fixtures';
import { httpRequests, mockHttpResponses } from '../helpers/http';

const documentId = '99999999-9999-4999-8999-999999999999';

describe('ScreenplayAnalysisPanel', () => {
  beforeEach(() => {
    vi.mocked(httpClient.request).mockReset();
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => 'screenplay-key') });
  });

  it('discloses cloud processing and creates a document-bound task', async () => {
    mockHttpResponses(
      screenplaySkills,
      null,
      screenplayAnalysisJob('analysis', 'queued'),
    );
    render(<ScreenplayAnalysisPanel documentId={documentId} />);

    expect(await screen.findByLabelText('剧本 Skill')).toHaveAttribute(
      'id',
      'screenplay-analysis-skill',
    );
    expect(screen.getByLabelText('分析或改写要求')).toHaveValue(
      '重点分析故事结构、人物弧光、场景功能、节奏与对白。',
    );
    expect(screen.getByText(/规范化剧本文本、任务指令/)).toBeInTheDocument();
    expect(screen.getByText(/不能使用文件、Shell、网络/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '开始剧本分析' }));
    expect(await screen.findByText('等待分析')).toBeInTheDocument();
    const create = httpRequests().find((request) => request.method === 'POST');
    expect(create?.url).toBe(`/api/documents/${documentId}/analyses`);
    expect(create?.headers?.['Idempotency-Key']).toBe('screenplay-key');
    expect(
      httpRequests().some(
        (request) =>
          request.method === 'GET' &&
          request.url === `/api/documents/${documentId}/analysis`,
      ),
    ).toBe(true);
  });

  it('turns the primary action into a rewrite action for the rewrite Skill', async () => {
    mockHttpResponses(screenplaySkills, null);
    render(<ScreenplayAnalysisPanel documentId={documentId} />);

    fireEvent.click(await screen.findByLabelText('剧本 Skill'));
    fireEvent.click(await screen.findByRole('option', { name: '剧本改写' }));

    expect(screen.getByRole('button', { name: '开始剧本改写' })).toBeEnabled();
    expect(screen.getByLabelText('分析或改写要求')).toHaveValue(
      '保持故事意图与剧本格式，使用自然、可拍摄的表达。',
    );
  });

  it('renders the screenplay evidence reading path', async () => {
    mockHttpResponses(screenplaySkills, screenplayAnalysisJob('analysis'));
    render(<ScreenplayAnalysisPanel documentId={documentId} />);

    expect(
      await screen.findByRole('heading', { name: '午夜来客' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/剪辑师必须在天亮前/)).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '结构' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '人物' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '场景' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '对白' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '修改建议' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '导出 DOCX' })).toHaveAttribute(
      'href',
      `/api/analyses/${screenplayAnalysisJob('analysis').id}/report.docx`,
    );
  });

  it('keeps rewritten text in the canonical report view', async () => {
    mockHttpResponses(screenplaySkills, screenplayAnalysisJob('rewrite'));
    render(<ScreenplayAnalysisPanel documentId={documentId} />);

    expect(
      await screen.findByRole('heading', { name: '剧本改写已完成' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Lin Zhou')).toBeInTheDocument();
    expect(screen.getByText('统一人物名译法。')).toBeInTheDocument();
    const reportTab = screen.getByRole('tab', { name: '改写正文' });
    fireEvent.mouseDown(reportTab, { button: 0, ctrlKey: false });
    fireEvent.click(reportTab);
    const preview = await screen.findByLabelText('Markdown 分析报告预览');
    expect(
      within(preview).getByText('Rewritten screenplay'),
    ).toBeInTheDocument();
    expect(screen.getByText(/仅用于改写与本地化参考/)).toBeInTheDocument();
  });

  it('explains screenplay resource failures without implying partial output', async () => {
    const failed = {
      ...screenplayAnalysisJob('rewrite', 'failed'),
      error_code: 'analysis_resource_limit',
    } satisfies API.AnalysisResponse;
    mockHttpResponses(screenplaySkills, failed);
    render(<ScreenplayAnalysisPanel documentId={documentId} />);

    expect(
      await screen.findByText(
        '剧本任务达到当前执行器资源上限，未发布部分结果；请稍后重试，持续出现时联系管理员调整分析配置。',
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重试任务' })).toBeEnabled();
  });
});
