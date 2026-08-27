import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ProviderStatusView } from '@/components/providers/provider-status-view';
import type { ProviderStatusList } from '@/services/providers';

const runtime = vi.hoisted(() => ({
  listProviders: vi.fn(),
}));

vi.mock('@/services/providers', () => ({
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
  listProviders: runtime.listProviders,
}));

describe('provider status page', () => {
  beforeEach(() => {
    runtime.listProviders.mockReset();
  });

  it('distinguishes registration, verification and controlled access', async () => {
    runtime.listProviders.mockResolvedValue(statuses());
    render(<ProviderStatusView />);

    expect(
      await screen.findByRole('heading', { level: 1, name: '平台状态' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('banner')).toHaveAttribute(
      'data-slot',
      'page-header',
    );
    const list = screen.getByRole('list', { name: '平台能力状态' });
    expect(list).not.toHaveClass('border-y', 'hairline');
    const youtube = within(list)
      .getByRole('heading', { name: 'YouTube' })
      .closest('li');
    expect(youtube).not.toBeNull();
    expect(youtube).not.toHaveClass('border-b', 'hairline');
    expect(youtube).toHaveTextContent('支持下载 · 需会话');
    const capabilities = within(youtube as HTMLElement).getByText(
      '单视频 · 音视频分离',
    );
    expect(capabilities).not.toHaveAttribute('data-slot', 'badge');
    expect(youtube).toHaveTextContent('匿名优先');
    expect(youtube).toHaveTextContent('最近状态检查：暂无当前版本记录');
    expect(youtube).toHaveTextContent('最近真实下载：暂无当前版本证据');
    expect(youtube).toHaveTextContent('最近完整分析：暂无当前版本证据');
    expect(youtube).not.toHaveTextContent('Cookie 版本');

    const bilibili = within(list)
      .getByRole('heading', { name: '哔哩哔哩' })
      .closest('li');
    expect(bilibili).not.toBeNull();
    expect(bilibili).toHaveTextContent('已支持下载');
    expect(bilibili).toHaveTextContent('仅匿名公开内容');
    expect(bilibili).toHaveTextContent('最近状态检查：2026年8月11日');
    expect(bilibili).toHaveTextContent('· 通过');
    expect(bilibili).toHaveTextContent('当前公开样本下载：可用 · 2026年8月9日');
    expect(bilibili).toHaveTextContent('2026年8月10日');

    const hongguo = within(list)
      .getByRole('heading', { name: '红果短剧官方分享' })
      .closest('li');
    expect(hongguo).not.toBeNull();
    expect(hongguo).toHaveTextContent('已支持下载');
    expect(hongguo).toHaveTextContent('下载解析器已部署');
    expect(hongguo).toHaveTextContent('官方分享链接当前单集');
  });

  it('supports loading, safe error and retry states', async () => {
    const first = deferred<ProviderStatusList>();
    const refresh = deferred<ProviderStatusList>();
    runtime.listProviders
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(refresh.promise)
      .mockResolvedValueOnce(statuses());
    render(<ProviderStatusView />);

    expect(
      screen.getByRole('status', { name: '正在加载平台状态' }),
    ).toBeInTheDocument();
    const initialRefresh = screen.getByRole('button', {
      name: '正在刷新平台状态',
    });
    expect(initialRefresh).toBeDisabled();
    expect(initialRefresh).toHaveClass('disabled:opacity-100');
    await act(async () => first.resolve(statuses()));
    expect(await screen.findByText('YouTube')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '刷新状态' }));
    expect(screen.getByText('YouTube')).toBeInTheDocument();
    expect(
      screen.queryByRole('status', { name: '正在加载平台状态' }),
    ).not.toBeInTheDocument();
    await act(async () => refresh.reject(new Error('状态服务暂不可用')));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      '状态服务暂不可用',
    );
    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    expect(await screen.findByText('哔哩哔哩')).toBeInTheDocument();
    expect(runtime.listProviders).toHaveBeenCalledTimes(3);
  });
});

function statuses(): ProviderStatusList {
  return {
    items: [
      {
        key: 'youtube',
        display_name: 'YouTube',
        registered: true,
        extractor_exists: true,
        capabilities: ['single_video', 'audio_video_split'],
        access_modes: ['anonymous', 'operator_managed'],
        status: 'access_required',
        last_checked_at: null,
        last_check_succeeded: null,
        download_supported: true,
        download_available: false,
        last_media_verified_at: null,
        last_verified_at: null,
        user_action: '该平台需要部署已批准的受控会话。',
      },
      {
        key: 'bilibili',
        display_name: '哔哩哔哩',
        registered: true,
        extractor_exists: true,
        capabilities: ['single_video'],
        access_modes: ['anonymous'],
        status: 'verified',
        last_checked_at: '2026-08-11T03:30:00Z',
        last_check_succeeded: true,
        download_supported: true,
        download_available: true,
        last_media_verified_at: '2026-08-09T00:00:00Z',
        last_verified_at: '2026-08-10T00:00:00Z',
        user_action: null,
      },
      {
        key: 'hongguo_web',
        display_name: '红果短剧官方分享',
        registered: true,
        extractor_exists: true,
        capabilities: ['single_video'],
        access_modes: ['anonymous'],
        status: 'unknown',
        last_checked_at: '2026-08-11T03:30:00Z',
        last_check_succeeded: true,
        download_supported: true,
        download_available: true,
        last_media_verified_at: '2026-08-11T03:30:00Z',
        last_verified_at: null,
        user_action:
          '已接入红果官方分享链接当前单集；不支持 App 受保护媒体、全集抓取或批量下载。',
      },
    ],
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, reject, resolve };
}
