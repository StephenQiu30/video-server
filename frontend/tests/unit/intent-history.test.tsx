import { fireEvent, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { IntentHistory } from '@/components/intake/intent-history';
import { intentFixture } from '../fixtures/intent-fixtures';
import { httpRequests, mockHttpResponses } from '../helpers/http';
import { render } from '../helpers/query-render';

it('loads history only on request, follows the server cursor and resumes without submitting work', async () => {
  const onResume = vi.fn();
  const item = {
    ...intentFixture(),
    created_at: '2026-09-23T00:00:00Z',
    title: '之前解析的视频',
  };
  render(<IntentHistory disabled={false} onResume={onResume} />);
  expect(httpRequests()).toHaveLength(0);
  mockHttpResponses({ items: [item], next_cursor: item.id });
  fireEvent.click(screen.getByRole('button', { name: '解析记录' }));
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
  fireEvent.click(screen.getByRole('button', { name: '查看解析' }));
  expect(onResume).toHaveBeenCalledWith('66666666-6666-4666-8666-666666666666');
  expect(screen.getByRole('button', { name: '解析记录' })).toHaveFocus();
  expect(
    screen.queryByRole('button', { name: '查看解析' }),
  ).not.toBeInTheDocument();
  expect(httpRequests().every((item) => item.method === 'GET')).toBe(true);
});

it('keeps empty history distinct from an active request and blocks selection while a write is pending', async () => {
  mockHttpResponses({
    items: [
      { ...intentFixture(), created_at: '2026-09-23T00:00:00Z', title: null },
    ],
    next_cursor: null,
  });
  render(<IntentHistory disabled onResume={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: '解析记录' }));
  await waitFor(() =>
    expect(screen.getByRole('button', { name: '查看解析' })).toBeDisabled(),
  );
});
