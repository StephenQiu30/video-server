import { fireEvent, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { IntentHistory } from '@/components/intake/intent-history';
import { intentFixture } from '../fixtures/intent-fixtures';
import { httpRequests, mockHttpResponses } from '../helpers/http';
import { render } from '../helpers/query-render';

it('loads the dedicated history page, follows the server cursor and resumes without submitting work', async () => {
  const onResume = vi.fn();
  const item = {
    ...intentFixture(),
    created_at: '2026-09-23T00:00:00Z',
    title: '之前解析的视频',
  };
  mockHttpResponses({ items: [item], next_cursor: item.id });
  render(<IntentHistory disabled={false} onResume={onResume} />);
  expect(screen.getByRole('heading', { name: '解析记录' })).toBeVisible();
  expect(await screen.findByText(item.title)).toBeVisible();
  mockHttpResponses({
    items: [
      {
        ...item,
        id: '66666666-6666-4666-8666-666666666666',
        title: '较早的视频',
      },
    ],
    next_cursor: null,
  });
  fireEvent.click(screen.getByRole('button', { name: '更早的记录' }));
  expect(await screen.findByText('较早的视频')).toBeVisible();
  expect(httpRequests()[1].params).toMatchObject({
    before: item.id,
    limit: 20,
  });
  fireEvent.click(screen.getByRole('button', { name: '查看结果' }));
  expect(onResume).toHaveBeenCalledWith(
    expect.objectContaining({ id: '66666666-6666-4666-8666-666666666666' }),
  );
  expect(screen.getByRole('button', { name: '查看结果' })).toBeVisible();
  expect(httpRequests().every((item) => item.method === 'GET')).toBe(true);
});

it('blocks record selection while a write is pending', async () => {
  mockHttpResponses({
    items: [
      { ...intentFixture(), created_at: '2026-09-23T00:00:00Z', title: null },
    ],
    next_cursor: null,
  });
  render(<IntentHistory disabled onResume={vi.fn()} />);
  await waitFor(() =>
    expect(screen.getByRole('button', { name: '查看结果' })).toBeDisabled(),
  );
});

it('makes handoff, pending, and failed records distinguishable without opening them', async () => {
  const onResume = vi.fn();
  mockHttpResponses({
    items: [
      {
        ...intentFixture({ status: 'handed_off', job_id: 'job-1' }),
        created_at: '2026-09-23T00:00:00Z',
        title: '已进入下载的视频',
      },
      {
        ...intentFixture({ id: 'intent-2', status: 'resolving' }),
        created_at: '2026-09-23T00:00:00Z',
        title: null,
      },
      {
        ...intentFixture({ id: 'intent-3', status: 'failed' }),
        created_at: '2026-09-23T00:00:00Z',
        title: null,
      },
    ],
    next_cursor: null,
  });
  render(<IntentHistory disabled={false} onResume={onResume} />);
  expect(await screen.findByText('已进入下载的视频')).toBeVisible();
  expect(screen.getByText('下载任务已创建')).toBeVisible();
  expect(screen.getByText('正在读取媒体信息')).toBeVisible();
  expect(screen.getByText('本次解析未完成')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: '查看下载' }));
  expect(onResume).toHaveBeenCalledWith(
    expect.objectContaining({ status: 'handed_off', job_id: 'job-1' }),
  );
});
