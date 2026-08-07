import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { history, request } from '@umijs/max';
import { describe, expect, it, vi } from 'vitest';

import DownloadHistoryPage from '@/pages/DownloadHistory';
import type { DownloadHistory } from '@/types/video';

const requestMock = vi.mocked(request);
const historyPushMock = vi.mocked(history.push);

const historyData: DownloadHistory = {
  items: [
    {
      id: '33333333-3333-4333-8333-333333333333',
      title: 'Owned video',
      thumbnail_url: 'data:image/jpeg;base64,Y292ZXI=',
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

describe('DownloadHistoryPage', () => {
  it('renders the archive and opens a task', async () => {
    requestMock.mockResolvedValueOnce(historyData);
    render(<DownloadHistoryPage />);

    expect(await screen.findByText('Owned video')).toBeInTheDocument();
    expect(screen.getByText('1080p MP4')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '查看任务' }));

    expect(historyPushMock).toHaveBeenCalledWith(
      '/downloads/33333333-3333-4333-8333-333333333333',
    );
  });

  it('gets a short-lived URL for completed history items', async () => {
    requestMock.mockResolvedValueOnce(historyData).mockResolvedValueOnce({
      url: 'https://objects.example/token',
      expires_at: '2026-08-06T10:05:00Z',
    });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
    render(<DownloadHistoryPage />);

    fireEvent.click(await screen.findByRole('button', { name: /获取文件/ }));

    await waitFor(() => expect(click).toHaveBeenCalledOnce());
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      '/api/downloads/33333333-3333-4333-8333-333333333333/download-url',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('guides an empty archive back to a new download', async () => {
    requestMock.mockResolvedValueOnce({
      ...historyData,
      items: [],
      total: 0,
      summary: { total: 0, succeeded: 0, active: 0, failed: 0 },
    });
    render(<DownloadHistoryPage />);

    expect(await screen.findByText('还没有下载记录')).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: /新建下载/ })[1]);
    expect(historyPushMock).toHaveBeenCalledWith('/');
  });
});
