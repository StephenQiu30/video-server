import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import { describe, expect, it, vi } from 'vitest';

import DownloadHistoryView from '@/components/download-history-view';
import type { DownloadHistory } from '@/types/video';
import { mockHttpResponses } from '../helpers/http';

const historyData: DownloadHistory = {
  items: [
    {
      id: '33333333-3333-4333-8333-333333333333',
      title: 'Owned video',
      thumbnail_url: null,
      format_name: '1080p MP4',
      status: 'succeeded',
      progress: 100,
      error_code: null,
      created_at: '2026-08-06T10:00:00Z',
      updated_at: '2026-08-06T10:00:10Z',
      finished_at: '2026-08-06T10:00:10Z',
    },
  ],
  page: 1,
  page_size: 20,
  total: 1,
  summary: { total: 1, succeeded: 1, active: 0, failed: 0 },
};

describe('DownloadHistoryView', () => {
  it('renders the archive and opens a task', async () => {
    mockHttpResponses(historyData);
    const push = vi.fn();
    vi.mocked(useRouter).mockReturnValue({ push } as never);
    render(<DownloadHistoryView />);

    fireEvent.click(await screen.findByRole('button', { name: 'Owned video' }));
    expect(push).toHaveBeenCalledWith(
      '/downloads/?jobId=33333333-3333-4333-8333-333333333333',
    );
  });

  it('downloads completed history items', async () => {
    mockHttpResponses(historyData, {
      url: 'https://objects.example/token',
      expires_at: '2026-08-06T10:05:00Z',
    });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
    render(<DownloadHistoryView />);
    fireEvent.click(await screen.findByRole('button', { name: /获取文件/ }));
    await waitFor(() => expect(click).toHaveBeenCalledOnce());
  });

  it('renders a designed empty state', async () => {
    mockHttpResponses({
      ...historyData,
      items: [],
      total: 0,
      summary: { total: 0, succeeded: 0, active: 0, failed: 0 },
    });
    render(<DownloadHistoryView />);
    expect(await screen.findByText('没有匹配的下载记录')).toBeInTheDocument();
  });
});
