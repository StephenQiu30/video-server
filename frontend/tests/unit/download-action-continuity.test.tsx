import { onlineManager, useQueryClient } from '@tanstack/react-query';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { useState } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useDownloadActions } from '@/components/downloads/use-download-actions';
import { useDownloadJob } from '@/components/downloads/use-download-job';
import { QueryProvider } from '@/components/layout/query-provider';
import { privateQueryKey } from '@/lib/query-keys';
import { advanceSessionGeneration } from '@/lib/session-events';
import { job } from '../fixtures/download-fixtures';

const runtime = vi.hoisted(() => ({
  retry: vi.fn(),
  get: vi.fn(),
  remove: vi.fn(),
  issue: vi.fn(),
  download: vi.fn(),
}));
vi.mock('@/api/downloads', () => ({
  retryDownload: runtime.retry,
  getDownload: runtime.get,
  deleteDownload: runtime.remove,
  issueDownloadUrl: runtime.issue,
}));
vi.mock('@/lib/browser-download', () => ({
  triggerBrowserDownload: runtime.download,
}));
vi.mock('@/lib/task-socket', () => ({
  taskSocket: { subscribe: () => () => undefined },
}));

function Actions() {
  const state = useDownloadActions('original');
  const queries = useQueryClient();
  return (
    <>
      <output data-testid="action">{state.action ?? 'idle'}</output>
      <output data-testid="target">{state.retryTarget ?? 'none'}</output>
      <output data-testid="cached">
        {queries.getQueryData<API.DownloadResponse>(
          privateQueryKey('download', 'new-job'),
        )?.id ?? 'none'}
      </output>
      {state.error && <div role="alert">{state.error}</div>}
      <button
        type="button"
        onClick={() => void state.execute('original', 'retry')}
      >
        Retry
      </button>
      <button
        type="button"
        onClick={() => void state.execute('original', 'delete')}
      >
        Delete
      </button>
      <button
        type="button"
        onClick={() => void state.execute('original', 'download')}
      >
        Download
      </button>
    </>
  );
}
function Detail() {
  const state = useDownloadJob('original', 60_000);
  return (
    <>
      <output data-testid="detail-action">{state.action ?? 'idle'}</output>
      <output data-testid="detail-job">{state.job?.id ?? 'none'}</output>
      <output data-testid="removed">{String(state.removed)}</output>
      <button type="button" onClick={() => void state.retry()}>
        Detail retry
      </button>
    </>
  );
}
function Routes() {
  const [page, setPage] = useState('history');
  return (
    <>
      <button type="button" onClick={() => setPage('history')}>
        History
      </button>
      <button type="button" onClick={() => setPage('detail')}>
        Detail
      </button>
      <button type="button" onClick={() => setPage('away')}>
        Away
      </button>
      {page === 'history' && <Actions />}
      {page === 'detail' && <Detail />}
    </>
  );
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
const retried = { ...job('queued'), id: 'new-job' };

describe('shared download operations', () => {
  beforeEach(() => {
    runtime.retry.mockReset();
    runtime.remove.mockReset();
    runtime.issue.mockReset();
    runtime.download.mockReset();
    runtime.get
      .mockReset()
      .mockResolvedValue({ ...job('failed'), id: 'original' });
  });
  afterEach(() => onlineManager.setOnline(true));

  it('shares a pending history retry with detail and writes the new task after unmount', async () => {
    const pending = deferred<API.DownloadResponse>();
    runtime.retry.mockReturnValue(pending.promise);
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    fireEvent.click(screen.getByText('Retry'));
    await waitFor(() => expect(runtime.retry).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByText('Detail'));
    expect(screen.getByTestId('detail-action')).toHaveTextContent('retry');
    await waitFor(() =>
      expect(screen.getByTestId('detail-job')).toHaveTextContent('original'),
    );
    fireEvent.click(screen.getByText('Detail retry'));
    expect(runtime.retry).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByText('Away'));
    await act(async () => pending.resolve(retried));
    fireEvent.click(screen.getByText('History'));
    expect(screen.getByTestId('target')).toHaveTextContent('new-job');
    expect(screen.getByTestId('cached')).toHaveTextContent('new-job');
  });

  it('reuses the failed retry key when retrying from another page', async () => {
    const pending = deferred<API.DownloadResponse>();
    runtime.retry
      .mockReturnValueOnce(pending.promise)
      .mockResolvedValueOnce(retried);
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    fireEvent.click(screen.getByText('Retry'));
    await waitFor(() => expect(runtime.retry).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByText('Away'));
    await act(async () => pending.reject(new Error('response lost')));
    fireEvent.click(screen.getByText('History'));
    await screen.findByRole('alert');
    fireEvent.click(screen.getByText('Detail'));
    fireEvent.click(screen.getByText('Detail retry'));
    await waitFor(() => expect(runtime.retry).toHaveBeenCalledTimes(2));
    expect(runtime.retry.mock.calls[1][1]).toEqual(
      runtime.retry.mock.calls[0][1],
    );
  });

  it('retains a deletion completed while away and never reloads the deleted record', async () => {
    const pending = deferred<void>();
    runtime.remove.mockReturnValue(pending.promise);
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    fireEvent.click(screen.getByText('Delete'));
    await waitFor(() => expect(runtime.remove).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByText('Away'));
    await act(async () => pending.resolve());
    fireEvent.click(screen.getByText('Detail'));
    expect(screen.getByTestId('removed')).toHaveTextContent('true');
    expect(screen.getByTestId('detail-job')).toHaveTextContent('none');
    expect(runtime.get).not.toHaveBeenCalled();
  });

  it('does not replay an offline retry when connectivity returns', async () => {
    runtime.retry.mockRejectedValue(new Error('offline'));
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    onlineManager.setOnline(false);
    fireEvent.click(screen.getByText('Retry'));
    await screen.findByRole('alert');
    await act(async () => onlineManager.setOnline(true));
    expect(runtime.retry).toHaveBeenCalledOnce();
  });

  it('does not trigger a previous identity file download after identity change', async () => {
    const pending = deferred<API.DownloadUrlResponse>();
    runtime.issue.mockReturnValue(pending.promise);
    render(
      <QueryProvider>
        <Routes />
      </QueryProvider>,
    );
    fireEvent.click(screen.getByText('Download'));
    await waitFor(() => expect(runtime.issue).toHaveBeenCalledOnce());
    act(() => advanceSessionGeneration());
    await act(async () =>
      pending.resolve({
        url: 'https://objects.example/old-identity',
        filename: 'file.mp4',
        expires_at: '2026-09-23T01:00:00Z',
      }),
    );
    expect(runtime.download).not.toHaveBeenCalled();
    expect(screen.getByTestId('action')).toHaveTextContent('idle');
  });
});
