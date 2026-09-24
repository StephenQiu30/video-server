import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import DownloadWorkspace from '@/components/intake/download-workspace';
import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { inspection } from '../fixtures/download-fixtures';
import { intentFixture } from '../fixtures/intent-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';
import { render } from '../helpers/query-render';

const push = vi.fn();
vi.mock('@/components/auth/auth-provider', async (importOriginal) => ({
  ...(await importOriginal()),
  useAuth: () => ({ user: { id: 'intent-test-owner', role: 'user' } }),
}));
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }));
vi.mock('@/components/providers/use-provider-statuses', () => ({
  useProviderStatuses: () => ({ data: null, error: null }),
}));
function renderEntry() {
  return render(
    <TooltipProvider>
      <DownloadWorkspace />
      <Toaster position="bottom-right" />
    </TooltipProvider>,
  );
}
function enter(url: string) {
  fireEvent.change(screen.getByLabelText('公开视频地址'), {
    target: { value: url },
  });
  fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
}
beforeEach(() => {
  push.mockReset();
  window.history.replaceState({}, '', '/');
});

it('recovers an uncertain submission using the same idempotency key and opens the result route', async () => {
  mockHttpError(new Error('response lost'));
  mockHttpResponses(intentFixture(), inspection);
  renderEntry();
  enter('https://youtu.be/owned');
  await waitFor(() =>
    expect(push).toHaveBeenCalledWith(
      `/downloads/new?inspectionId=${inspection.id}&intentId=${intentFixture().id}`,
    ),
  );
  const requests = httpRequests();
  expect(requests.filter((request) => request.method === 'POST')).toHaveLength(
    1,
  );
  expect(requests[1]).toMatchObject({
    method: 'GET',
    url: '/api/download-intents',
    params: { idempotency_key: requests[0].headers?.['Idempotency-Key'] },
  });
});

it('dismisses the loading notice once the parsed result has opened', async () => {
  mockHttpResponses(intentFixture(), inspection);
  renderEntry();
  enter('https://youtu.be/owned');
  await waitFor(() => expect(push).toHaveBeenCalledTimes(1));
  expect(sessionStorage.getItem('framefetch-active-intent')).toBeNull();
  await waitFor(() =>
    expect(screen.queryByText('正在加载解析结果')).not.toBeInTheDocument(),
  );
});

it('retires a restored ready task after handing off its result', async () => {
  const ready = intentFixture();
  sessionStorage.setItem(
    'framefetch-active-intent',
    JSON.stringify({ owner: 'intent-test-owner', id: ready.id }),
  );
  mockHttpResponses(ready, inspection);
  const first = renderEntry();
  await waitFor(() => expect(push).toHaveBeenCalledTimes(1));
  expect(sessionStorage.getItem('framefetch-active-intent')).toBeNull();
  const requests = httpRequests().length;
  first.unmount();
  renderEntry();
  expect(screen.getByLabelText('公开视频地址')).toBeVisible();
  expect(httpRequests()).toHaveLength(requests);
  expect(push).toHaveBeenCalledTimes(1);
});

it('keeps an expired inspection on home with a refresh action', async () => {
  mockHttpResponses(intentFixture(), {
    ...inspection,
    expires_at: new Date(Date.now() - 1000).toISOString(),
  });
  renderEntry();
  enter('https://youtu.be/owned');
  expect(await screen.findByRole('button', { name: '更新结果' })).toBeEnabled();
  expect(push).not.toHaveBeenCalled();
  expect(document.querySelector('[data-slot="media-result"]')).toBeNull();
});

it('does not restore a completed download into the homepage', async () => {
  const completed = intentFixture({
    status: 'handed_off',
    inspection_id: null,
    job_id: '33333333-3333-4333-8333-333333333333',
  });
  sessionStorage.setItem(
    'framefetch-active-intent',
    JSON.stringify({ owner: 'intent-test-owner', id: completed.id }),
  );
  mockHttpResponses(completed);
  try {
    renderEntry();
    await waitFor(() => expect(httpRequests()).toHaveLength(1));
    expect(push).not.toHaveBeenCalled();
    expect(document.querySelector('[data-slot="media-result"]')).toBeNull();
  } finally {
    sessionStorage.removeItem('framefetch-active-intent');
  }
});
