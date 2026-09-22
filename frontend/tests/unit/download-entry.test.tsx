import { fireEvent, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DownloadWorkspace from '@/components/intake/download-workspace';
import { TooltipProvider } from '@/components/ui/tooltip';
import { inspection } from '../fixtures/download-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';
import { render } from '../helpers/query-render';

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));
const statuses = vi.hoisted(() => vi.fn(() => ({ data: null, error: null })));
vi.mock('@/components/providers/use-provider-statuses', () => ({
  useProviderStatuses: statuses,
}));

function enter(url: string) {
  fireEvent.change(screen.getByLabelText('公开视频地址'), {
    target: { value: url },
  });
  fireEvent.click(screen.getByRole('button', { name: /解析/ }));
}

describe('simple download entry', () => {
  beforeEach(() => window.history.replaceState({}, '', '/'));

  it('submits only the input and does not fetch provider configuration', async () => {
    mockHttpResponses({ ...inspection, access_policy_id: 'operator_public' });
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
    expect(httpRequests()).toHaveLength(1);
    expect(httpRequests()[0].data).toEqual({
      source: { kind: 'public_url', url },
    });
  });

  it('clears previous results and changes the key only when input changes', async () => {
    mockHttpResponses(inspection, inspection);
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
    const requests = httpRequests();
    expect(requests[0].headers?.['Idempotency-Key']).not.toBe(
      requests[1].headers?.['Idempotency-Key'],
    );
  });

  it('keeps the input and reuses the key after an uncertain failure', async () => {
    mockHttpError(new Error('request failed'));
    mockHttpResponses(inspection);
    render(
      <TooltipProvider>
        <DownloadWorkspace />
      </TooltipProvider>,
    );
    const url = 'https://youtu.be/owned';
    enter(url);
    await screen.findByText('操作未完成');
    expect(screen.getByLabelText('公开视频地址')).toHaveValue(url);
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
    await screen.findByText(inspection.title);
    const requests = httpRequests();
    expect(requests[0].headers?.['Idempotency-Key']).toBe(
      requests[1].headers?.['Idempotency-Key'],
    );
  });
});
