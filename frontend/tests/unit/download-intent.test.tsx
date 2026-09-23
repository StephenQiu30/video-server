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
vi.mock('@/components/auth/auth-provider', async (importOriginal) => ({
  ...(await importOriginal()),
  useAuth: () => ({ user: identity }),
}));
const reference = 'framefetch-active-intent';
const requestKey = '55555555-5555-4555-8555-555555555555';
const input = '分享 https://media.example/video?signature=private-input 文案';

function saveAcceptedId(id = intentFixture().id) {
  sessionStorage.setItem(reference, JSON.stringify({ owner: identity.id, id }));
}

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

it('restores a previously accepted ID without a new POST after remount', async () => {
  const saved = intentFixture();
  saveAcceptedId(saved.id);
  mockHttpResponses(saved, inspection);
  const first = renderHook(useDownloadIntent);
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
  saveAcceptedId();
  mockHttpError(new ApiError(404, 'not_found', 'not found', '不存在。'));
  const { result } = renderHook(useDownloadIntent);
  await waitFor(() =>
    expect(result.current.error).toContain('这条解析记录已不可用'),
  );
  expect(result.current.pending).toBe(false);
  expect(result.current.canResubmit).toBe(false);
  mockHttpError(new ApiError(404, 'not_found', 'not found', '不存在。'));
  await act(async () => result.current.retry());
  expect(httpRequests().every((item) => item.method === 'GET')).toBe(true);
});

it('restores a handed-off accepted ID without reading its expired inspection', async () => {
  saveAcceptedId();
  mockHttpResponses(
    intentFixture({
      status: 'handed_off',
      job_id: '77777777-7777-4777-8777-777777777777',
    }),
  );
  const { result } = renderHook(useDownloadIntent);
  await waitFor(() =>
    expect(result.current.snapshot?.status).toBe('handed_off'),
  );
  expect(result.current.error).toBeNull();
  expect(result.current.inspection).toBeUndefined();
  expect(httpRequests()).toHaveLength(1);
});

it('refreshes an expired result explicitly once and keeps the same intent until new options are ready', async () => {
  const expired = {
    ...inspection,
    expires_at: new Date(Date.now() - 1000).toISOString(),
    formats: [],
  };
  saveAcceptedId();
  mockHttpResponses(intentFixture(), expired);
  const { result } = renderHook(useDownloadIntent);
  await waitFor(() => expect(result.current.resultExpired).toBe(true));
  expect(httpRequests().every((item) => item.method === 'GET')).toBe(true);
  let finish!: (value: unknown) => void;
  vi.mocked(httpClient.request).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }) as never,
  );
  let updating!: Promise<void>;
  act(() => {
    updating = result.current.refresh();
    void result.current.refresh();
  });
  await waitFor(() => expect(result.current.pending).toBe(true));
  expect(result.current.inspection).toBeUndefined();
  expect(httpRequests().filter((item) => item.method === 'POST')).toHaveLength(
    1,
  );
  await act(async () => {
    finish({ data: intentFixture({ version: 3, status: 'queued' }) });
    await updating;
  });
  const newId = '88888888-8888-4888-8888-888888888888';
  mockHttpResponses(intentFixture({ version: 4, inspection_id: newId }), {
    ...inspection,
    id: newId,
  });
  await act(async () => result.current.retry());
  await waitFor(() => expect(result.current.inspection?.id).toBe(newId));
  expect(result.current.resultExpired).toBe(false);
  expect(result.current.snapshot?.id).toBe(intentFixture().id);
  const posts = httpRequests().filter((item) => item.method === 'POST');
  expect(posts).toHaveLength(1);
  expect(posts[0].url).toBe(
    `/api/download-intents/${intentFixture().id}/refresh`,
  );
});

it('resolves an uncertain refresh by a read without automatically replaying it', async () => {
  saveAcceptedId();
  mockHttpResponses(intentFixture(), {
    ...inspection,
    expires_at: new Date(Date.now() - 1000).toISOString(),
    formats: [],
  });
  const { result } = renderHook(useDownloadIntent);
  await waitFor(() => expect(result.current.resultExpired).toBe(true));
  mockHttpError(new ApiError(0, 'request_failed', 'offline', '连接失败。'));
  mockHttpResponses(intentFixture({ version: 3, status: 'queued' }));
  await act(async () => result.current.refresh());
  await waitFor(() => expect(result.current.snapshot?.status).toBe('queued'));
  expect(httpRequests().filter((item) => item.method === 'POST')).toHaveLength(
    1,
  );
});
