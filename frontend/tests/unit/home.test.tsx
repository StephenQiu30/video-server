import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import { describe, expect, it, vi } from 'vitest';

import DownloadWorkspace from '@/components/download-workspace';
import { httpClient } from '@/lib/request';
import { ApiError } from '@/requestErrorConfig';
import { mockHttpError, mockHttpResponses } from '../helpers/http';
import { inspection, job } from './download-fixtures';

describe('DownloadWorkspace', () => {
  it('renders a focused URL-first workspace', () => {
    render(<DownloadWorkspace />);
    expect(screen.getByLabelText('公开视频地址')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '解析视频' })).toBeEnabled();
    expect(screen.getByText(/公开视频解析与下载/)).toBeInTheDocument();
  });

  it('validates the URL before sending a request', async () => {
    render(<DownloadWorkspace />);
    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));
    expect(
      await screen.findByText('请输入有效的公开 HTTP(S) 视频地址。'),
    ).toBeInTheDocument();
    expect(httpClient.request).not.toHaveBeenCalled();
  });

  it('inspects media and creates a download task', async () => {
    mockHttpResponses(inspection, job());
    const push = vi.fn();
    vi.mocked(useRouter).mockReturnValue({ push } as never);
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => 'stable-key') });
    render(<DownloadWorkspace />);

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://media.example/owned' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));

    expect(await screen.findByText('Owned video')).toBeInTheDocument();
    expect(screen.getByText(/1920×1080/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '开始下载' }));

    await waitFor(() => {
      expect(push).toHaveBeenCalledWith(`/downloads/?jobId=${job().id}`);
    });
    expect(httpClient.request).toHaveBeenCalledTimes(2);
  });

  it('clears stale inspection data after a later failure', async () => {
    mockHttpResponses(inspection);
    mockHttpError(
      new ApiError(
        422,
        'provider_access_required',
        'Provider access required',
        'This provider requires additional access verification.',
      ),
    );
    render(<DownloadWorkspace />);

    const input = screen.getByLabelText('公开视频地址');
    fireEvent.change(input, {
      target: { value: 'https://media.example/owned' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));
    expect(await screen.findByText('Owned video')).toBeInTheDocument();

    fireEvent.change(input, {
      target: { value: 'https://v.douyin.com/example/' },
    });
    fireEvent.click(screen.getByRole('button', { name: '重新解析' }));
    expect(
      await screen.findByText(
        'This provider requires additional access verification.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText('Owned video')).not.toBeInTheDocument();
  });
});
