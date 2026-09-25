import { fireEvent, screen, waitFor } from '@testing-library/react';
import { expect, it } from 'vitest';
import { OperationLogsView } from '@/components/admin/operation-logs-view';
import { httpRequests, mockHttpResponses } from '../helpers/http';
import { render } from '../helpers/query-render';

const item: API.OperationLogResponse = {
  id: 'log-id',
  created_at: '2026-09-25T00:00:00Z',
  finished_at: '2026-09-25T00:00:01Z',
  actor_id: 'admin-id',
  actor_name: '管理员',
  operation: 'deleteUser',
  description: '删除用户',
  method: 'DELETE',
  route: '/api/admin/users/{user_id}',
  resource_id: 'resource-id',
  resource_key: null,
  outcome: 'succeeded',
  source: 'request',
  task_state: null,
  status_code: 204,
  error_code: null,
};
it('loads ten read-only records, opens details and filters administrator actions', async () => {
  mockHttpResponses({ items: [item], total: 1, page: 1, page_size: 10 });
  render(<OperationLogsView />);
  expect(await screen.findByText('删除用户')).toBeVisible();
  expect(httpRequests()[0]).toMatchObject({
    url: '/api/admin/operation-logs',
    params: { page: 1, page_size: 10 },
  });
  expect(
    screen.queryByRole('button', { name: /批量|重试任务|删除记录/ }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '查看删除用户详情' }));
  expect(await screen.findByRole('dialog')).toHaveTextContent('resource-id');
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  await waitFor(() =>
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
  );
  mockHttpResponses({ items: [], total: 0, page: 1, page_size: 10 });
  fireEvent.click(screen.getByRole('combobox', { name: '操作范围' }));
  fireEvent.click(await screen.findByRole('option', { name: '管理员操作' }));
  await waitFor(() =>
    expect(httpRequests().at(-1)?.params).toMatchObject({
      admin_only: true,
      page: 1,
    }),
  );
});
it('shows empty state without a permanent spinner', async () => {
  mockHttpResponses({ items: [], total: 0, page: 1, page_size: 10 });
  render(<OperationLogsView />);
  expect(
    await screen.findByRole('heading', { name: '暂无操作日志' }),
  ).toBeVisible();
  expect(screen.queryByLabelText('正在读取操作日志')).not.toBeInTheDocument();
});
it('includes the whole selected end minute', async () => {
  mockHttpResponses({ items: [], total: 0, page: 1, page_size: 10 });
  render(<OperationLogsView />);
  await screen.findByRole('heading', { name: '暂无操作日志' });
  fireEvent.change(screen.getByLabelText('结束时间'), {
    target: { value: '2026-09-25T10:30' },
  });
  await waitFor(() =>
    expect(httpRequests().at(-1)?.params).toMatchObject({
      created_to: new Date(
        new Date('2026-09-25T10:30').getTime() + 59_999,
      ).toISOString(),
    }),
  );
});
