import { act } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { useBulkParseDownload } from '@/components/intake/use-bulk-parse-download';
import { inspection, job } from '../fixtures/download-fixtures';
import { intentFixture } from '../fixtures/intent-fixtures';
import { httpRequests, mockHttpResponses } from '../helpers/http';
import { renderHook } from '../helpers/query-render';

it('checks access before creating jobs and keeps an idempotency key for repeated requests', async () => {
  const item = {
    ...intentFixture(),
    title: '视频',
    record_type: 'parse',
  } as API.ParseHistoryRecordResponse;
  const { result } = renderHook(() => useBulkParseDownload());
  mockHttpResponses(inspection, job('queued'), {
    ...inspection,
    access_decision: 'blocked',
  });
  let done: string[] = [];
  await act(async () => {
    done = await result.current.execute([item, { ...item, id: 'blocked' }]);
  });
  expect(done).toEqual([item.id]);
  expect(result.current.message).toContain('已创建 1 项下载任务，失败 1 项');
  const first = httpRequests().find((request) => request.method === 'POST');
  expect(first?.data).toEqual({
    inspection_id: inspection.id,
    format_id: inspection.formats[0].id,
  });
  mockHttpResponses(inspection, job('queued'));
  await act(async () => {
    await result.current.execute([item]);
  });
  const posts = httpRequests().filter((request) => request.method === 'POST');
  expect(posts).toHaveLength(2);
  expect(posts[1].headers?.['Idempotency-Key']).toBe(
    first?.headers?.['Idempotency-Key'],
  );
});

it('stops creating jobs after unmount', async () => {
  const api = await import('@/api/inspections');
  let resolve!: (value: API.InspectionResponse) => void;
  vi.spyOn(api, 'getInspection').mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const { result, unmount } = renderHook(() => useBulkParseDownload());
  let pending!: Promise<string[]>;
  act(() => {
    pending = result.current.execute([
      { ...intentFixture() } as API.ParseHistoryRecordResponse,
    ]);
  });
  unmount();
  resolve(inspection);
  await pending;
  expect(
    httpRequests().filter((request) => request.method === 'POST'),
  ).toHaveLength(0);
});
