import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createElement } from 'react';
import { expect, it, vi } from 'vitest';
import * as providers from '@/api/providers';
import { ProviderAuthorizationDialog } from '@/components/providers/provider-authorization-dialog';
import {
  providerAuthorizationTarget,
  requestBrowserProviderSync,
} from '@/lib/provider-authorization';

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
    screen.queryByRole('button', { name: '使用当前 Chrome 会话' }),
  ).not.toBeInTheDocument();
});

it('accepts only the correlated provider acknowledgement with a revision', async () => {
  let outbound:
    | { provider: string; requestId: string; transactionId: string }
    | undefined;
  const postMessage = vi
    .spyOn(window, 'postMessage')
    .mockImplementation((message) => {
      if (message?.type === 'framefetch:provider-sync') outbound = message;
    });
  const request = requestBrowserProviderSync('youtube', TRANSACTION_ID, 1_000);
  expect(outbound).toBeDefined();
  expect(outbound?.transactionId).toBe(TRANSACTION_ID);

  dispatchBridgeResult({
    ok: true,
    provider: 'reddit',
    requestId: outbound?.requestId,
    revision: 'stale-revision',
  });
  dispatchBridgeResult({
    ok: true,
    provider: 'youtube',
    requestId: outbound?.requestId,
    revision: 'current-revision',
  });

  await expect(request).resolves.toBeUndefined();
  postMessage.mockRestore();
});

it('rejects an acknowledgement without a native bridge revision', async () => {
  let outbound:
    | { provider: string; requestId: string; transactionId: string }
    | undefined;
  const postMessage = vi
    .spyOn(window, 'postMessage')
    .mockImplementation((message) => {
      if (message?.type === 'framefetch:provider-sync') outbound = message;
    });
  const request = requestBrowserProviderSync('youtube', TRANSACTION_ID, 1_000);

  dispatchBridgeResult({
    ok: true,
    provider: 'youtube',
    requestId: outbound?.requestId,
    revision: null,
  });

  await expect(request).rejects.toThrow('浏览器连接器未能同步当前平台会话');
  postMessage.mockRestore();
});

it('cancels the server intent when browser synchronization fails', async () => {
  const begin = vi
    .spyOn(providers, 'beginProviderAuthorization')
    .mockResolvedValue({
      expires_at: '2026-09-22T12:10:00Z',
      provider_key: 'youtube',
      status: 'pending',
      transaction_id: TRANSACTION_ID,
    });
  const cancel = vi
    .spyOn(providers, 'cancelProviderAuthorization')
    .mockResolvedValue(undefined);
  const postMessage = vi
    .spyOn(window, 'postMessage')
    .mockImplementation((message) => {
      if (message?.type !== 'framefetch:provider-sync') return;
      dispatchBridgeResult({
        provider: message.provider,
        requestId: message.requestId,
        ok: false,
      });
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
  fireEvent.click(screen.getByRole('button', { name: '使用当前 Chrome 会话' }));
  await waitFor(() =>
    expect(
      screen.getByText('浏览器连接器未能同步当前平台会话。'),
    ).toBeInTheDocument(),
  );
  expect(begin).toHaveBeenCalledOnce();
  expect(cancel).toHaveBeenCalledWith({ transaction_id: TRANSACTION_ID });
  postMessage.mockRestore();
});

function dispatchBridgeResult(value: object) {
  window.dispatchEvent(
    new MessageEvent('message', {
      data: { type: 'framefetch:provider-sync:result', ...value },
      origin: window.location.origin,
      source: window,
    }),
  );
}
