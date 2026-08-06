import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import HomePage from '@/pages/Home';
import { inspection, job, jsonResponse } from './download-fixtures';

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.history.replaceState({}, '', '/');
});

describe('HomePage', () => {
  it('shows the downloader and explicit legal boundary', () => {
    render(<HomePage />);

    expect(
      screen.getByRole('heading', { name: '万能视频下载与智能分析' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('公开视频地址')).toBeInTheDocument();
    expect(screen.getByText(/仅处理你有权下载的公开内容/)).toBeInTheDocument();
    expect(screen.getByText(/不支持 Cookie、DRM/)).toBeInTheDocument();
  });

  it('validates the URL before sending a request', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    render(<HomePage />);

    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));

    expect(
      screen.getByText('请输入有效的公开 HTTP(S) 视频地址。'),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('completes inspection, format selection, and job creation', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(inspection, 201))
      .mockResolvedValueOnce(jsonResponse(job(), 202));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn().mockReturnValue('stable-key'),
    });
    render(<HomePage />);

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://media.example/owned' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));

    expect(await screen.findByText('Owned video')).toBeInTheDocument();
    expect(screen.getByText(/1920 × 1080/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '开始下载' }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(`/downloads/${job().id}`);
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('keeps the idempotency key stable when retrying the same URL', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(
          {
            status: 502,
            code: 'inspection_failed',
            title: '失败',
            detail: '解析失败',
          },
          502,
        ),
      )
      .mockResolvedValueOnce(jsonResponse(inspection, 201));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('crypto', {
      randomUUID: vi
        .fn()
        .mockReturnValueOnce('stable-key')
        .mockReturnValueOnce('new-key'),
    });
    render(<HomePage />);

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://media.example/owned' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));
    expect(await screen.findByText('解析失败')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));
    expect(await screen.findByText('Owned video')).toBeInTheDocument();

    expect(requestHeader(fetchMock, 0, 'Idempotency-Key')).toBe('stable-key');
    expect(requestHeader(fetchMock, 1, 'Idempotency-Key')).toBe('stable-key');
  });

  it('shows an empty format result without enabling download', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(jsonResponse({ ...inspection, formats: [] }, 201)),
    );
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn().mockReturnValue('empty-key'),
    });
    render(<HomePage />);

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://media.example/empty' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));

    expect(await screen.findByText('没有可用的下载格式。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '开始下载' })).toBeDisabled();
  });
});

function requestHeader(
  fetchMock: ReturnType<typeof vi.fn>,
  index: number,
  name: string,
) {
  return (fetchMock.mock.calls[index][0] as Request).headers.get(name);
}
