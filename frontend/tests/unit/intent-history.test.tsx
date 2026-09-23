import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { IntentHistoryPage } from '@/components/intake/intent-history-page';
import { job } from '../fixtures/download-fixtures';
import { intentFixture } from '../fixtures/intent-fixtures';
import { httpRequests, mockHttpResponses } from '../helpers/http';
import { render } from '../helpers/query-render';

const push = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }));
beforeEach(() => push.mockReset());

it('keeps pagination read-only and sends a ready result to its dedicated page', async () => {
  const item = {
    ...intentFixture(),
    created_at: '2026-09-23T00:00:00Z',
    title: '之前解析的视频',
  };
  mockHttpResponses({ items: [item], next_cursor: item.id });
  render(<IntentHistoryPage />);
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
  expect(push).toHaveBeenCalledWith(
    '/downloads/new?inspectionId=11111111-1111-4111-8111-111111111111&intentId=66666666-6666-4666-8666-666666666666',
  );
  expect(httpRequests().every((request) => request.method === 'GET')).toBe(
    true,
  );
});

it('opens failed history in a read-only dialog without restoring it as the current home task', async () => {
  const failed = intentFixture({
    status: 'failed',
    reason_code: 'provider_auth_required',
    inspection_id: null,
  });
  mockHttpResponses(
    {
      items: [{ ...failed, title: null, created_at: '2026-09-23T00:00:00Z' }],
      next_cursor: null,
    },
    failed,
  );
  render(<IntentHistoryPage />);
  const detailButton = await screen.findByRole('button', { name: '查看详情' });
  fireEvent.click(detailButton);
  expect(await screen.findByRole('dialog')).toBeVisible();
  expect(screen.getByText('本次解析未完成')).toBeVisible();
  expect(await screen.findByText(/该链接明确需要平台账号权限/)).toBeVisible();
  expect(httpRequests().map((request) => request.url)).toEqual([
    '/api/download-intents/history',
    `/api/download-intents/${failed.id}`,
  ]);
  expect(push).not.toHaveBeenCalled();
  expect(sessionStorage.getItem('framefetch-active-intent')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '关闭' }));
  await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  expect(detailButton).toHaveFocus();
});

it('shows handed-off download status and progress in a dialog before any navigation', async () => {
  const download = { ...job('running'), progress: 42 };
  const handedOff = intentFixture({
    status: 'handed_off',
    job_id: download.id,
    inspection_id: null,
  });
  mockHttpResponses(
    {
      items: [
        {
          ...handedOff,
          title: '已进入下载的视频',
          created_at: '2026-09-23T00:00:00Z',
        },
      ],
      next_cursor: null,
    },
    handedOff,
    download,
  );
  render(<IntentHistoryPage />);
  fireEvent.click(await screen.findByRole('button', { name: '查看下载' }));
  expect(await screen.findByText('正在下载')).toBeVisible();
  expect(
    screen.getByRole('progressbar', { name: '下载进度 42%' }),
  ).toBeVisible();
  expect(
    screen.getByRole('link', { name: '打开完整下载任务' }),
  ).toHaveAttribute('href', `/downloads/detail?jobId=${download.id}`);
  expect(httpRequests().map((request) => request.url)).toEqual([
    '/api/download-intents/history',
    `/api/download-intents/${handedOff.id}`,
    `/api/downloads/${download.id}`,
  ]);
  expect(push).not.toHaveBeenCalled();
});
