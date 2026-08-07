import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { history, request } from '@umijs/max';
import { describe, expect, it, vi } from 'vitest';

import HomePage from '@/pages/Home';
import { ApiError } from '@/requestErrorConfig';
import { inspection, job } from './download-fixtures';

const historyPushMock = vi.mocked(history.push);
const requestMock = vi.mocked(request);

describe('HomePage', () => {
  it('展示聚焦下载任务且没有推广内容的工作区', () => {
    render(<HomePage />);

    expect(screen.getAllByText('新建下载')).not.toHaveLength(0);
    expect(screen.getByLabelText('公开视频地址')).toBeInTheDocument();
    expect(screen.queryByText('支持的平台')).not.toBeInTheDocument();
    expect(screen.queryByText('AI 智能分析预览')).not.toBeInTheDocument();
    expect(
      screen.queryByText(/仅处理你有权下载的公开内容/),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/不支持 Cookie、DRM/)).not.toBeInTheDocument();
  });

  it('发送请求前校验视频地址', async () => {
    render(<HomePage />);

    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));

    expect(
      await screen.findByText('请输入有效的公开 HTTP(S) 视频地址。'),
    ).toBeInTheDocument();
    expect(requestMock).not.toHaveBeenCalled();
  });

  it('完成视频解析、格式选择和任务创建', async () => {
    requestMock.mockResolvedValueOnce(inspection).mockResolvedValueOnce(job());
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn().mockReturnValue('stable-key'),
    });
    render(<HomePage />);

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://media.example/owned' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));

    expect(await screen.findByText('Owned video')).toBeInTheDocument();
    expect(
      screen.getByRole('img', { name: /Owned video 视频封面/ }),
    ).toHaveAttribute('src', inspection.thumbnail_url);
    expect(screen.getByText(/1920 × 1080/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '创建下载任务' }));

    await waitFor(() => {
      expect(historyPushMock).toHaveBeenCalledWith(`/downloads/${job().id}`);
    });
    expect(requestMock).toHaveBeenCalledTimes(2);
  });

  it('重试同一地址时保持幂等键不变', async () => {
    requestMock
      .mockRejectedValueOnce(
        new ApiError(502, 'inspection_failed', '失败', '解析失败'),
      )
      .mockResolvedValueOnce(inspection);
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

    expect(requestHeader(0, 'Idempotency-Key')).toBe(
      requestHeader(1, 'Idempotency-Key'),
    );
  });

  it('后续解析失败时清除上一次结果', async () => {
    requestMock
      .mockResolvedValueOnce(inspection)
      .mockRejectedValueOnce(
        new ApiError(
          422,
          'provider_access_required',
          'Provider access required',
          'This provider requires additional access verification; cookie uploads are not supported.',
        ),
      );
    render(<HomePage />);

    const input = screen.getByLabelText('公开视频地址');
    fireEvent.change(input, {
      target: { value: 'https://media.example/owned' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));
    expect(await screen.findByText('Owned video')).toBeInTheDocument();

    fireEvent.change(input, {
      target: { value: 'https://v.douyin.com/uLK6Ofbm54k/' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));

    expect(
      await screen.findByText(
        'This provider requires additional access verification; cookie uploads are not supported.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText('Owned video')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '创建下载任务' }),
    ).not.toBeInTheDocument();
  });

  it('没有可用格式时禁用下载操作', async () => {
    requestMock.mockResolvedValue({ ...inspection, formats: [] });
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn().mockReturnValue('empty-key'),
    });
    render(<HomePage />);

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://media.example/empty' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析视频' }));

    expect(await screen.findByText('没有可用的下载格式。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '创建下载任务' })).toBeDisabled();
  });
});

function requestHeader(index: number, name: string) {
  const [, options] = requestMock.mock.calls[index] as unknown as [
    string,
    {
      headers?: Record<string, string>;
    },
  ];
  return options.headers?.[name];
}
