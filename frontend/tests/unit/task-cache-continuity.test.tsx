import { useQueryClient } from '@tanstack/react-query';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAnalysisJob } from '@/components/analysis/use-analysis-job';
import { useDownloadJob } from '@/components/downloads/use-download-job';
import { QueryProvider } from '@/components/layout/query-provider';
import { privateQueryKey } from '@/lib/query-keys';
import { advanceSessionGeneration } from '@/lib/session-events';
import { analysisJob } from '../fixtures/analysis-fixtures';
import { job } from '../fixtures/download-fixtures';

const runtime = vi.hoisted(() => ({
  get: vi.fn(),
  latest: vi.fn(),
  cancel: vi.fn(),
}));
vi.mock('@/api/downloads', () => ({
  getDownload: runtime.get,
  cancelDownload: runtime.cancel,
}));
vi.mock('@/api/analyses', () => ({
  getLatestDownloadAnalysis: runtime.latest,
  getAnalysis: runtime.get,
  cancelAnalysis: runtime.cancel,
}));
vi.mock('@/lib/task-socket', async (importOriginal) => ({
  ...(await importOriginal()),
  taskSocket: { subscribe: () => () => undefined },
}));

describe.each(['download', 'analysis'] as const)('%s cached detail', (kind) => {
  const useJob = kind === 'download' ? useDownloadJob : useAnalysisJob;
  const active = kind === 'download' ? job('running') : analysisJob('running');
  function Detail() {
    const state = useJob(active.id, 60_000);
    return (
      <>
        <output data-testid="job">{state.job?.id ?? 'none'}</output>
        <output data-testid="status">{state.job?.status}</output>
        <button type="button" onClick={() => void state.cancel()}>
          Cancel
        </button>
        <output data-testid="loading">{String(state.loading)}</output>
        {state.error && <div role="alert">{state.error}</div>}
      </>
    );
  }
  function Routes() {
    const [visible, setVisible] = useState(true);
    const queries = useQueryClient();
    return (
      <>
        <button type="button" onClick={() => setVisible(!visible)}>
          Navigate
        </button>
        <button
          type="button"
          onClick={() =>
            void queries.invalidateQueries({
              queryKey: privateQueryKey(kind),
              refetchType: 'none',
            })
          }
        >
          Mark stale
        </button>
        {visible && <Detail />}
      </>
    );
  }
  beforeEach(() => {
    runtime.get.mockReset().mockResolvedValue(active);
    runtime.latest.mockReset().mockResolvedValue(active);
    runtime.cancel.mockReset();
  });

  it('renders the cached task immediately after leaving and returning', async () => {
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId('job')).toHaveTextContent(active.id),
    );
    runtime.get.mockClear();
    runtime.latest.mockClear();
    fireEvent.click(screen.getByText('Navigate'));
    fireEvent.click(screen.getByText('Navigate'));
    expect(screen.getByTestId('job')).toHaveTextContent(active.id);
    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(runtime.get).not.toHaveBeenCalled();
    expect(runtime.latest).not.toHaveBeenCalled();
  });

  it('retains the task when a background refresh fails', async () => {
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId('job')).toHaveTextContent(active.id),
    );
    fireEvent.click(screen.getByText('Navigate'));
    runtime.get.mockRejectedValue(new Error('offline'));
    fireEvent.click(screen.getByText('Mark stale'));
    fireEvent.click(screen.getByText('Navigate'));
    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    await screen.findByRole('alert');
    expect(screen.getByTestId('job')).toHaveTextContent(active.id);
  });

  it('revalidates the original cache when a mutation completes after navigation', async () => {
    let finish!: (value: typeof active) => void;
    runtime.cancel.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId('job')).toHaveTextContent(active.id),
    );
    fireEvent.click(screen.getByText('Cancel'));
    await waitFor(() => expect(runtime.cancel).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByText('Navigate'));
    const cancelled = { ...active, status: 'cancelled' as const, version: 5 };
    runtime.get.mockResolvedValue(cancelled);
    runtime.latest.mockResolvedValue(cancelled);
    await act(async () => finish(cancelled));
    fireEvent.click(screen.getByText('Navigate'));
    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('cancelled'),
    );
  });

  it('clears cached private tasks before rendering another identity', async () => {
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId('job')).toHaveTextContent(active.id),
    );
    runtime.get.mockImplementation(() => new Promise(() => {}));
    runtime.latest.mockImplementation(() => new Promise(() => {}));
    act(() => advanceSessionGeneration());
    expect(screen.getByTestId('job')).toHaveTextContent('none');
    expect(screen.getByTestId('loading')).toHaveTextContent('true');
  });
});
