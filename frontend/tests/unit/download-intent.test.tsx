import { act, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { useDownloadIntent } from '@/components/intake/use-download-intent';
import { httpClient } from '@/lib/request';
import { ApiError } from '@/lib/request-error';
import { advanceSessionGeneration } from '@/lib/session-events';
import { inspection } from '../fixtures/download-fixtures';
import { intentFixture } from '../fixtures/intent-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';
import { renderHook } from '../helpers/query-render';

const identity = vi.hoisted(() => ({ id: 'owner-a' }));
vi.mock('@/components/auth/auth-provider', () => ({
  useAuth: () => ({ user: identity }),
}));
const reference = 'framefetch-active-intent';
const requestKey = '55555555-5555-4555-8555-555555555555';
const input = '分享 https://media.example/video?signature=private-input 文案';

beforeEach(() => {
  identity.id = 'owner-a';
});

it('persists only an owner-bound random reference before accepting work and prevents double submit', async () => {
  let resolve!: (value: unknown) => void;
  vi.mocked(httpClient.request).mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done;
      }) as never,
  );
  const { result } = renderHook(useDownloadIntent);
  let submitted!: Promise<void>;
  act(() => {
    submitted = result.current.submit(input);
    void result.current.submit(input);
  });
  await waitFor(() => expect(httpRequests()).toHaveLength(1));
  const saved = JSON.parse(sessionStorage.getItem(reference) ?? '{}');
  expect(saved).toEqual({ owner: 'owner-a', key: expect.any(String) });
  expect(sessionStorage.getItem(reference)).not.toContain('private-input');
  expect(httpRequests()[0]).toMatchObject({
    data: { input },
    headers: { 'Idempotency-Key': saved.key },
  });
  await act(async () => {
    resolve({ data: intentFixture({ status: 'queued', inspection_id: null }) });
    await submitted;
  });
  expect(result.current.pending).toBe(true);
});

it('restores an accepted result after a full application remount without storing raw input', async () => {
  sessionStorage.setItem(
    reference,
    JSON.stringify({ owner: identity.id, key: requestKey }),
  );
  mockHttpResponses(intentFixture(), inspection);
  const first = renderHook(useDownloadIntent);
  await waitFor(() =>
    expect(first.result.current.inspection?.id).toBe(inspection.id),
  );
  first.unmount();
  mockHttpResponses(intentFixture(), inspection);
  const second = renderHook(useDownloadIntent);
  await waitFor(() =>
    expect(second.result.current.inspection?.id).toBe(inspection.id),
  );
  expect(second.result.current.attempt?.input).toBeNull();
  expect(httpRequests().every((request) => request.method === 'GET')).toBe(
    true,
  );
  expect(httpRequests()[2].params).toEqual({ idempotency_key: requestKey });
});

it('recovers a lost POST response by read-only lookup, never a fresh POST', async () => {
  mockHttpError(new ApiError(0, 'request_failed', 'offline', '连接失败。'));
  mockHttpResponses(intentFixture(), inspection);
  const { result } = renderHook(useDownloadIntent);
  await act(async () => result.current.submit(input));
  await waitFor(() =>
    expect(result.current.inspection?.id).toBe(inspection.id),
  );
  const requests = httpRequests();
  expect(requests.filter((request) => request.method === 'POST')).toHaveLength(
    1,
  );
  expect(requests[1].params).toEqual({
    idempotency_key: requests[0].headers?.['Idempotency-Key'],
  });
});

it('reuses the original key only after explicit retry when the server did not accept the first request', async () => {
  mockHttpError(new ApiError(0, 'request_failed', 'offline', '连接失败。'));
  mockHttpError(new ApiError(404, 'not_found', 'not found', '未接单。'));
  const { result } = renderHook(useDownloadIntent);
  await act(async () => result.current.submit(input));
  await waitFor(() => expect(result.current.canResubmit).toBe(true));
  expect(httpRequests()).toHaveLength(2);
  mockHttpResponses(intentFixture(), inspection);
  await act(async () => result.current.retry());
  await waitFor(() => expect(result.current.inspection).toBeDefined());
  const posts = httpRequests().filter((request) => request.method === 'POST');
  expect(posts).toHaveLength(2);
  expect(posts[1].headers?.['Idempotency-Key']).toBe(
    posts[0].headers?.['Idempotency-Key'],
  );
});

it('retains ready results on query failure and recovers without repeating parsing', async () => {
  mockHttpResponses(intentFixture(), inspection);
  const { result } = renderHook(useDownloadIntent);
  await act(async () => result.current.submit(input));
  await waitFor(() => expect(result.current.inspection).toBeDefined());
  mockHttpError(
    new ApiError(503, 'service_unavailable', 'offline', '服务暂时不可用。'),
  );
  mockHttpResponses(inspection);
  await act(async () => result.current.retry());
  expect(result.current.inspection?.id).toBe(inspection.id);
  expect(result.current.error).toBeTruthy();
  mockHttpResponses(intentFixture(), inspection);
  await act(async () => result.current.retry());
  expect(result.current.error).toBeNull();
  expect(
    httpRequests().filter((request) => request.method === 'POST'),
  ).toHaveLength(1);
});

it('does not let an older ready version replace confirmed cancellation', async () => {
  mockHttpResponses(
    intentFixture({ status: 'queued', version: 1, inspection_id: null }),
  );
  const { result } = renderHook(useDownloadIntent);
  await act(async () => result.current.submit(input));
  await waitFor(() => expect(result.current.snapshot?.status).toBe('queued'));
  mockHttpResponses(
    intentFixture({ status: 'cancelled', version: 3, inspection_id: null }),
  );
  await act(async () => result.current.cancel());
  mockHttpResponses(intentFixture({ status: 'ready', version: 2 }));
  await act(async () => result.current.retry());
  expect(result.current.snapshot?.status).toBe('cancelled');
  expect(result.current.inspection).toBeUndefined();
  expect(result.current.pending).toBe(false);
});

it('rejects a previous owner reference without querying it and clears state at an identity change', async () => {
  sessionStorage.setItem(
    reference,
    JSON.stringify({ owner: 'other-owner', key: requestKey }),
  );
  const { result } = renderHook(useDownloadIntent);
  expect(result.current.attempt).toBeNull();
  expect(httpRequests()).toHaveLength(0);
  expect(sessionStorage.getItem(reference)).toBeNull();
  mockHttpResponses(intentFixture({ status: 'queued', inspection_id: null }));
  await act(async () => result.current.submit(input));
  act(() => {
    identity.id = 'owner-b';
    advanceSessionGeneration();
  });
  expect(result.current.attempt).toBeNull();
  expect(result.current.snapshot).toBeUndefined();
  expect(sessionStorage.getItem(reference)).toBeNull();
});

it('does not start remote work when a refresh-safe reference cannot be saved', async () => {
  const { result } = renderHook(useDownloadIntent);
  const denied = vi.spyOn(sessionStorage, 'setItem').mockImplementation(() => {
    throw new DOMException('Denied');
  });
  await expect(result.current.submit(input)).rejects.toMatchObject({
    code: 'intent_reference_unavailable',
  });
  expect(httpRequests()).toHaveLength(0);
  denied.mockRestore();
});

it('recovers a history record by ID without browser references or a new POST and restores it after remount', async () => {
  const saved = intentFixture();
  const first = renderHook(useDownloadIntent);
  mockHttpResponses(saved, inspection);
  act(() => expect(first.result.current.resume(saved.id)).toBe(true));
  await waitFor(() =>
    expect(first.result.current.inspection?.id).toBe(inspection.id),
  );
  expect(sessionStorage.getItem(reference)).toBe(
    JSON.stringify({ owner: identity.id, id: saved.id }),
  );
  first.unmount();
  mockHttpResponses(saved, inspection);
  const second = renderHook(useDownloadIntent);
  await waitFor(() =>
    expect(second.result.current.inspection?.id).toBe(inspection.id),
  );
  expect(httpRequests().every((item) => item.method === 'GET')).toBe(true);
  expect(
    httpRequests()
      .filter((item) => item.url?.startsWith('/api/download-intents'))
      .every((item) => item.url === `/api/download-intents/${saved.id}`),
  ).toBe(true);
});

it('does not treat an unavailable history ID as an unaccepted request to replay', async () => {
  mockHttpError(new ApiError(404, 'not_found', 'not found', '不存在。'));
  const { result } = renderHook(useDownloadIntent);
  act(() => result.current.resume(intentFixture().id));
  await waitFor(() =>
    expect(result.current.error).toContain('这条解析记录已不可用'),
  );
  expect(result.current.pending).toBe(false);
  expect(result.current.canResubmit).toBe(false);
  mockHttpError(new ApiError(404, 'not_found', 'not found', '不存在。'));
  await act(async () => result.current.retry());
  expect(httpRequests().every((item) => item.method === 'GET')).toBe(true);
});

it('allows read-only history recovery when session storage is unavailable', async () => {
  const storage = vi
    .spyOn(Storage.prototype, 'setItem')
    .mockImplementation(() => {
      throw new Error('denied');
    });
  mockHttpResponses(intentFixture(), inspection);
  const { result } = renderHook(useDownloadIntent);
  act(() => expect(result.current.resume(intentFixture().id)).toBe(true));
  await waitFor(() =>
    expect(result.current.inspection?.id).toBe(inspection.id),
  );
  expect(httpRequests().every((item) => item.method === 'GET')).toBe(true);
  storage.mockRestore();
});

it('opens a handed-off history record without reading its expired inspection', async () => {
  mockHttpResponses(
    intentFixture({
      status: 'handed_off',
      job_id: '77777777-7777-4777-8777-777777777777',
    }),
  );
  const { result } = renderHook(useDownloadIntent);
  act(() => result.current.resume(intentFixture().id));
  await waitFor(() =>
    expect(result.current.snapshot?.status).toBe('handed_off'),
  );
  expect(result.current.error).toBeNull();
  expect(result.current.inspection).toBeUndefined();
  expect(httpRequests()).toHaveLength(1);
});

it('keeps confirmed cancellation when switching from an acceptance key to the same history ID', async () => {
  mockHttpResponses(
    intentFixture({ status: 'queued', version: 1, inspection_id: null }),
  );
  const { result } = renderHook(useDownloadIntent);
  await act(async () => result.current.submit(input));
  mockHttpResponses(
    intentFixture({ status: 'cancelled', version: 3, inspection_id: null }),
  );
  await act(async () => result.current.cancel());
  mockHttpResponses(intentFixture({ status: 'ready', version: 2 }));
  act(() => result.current.resume(intentFixture().id));
  await act(async () => result.current.retry());
  await waitFor(() => expect(httpRequests()).toHaveLength(3));
  expect(result.current.snapshot?.status).toBe('cancelled');
  expect(result.current.inspection).toBeUndefined();
});
