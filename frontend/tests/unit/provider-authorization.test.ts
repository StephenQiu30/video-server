import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createElement } from 'react';
import { expect, it, vi } from 'vitest';
import * as providers from '@/api/providers';
import { ProviderAuthorizationDialog } from '@/components/providers/provider-authorization-dialog';
import { providerAuthorizationTarget } from '@/lib/provider-authorization';

const TRANSACTION_ID = '1'.repeat(32);

vi.mock('@/components/auth/auth-provider', () => ({
  useAuth: () => ({
    user: { role: 'admin' },
  }),
}));

it.each([
  'provider_guest_context_required',
  'provider_configuration_missing',
  'provider_verification_failed',
])('does not turn %s into an account authorization action', (errorCode) => {
  expect(
    providerAuthorizationTarget('https://www.douyin.com/video/123', errorCode),
  ).toBeNull();
});

it('does not render a no-op managed-session action without a recovery callback', () => {
  const { container } = render(
    createElement(ProviderAuthorizationDialog, {
      provider: {
        authorization_action: 'managed_session',
        display_name: '微信视频号',
        key: 'wechat_channels',
      },
    }),
  );

  expect(container).toBeEmptyDOMElement();
});

it('retries a deployment-managed provider without starting browser authorization', async () => {
  const onAuthorized = vi.fn().mockResolvedValue(undefined);
  render(
    createElement(ProviderAuthorizationDialog, {
      onAuthorized,
      provider: {
        authorization_action: 'managed_session',
        display_name: 'YouTube',
        key: 'youtube',
      },
    }),
  );

  fireEvent.click(screen.getByRole('button', { name: '使用托管线路重试' }));

  expect(onAuthorized).toHaveBeenCalledOnce();
  expect(
    screen.queryByRole('button', { name: '使用隔离浏览器会话' }),
  ).not.toBeInTheDocument();
});

it('starts an isolated browser authorization without a connector handshake', async () => {
  const begin = vi
    .spyOn(providers, 'beginProviderAuthorization')
    .mockResolvedValue({
      expires_at: '2026-09-22T12:10:00Z',
      provider_key: 'youtube',
      status: 'pending',
      transaction_id: TRANSACTION_ID,
    });
  render(
    createElement(ProviderAuthorizationDialog, {
      provider: {
        authorization_action: 'browser_session',
        display_name: 'YouTube',
        key: 'youtube',
      },
    }),
  );
  fireEvent.click(screen.getByRole('button', { name: '使用隔离浏览器会话' }));
  await waitFor(() =>
    expect(begin).toHaveBeenCalledWith(
      { provider_key: 'youtube' },
      { source: 'dedicated_chrome' },
    ),
  );
  expect(screen.getByText(/正在等待隔离 Chrome/)).toBeInTheDocument();
});

it.each([false, true])(
  'keeps a durable authorization on navigation (response pending: %s)',
  async (pendingResponse) => {
    let finish!: (value: API.ProviderAuthorizationResponse) => void;
    const transaction: API.ProviderAuthorizationResponse = {
      expires_at: '2026-09-22T12:10:00Z',
      provider_key: 'youtube',
      status: 'pending',
      transaction_id: TRANSACTION_ID,
    };
    const begin = vi
      .spyOn(providers, 'beginProviderAuthorization')
      .mockImplementation(() =>
        pendingResponse
          ? new Promise((resolve) => {
              finish = resolve;
            })
          : Promise.resolve(transaction),
      );
    const cancel = vi
      .spyOn(providers, 'cancelProviderAuthorization')
      .mockResolvedValue(undefined);
    const view = render(
      createElement(ProviderAuthorizationDialog, {
        provider: {
          authorization_action: 'browser_session',
          display_name: 'YouTube',
          key: 'youtube',
        },
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: '使用隔离浏览器会话' }));
    if (!pendingResponse) await waitFor(() => expect(begin).toHaveBeenCalled());
    view.unmount();
    if (pendingResponse) finish(transaction);
    await Promise.resolve();
    await Promise.resolve();
    expect(cancel).not.toHaveBeenCalled();
  },
);
