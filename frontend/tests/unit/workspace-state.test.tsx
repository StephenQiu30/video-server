import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AnalysisConfigurator from '@/components/analysis/analysis-configurator';
import DownloadHistoryView from '@/components/downloads/download-history-view';
import { QueryProvider } from '@/components/layout/query-provider';
import { advanceSessionGeneration } from '@/lib/session-events';
import { analysisSkills } from '../fixtures/analysis-fixtures';

const runtime = vi.hoisted(() => ({ history: vi.fn(), skills: vi.fn() }));
vi.mock('@/api/downloads', () => ({ getDownloadHistory: runtime.history }));
vi.mock('@/api/analyses', () => ({ listAnalysisSkills: runtime.skills }));
vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));

function Routes() {
  const [visible, setVisible] = useState(true);
  const [inputId, setInputId] = useState('first');
  const [kind, setKind] = useState<API.AnalysisInputKind>('video');
  return (
    <>
      <button type="button" onClick={() => setVisible(!visible)}>
        Navigate
      </button>
      <button
        type="button"
        onClick={() => setInputId(inputId === 'first' ? 'second' : 'first')}
      >
        Change input
      </button>
      <button
        type="button"
        onClick={() => setKind(kind === 'video' ? 'screenplay' : 'video')}
      >
        Change kind
      </button>
      {visible && (
        <>
          <DownloadHistoryView />
          <AnalysisConfigurator
            inputId={inputId}
            inputKind={kind}
            busy={false}
            onStart={vi.fn()}
          />
        </>
      )}
    </>
  );
}

describe('private workspace view state', () => {
  beforeEach(() => {
    runtime.history.mockReset().mockResolvedValue({
      items: [],
      page: 1,
      page_size: 20,
      total: 60,
      summary: { total: 60, active: 0, succeeded: 60, failed: 0 },
    });
    runtime.skills.mockReset().mockResolvedValue(analysisSkills);
  });

  it('restores pagination, applied filters and unsubmitted search text separately', async () => {
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    const search = screen.getByRole('textbox', { name: '搜索下载记录' });
    fireEvent.change(search, { target: { value: '已应用' } });
    fireEvent.keyDown(search, { key: 'Enter' });
    fireEvent.click(screen.getByRole('combobox', { name: '按状态筛选' }));
    fireEvent.click(await screen.findByRole('option', { name: '已完成' }));
    fireEvent.click(await screen.findByRole('button', { name: '下一页' }));
    await screen.findByText('2 / 3');
    fireEvent.change(search, { target: { value: '尚未搜索' } });
    fireEvent.click(screen.getByText('Navigate'));
    fireEvent.click(screen.getByText('Navigate'));
    expect(screen.getByRole('textbox', { name: '搜索下载记录' })).toHaveValue(
      '尚未搜索',
    );
    expect(screen.getByText('2 / 3')).toBeInTheDocument();
    expect(
      screen.getByRole('combobox', { name: '按状态筛选' }),
    ).toHaveTextContent('已完成');
    expect(runtime.history).toHaveBeenLastCalledWith(
      expect.objectContaining({
        page: 2,
        search: '已应用',
        status: 'succeeded',
      }),
      expect.anything(),
    );
  });

  it('keeps prompts, skills and language per input and input kind across navigation', async () => {
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    await waitFor(() =>
      expect(screen.getByLabelText('分析 Skill')).toBeEnabled(),
    );
    fireEvent.click(screen.getByLabelText('分析 Skill'));
    fireEvent.click(await screen.findByRole('option', { name: '高光提炼' }));
    fireEvent.click(screen.getByLabelText('输出语言'));
    fireEvent.click(await screen.findByRole('option', { name: 'English' }));
    fireEvent.change(screen.getByLabelText('分析提示词'), {
      target: { value: '只保留这个素材的要求' },
    });
    fireEvent.click(screen.getByText('Navigate'));
    fireEvent.click(screen.getByText('Navigate'));
    expect(screen.getByLabelText('分析提示词')).toHaveValue(
      '只保留这个素材的要求',
    );
    expect(screen.getByLabelText('输出语言')).toHaveTextContent('English');
    expect(screen.getByLabelText('分析 Skill')).toHaveTextContent('高光提炼');
    fireEvent.click(screen.getByText('Change input'));
    expect(screen.getByLabelText('分析提示词')).toHaveValue(
      analysisSkills[0].default_prompt,
    );
    fireEvent.click(screen.getByText('Change input'));
    fireEvent.click(screen.getByText('Change kind'));
    expect(screen.getByLabelText('分析或改写要求')).not.toHaveValue(
      '只保留这个素材的要求',
    );
    fireEvent.click(screen.getByText('Change kind'));
    expect(screen.getByLabelText('分析提示词')).toHaveValue(
      '只保留这个素材的要求',
    );
    expect(sessionStorage.length).toBe(0);
  });

  it('clears filters and prompt drafts when the identity changes', async () => {
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    fireEvent.change(screen.getByRole('textbox', { name: '搜索下载记录' }), {
      target: { value: 'private search' },
    });
    fireEvent.change(screen.getByLabelText('分析提示词'), {
      target: { value: 'private prompt' },
    });
    act(() => advanceSessionGeneration());
    expect(screen.getByRole('textbox', { name: '搜索下载记录' })).toHaveValue(
      '',
    );
    expect(screen.getByLabelText('分析提示词')).not.toHaveValue(
      'private prompt',
    );
  });
});
