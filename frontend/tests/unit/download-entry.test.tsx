import { fireEvent, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DownloadWorkspace from '@/components/intake/download-workspace';
import { TooltipProvider } from '@/components/ui/tooltip';
import { inspection } from '../fixtures/download-fixtures';
import { intentFixture } from '../fixtures/intent-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';
import { render } from '../helpers/query-render';

vi.mock('@/components/auth/auth-provider', () => ({
  useAuth: () => ({ user: { id: 'intent-test-owner', role: 'user' } }),
}));

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));
const statuses = vi.hoisted(() => vi.fn(() => ({ data: null, error: null })));
vi.mock('@/components/providers/use-provider-statuses', () => ({
  useProviderStatuses: statuses,
}));

function enter(url: string) {
  fireEvent.change(screen.getByLabelText('公开视频地址'), {
    target: { value: url },
  });
  fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
}

describe('simple download entry', () => {
  beforeEach(() => window.history.replaceState({}, '', '/'));

  it('submits only the input and does not fetch provider configuration', async () => {
    mockHttpResponses(intentFixture(), {
      ...inspection,
      access_policy_id: 'operator_public',
    });
    render(
      <TooltipProvider>
        <DownloadWorkspace />
      </TooltipProvider>,
    );
    expect(statuses).not.toHaveBeenCalled();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    const url = '分享 https://www.youtube.com/watch?v=owned 文案';
    enter(url);
    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(screen.queryByText('部署者公开会话')).not.toBeInTheDocument();
    expect(httpRequests()).toHaveLength(2);
    expect(httpRequests()[0].data).toEqual({
      input: url,
    });
  });

  it('clears previous results and changes the key only when input changes', async () => {
    mockHttpResponses(intentFixture(), inspection, intentFixture());
    render(
      <TooltipProvider>
        <DownloadWorkspace />
      </TooltipProvider>,
    );
    enter('https://youtu.be/first');
    await screen.findByText(inspection.title);
    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://youtu.be/second' },
    });
    expect(
      document.querySelector('[data-slot="inspection-result"]'),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
    await screen.findByText(inspection.title);
    const requests = httpRequests().filter(
      (request) => request.method === 'POST',
    );
    expect(requests[0].headers?.['Idempotency-Key']).not.toBe(
      requests[1].headers?.['Idempotency-Key'],
    );
  });

  it('finds the original intent after an uncertain submission without replaying POST', async () => {
    mockHttpError(new Error('response lost'));
    mockHttpResponses(intentFixture(), inspection);
    render(
      <TooltipProvider>
        <DownloadWorkspace />
      </TooltipProvider>,
    );
    const url = 'https://youtu.be/owned';
    enter(url);
    await screen.findByText(inspection.title);
    expect(screen.getByLabelText('公开视频地址')).toHaveValue(url);
    const requests = httpRequests();
    expect(
      requests.filter((request) => request.method === 'POST'),
    ).toHaveLength(1);
    expect(requests[1]).toMatchObject({
      method: 'GET',
      url: '/api/download-intents',
      params: { idempotency_key: requests[0].headers?.['Idempotency-Key'] },
    });
  });
});

it('shows an explicit update action for expired results without displaying stale format controls', async () => {
  mockHttpResponses(intentFixture(), {
    ...inspection,
    expires_at: new Date(Date.now() - 1000).toISOString(),
    formats: [],
  });
  render(
    <TooltipProvider>
      <DownloadWorkspace />
    </TooltipProvider>,
  );
  enter('https://youtu.be/owned');
  expect(
    await screen.findByRole('button', { name: '更新解析结果' }),
  ).toBeEnabled();
  expect(
    screen.queryByRole('button', { name: '创建下载任务' }),
  ).not.toBeInTheDocument();
  expect(httpRequests().filter((item) => item.method === 'POST')).toHaveLength(
    1,
  );
  mockHttpResponses(intentFixture({ status: 'queued', version: 3 }));
  fireEvent.click(screen.getByRole('button', { name: '更新解析结果' }));
  expect(await screen.findByText('等待解析')).toBeVisible();
  expect(
    httpRequests()
      .filter((item) => item.method === 'POST')
      .map((item) => item.url),
  ).toEqual([
    '/api/download-intents',
    `/api/download-intents/${intentFixture().id}/refresh`,
  ]);
});

it('updates the original intent when confirmation races expiry and does not automatically confirm again', async () => {
  mockHttpResponses(intentFixture(), inspection);
  render(
    <TooltipProvider>
      <DownloadWorkspace />
    </TooltipProvider>,
  );
  enter('https://youtu.be/owned');
  await screen.findByRole('button', { name: '创建下载任务' });
  const { ApiError } = await import('@/lib/request-error');
  mockHttpError(new ApiError(410, 'resource_expired', 'expired', '已过期。'));
  mockHttpResponses(intentFixture({ status: 'queued', version: 3 }));
  fireEvent.click(screen.getByRole('button', { name: '创建下载任务' }));
  expect(await screen.findByText('等待解析')).toBeVisible();
  expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument();
  expect(
    httpRequests().filter((item) => item.url === '/api/downloads'),
  ).toHaveLength(1);
  expect(
    httpRequests().filter((item) => item.url?.endsWith('/refresh')),
  ).toHaveLength(1);
});
