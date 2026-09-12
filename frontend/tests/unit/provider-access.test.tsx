import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DownloadWorkspace from '@/components/intake/download-workspace';
import { ProviderAccessSelector } from '@/components/intake/provider-access-selector';
import { TooltipProvider } from '@/components/ui/tooltip';
import { providerForInput } from '@/lib/provider-access';
import { inspection } from '../fixtures/download-fixtures';
import { youtubeProvider } from '../fixtures/provider-fixtures';
import { httpRequests, mockHttpResponses } from '../helpers/http';

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock('@/hooks/useProviderStatuses', () => ({
  useProviderStatuses: () => ({
    data: { items: [youtubeProvider] },
    error: null,
    loading: false,
    retry: vi.fn(),
  }),
}));

describe('explicit provider access', () => {
  beforeEach(() => window.history.replaceState({}, '', '/'));

  it('uses only server-supplied hosts and does not rewrite the submitted share text', () => {
    expect(
      providerForInput('分享 https://youtu.be/owned 文案', [youtubeProvider]),
    ).toBe(youtubeProvider);
    expect(
      providerForInput('https://youtube.com.attacker.example/video', [
        youtubeProvider,
      ]),
    ).toBeUndefined();
    expect(providerForInput('not a URL', [youtubeProvider])).toBeUndefined();
  });

  it('clears the old result and changes the idempotency key when policy changes', async () => {
    mockHttpResponses(
      { ...inspection, access_policy_id: 'operator_public' },
      inspection,
    );
    render(
      <TooltipProvider>
        <DownloadWorkspace />
      </TooltipProvider>,
    );
    const url = '分享 https://www.youtube.com/watch?v=owned';
    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: url },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole('combobox'), { key: 'ArrowDown' });
    fireEvent.click(await screen.findByRole('option', { name: '公开无会话' }));
    expect(
      screen.queryByRole('region', { name: '解析结果' }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    const requests = httpRequests();
    expect(requests).toHaveLength(2);
    expect(requests[0].data).toEqual({
      source: {
        kind: 'public_url',
        url,
        access_policy_id: 'operator_public',
      },
    });
    expect(requests[1].data).toEqual({
      source: {
        kind: 'public_url',
        url,
        access_policy_id: 'public',
      },
    });
    expect(requests[0].headers?.['Idempotency-Key']).not.toBe(
      requests[1].headers?.['Idempotency-Key'],
    );
  });

  it('does not enable an unconfigured operator or offer an unadmitted visitor policy', async () => {
    const changed = vi.fn();
    render(
      <ProviderAccessSelector
        provider={{
          ...youtubeProvider,
          access_policies: [
            { id: 'public', configured: true },
            { id: 'operator_public', configured: false },
          ],
        }}
        selected="public"
        disabled={false}
        onChange={changed}
      />,
    );
    fireEvent.keyDown(screen.getByRole('combobox'), { key: 'ArrowDown' });
    const option = await screen.findByRole('option', {
      name: '部署者公开会话（未配置）',
    });
    expect(option).toHaveAttribute('aria-disabled', 'true');
    fireEvent.click(option);
    expect(changed).not.toHaveBeenCalled();
    expect(
      screen.queryByRole('option', { name: '公开访客会话' }),
    ).not.toBeInTheDocument();
  });
});
