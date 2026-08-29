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

  it('distinguishes registration, verification and availability', async () => {
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
    expect(youtube).toHaveTextContent('已接入 · 当前不可用');
    const capabilities = within(youtube as HTMLElement).getByText(
      '单视频 · 音视频分离',
    );
    expect(capabilities).not.toHaveAttribute('data-slot', 'badge');
    expect(youtube).toHaveTextContent('仅匿名公开内容');
    expect(youtube).toHaveTextContent('最近状态检查：暂无当前版本记录');
    expect(youtube).toHaveTextContent('最近真实下载：暂无当前版本证据');
    expect(youtube).toHaveTextContent('最近完整分析：暂无当前版本证据');
    expect(youtube).not.toHaveTextContent('Cookie 版本');

    const tiktok = within(list)
      .getByRole('heading', { name: 'TikTok' })
      .closest('li');
    expect(tiktok).not.toBeNull();
    expect(tiktok).toHaveTextContent('已支持下载');
    expect(tiktok).toHaveTextContent('仅匿名公开内容');
    expect(tiktok).toHaveTextContent('当前公开样本下载：可用 · 2026年8月29日');

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

    const qqvideo = within(list)
      .getByRole('heading', { name: '腾讯视频' })
      .closest('li');
    expect(qqvideo).not.toBeNull();
    expect(qqvideo).toHaveTextContent('已停用');
    expect(qqvideo).toHaveTextContent('访问：当前未开放');
    expect(qqvideo).toHaveTextContent('仅识别链接，未开放安全下载通道');
    expect(qqvideo).toHaveTextContent('支持识别腾讯视频单视频链接');
    expect(qqvideo).toHaveTextContent('VIP、付费及 DRM 内容不提供下载');
    expect(qqvideo).not.toHaveTextContent('运维');
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

  it('labels operator-only evidence without calling it a public sample', async () => {
    const operatorOnly = statuses().items[1];
    runtime.listProviders.mockResolvedValue({
      items: [
        {
          ...operatorOnly,
          key: 'operator-only',
          display_name: '受控线路示例',
          access_modes: ['operator_managed'],
        },
      ],
    });
    render(<ProviderStatusView />);

    const provider = (
      await screen.findByRole('heading', { name: '受控线路示例' })
    ).closest('li');
    expect(provider).not.toBeNull();
    expect(provider).toHaveTextContent('当前受控线路样本下载：可用');
    expect(provider).not.toHaveTextContent('当前公开样本下载');
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
        access_modes: ['anonymous'],
        status: 'access_required',
        last_checked_at: null,
        last_check_succeeded: null,
        download_supported: true,
        download_available: false,
        last_media_verified_at: null,
        last_verified_at: null,
        user_action:
          '该平台当前要求额外授权或验证；请稍后重试，或上传你拥有或已获授权的文件。',
      },
      {
        key: 'tiktok',
        display_name: 'TikTok',
        registered: true,
        extractor_exists: true,
        capabilities: ['single_video', 'short_video'],
        access_modes: ['anonymous'],
        status: 'verified',
        last_checked_at: '2026-08-29T03:33:50Z',
        last_check_succeeded: true,
        download_supported: true,
        download_available: true,
        last_media_verified_at: '2026-08-29T03:33:50Z',
        last_verified_at: null,
        user_action: null,
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
      {
        key: 'qqvideo',
        display_name: '腾讯视频',
        registered: true,
        extractor_exists: true,
        capabilities: ['single_video'],
        access_modes: [],
        status: 'disabled',
        last_checked_at: null,
        last_check_succeeded: null,
        download_supported: false,
        download_available: false,
        last_media_verified_at: null,
        last_verified_at: null,
        user_action:
          '支持识别腾讯视频单视频链接并引导官方播放；消费端私有接口、VIP、付费及 DRM 内容不提供下载。自有媒资请通过腾讯云 VOD 官方导出或上传明文文件。',
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
