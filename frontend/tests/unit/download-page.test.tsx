import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import DownloadWorkspace from '@/components/download-workspace';
import { TooltipProvider } from '@/components/ui/tooltip';
import { URL_MESSAGE } from '@/utils/validation';
import { inspection, job } from '../fixtures/download-fixtures';
import { httpRequests, mockHttpResponses } from '../helpers/http';

const runtime = vi.hoisted(() => ({
  push: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: runtime.push }),
}));

describe('DownloadWorkspace', () => {
  beforeEach(() => {
    runtime.push.mockReset();
    window.history.replaceState({}, '', '/');
  });

  it('starts with one focused, accessible inspection form', () => {
    renderWorkspace();

    expect(
      screen.getByRole('heading', { name: /把视频，\s*带回本地。/u }),
    ).toBeInTheDocument();
    expect(screen.queryByText('Public media workflow')).not.toBeInTheDocument();
    expect(screen.queryByText('02 / 选择画质')).not.toBeInTheDocument();
    expect(screen.queryByText('03 / 创建任务')).not.toBeInTheDocument();
    expect(screen.getByLabelText('公开视频地址')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '解析媒体' })).toBeEnabled();
    expect(
      screen.queryByRole('region', { name: '解析结果' }),
    ).not.toBeInTheDocument();
  });

  it('rejects an invalid address before making an API request', async () => {
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'file:///tmp/private-video' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText(URL_MESSAGE)).toBeInTheDocument();
    expect(httpRequests()).toHaveLength(0);
  });

  it('inspects a public URL, creates a download, and opens its Next route', async () => {
    mockHttpResponses(inspection, job());
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: ' https://media.example/owned ' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '画质预设' }),
    ).toBeInTheDocument();
    expect(screen.getByText('体积优先')).toBeInTheDocument();
    expect(screen.getByRole('radio')).toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: '创建下载任务' }));

    await waitFor(() =>
      expect(runtime.push).toHaveBeenCalledWith(
        `/downloads/detail?jobId=${encodeURIComponent(job().id)}`,
      ),
    );
    expect(httpRequests()).toMatchObject([
      {
        data: { url: 'https://media.example/owned' },
        headers: { 'Idempotency-Key': expect.any(String) },
        method: 'POST',
        url: '/api/inspections',
      },
      {
        data: {
          format_id: inspection.formats[0].id,
          inspection_id: inspection.id,
        },
        headers: { 'Idempotency-Key': expect.any(String) },
        method: 'POST',
        url: '/api/downloads',
      },
    ]);
  });
});

function renderWorkspace() {
  return render(
    <TooltipProvider>
      <DownloadWorkspace />
    </TooltipProvider>,
  );
}
