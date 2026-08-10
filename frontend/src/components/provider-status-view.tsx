'use client';

import { ArrowClockwiseIcon } from '@phosphor-icons/react';

import { BackLink } from '@/components/back-link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { useProviderStatuses } from '@/hooks/useProviderStatuses';
import type { ProviderStatus } from '@/services/providers';

const STATUS_LABELS: Record<API.ProviderSupportStatus, string> = {
  unknown: '待验证',
  verified: '已验证',
  degraded: '服务降级',
  access_required: '需受控会话',
  rate_limited: '平台限流',
  blocked: '出口受限',
  disabled: '已停用',
  unsupported: '不支持',
};

const CAPABILITY_LABELS: Record<API.ProviderCapability, string> = {
  single_video: '单视频',
  short_video: '短视频',
  clip_or_vod: '片段/VOD',
  audio_video_split: '音视频分离',
  subtitles: '字幕',
  image_or_carousel: '图文/轮播',
  live: '直播',
  playlist: '播放列表',
};

export function ProviderStatusView() {
  const state = useProviderStatuses();

  return (
    <section aria-labelledby="provider-status-title">
      <BackLink fallbackHref="/" />
      <div className="mt-8 flex flex-wrap items-end justify-between gap-5">
        <div className="max-w-3xl">
          <h1
            className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl"
            id="provider-status-title"
          >
            平台状态
          </h1>
          <p className="mt-3 text-sm leading-6 text-muted-foreground sm:text-base">
            登记域名或存在提取器不代表实时可用。这里只展示当前版本的能力、访问模式与最近验证状态，不展示账号、Cookie、出口或探针地址。
          </p>
        </div>
        <Button
          disabled={state.loading}
          onClick={state.retry}
          variant="secondary"
        >
          <ArrowClockwiseIcon aria-hidden />
          刷新状态
        </Button>
      </div>

      <div className="mt-12 border-t border-border">
        {state.loading ? (
          <StatusMessage label="正在加载平台状态" loading />
        ) : null}
        {state.error ? (
          <div className="py-14" role="alert">
            <p className="font-medium text-destructive">{state.error}</p>
            <Button className="mt-4" onClick={state.retry} variant="secondary">
              重试
            </Button>
          </div>
        ) : null}
        {state.data ? (
          <ul aria-label="平台能力状态">
            {state.data.items.map((provider) => (
              <ProviderRow key={provider.key} provider={provider} />
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}

function ProviderRow({ provider }: { provider: ProviderStatus }) {
  return (
    <li className="grid gap-4 border-b border-border py-6 md:grid-cols-[minmax(10rem,0.8fr)_minmax(18rem,1.4fr)_minmax(12rem,1fr)] md:items-start">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-medium">{provider.display_name}</h2>
          <Badge variant={statusVariant(provider.status)}>
            {STATUS_LABELS[provider.status]}
          </Badge>
        </div>
        <p className="mt-1 font-mono text-xs text-muted-foreground">
          {provider.key}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {provider.capabilities.length > 0 ? (
          provider.capabilities.map((capability) => (
            <Badge key={capability} variant="neutral">
              {CAPABILITY_LABELS[capability]}
            </Badge>
          ))
        ) : (
          <span className="text-sm text-muted-foreground">暂无已登记能力</span>
        )}
      </div>
      <div className="text-sm leading-6 text-muted-foreground">
        <p>{accessDescription(provider)}</p>
        <p className="mt-1">{verificationDescription(provider)}</p>
        {provider.user_action ? (
          <p className="mt-2">{provider.user_action}</p>
        ) : null}
      </div>
    </li>
  );
}

function accessDescription(provider: ProviderStatus): string {
  if (provider.access_modes.includes('operator_managed')) {
    return '访问：匿名优先，必要时使用已批准的运维会话';
  }
  if (provider.access_modes.includes('anonymous'))
    return '访问：仅匿名公开内容';
  return '访问：当前未开放';
}

function verificationDescription(provider: ProviderStatus): string {
  if (!provider.last_verified_at) return '最近验证：暂无当前版本证据';
  return `最近验证：${new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
  }).format(new Date(provider.last_verified_at))}`;
}

function statusVariant(
  status: API.ProviderSupportStatus,
): 'destructive' | 'neutral' | 'success' | 'warning' {
  if (status === 'verified') return 'success';
  if (status === 'unsupported' || status === 'blocked') return 'destructive';
  if (
    status === 'access_required' ||
    status === 'degraded' ||
    status === 'rate_limited'
  ) {
    return 'warning';
  }
  return 'neutral';
}

function StatusMessage({
  label,
  loading = false,
}: {
  label: string;
  loading?: boolean;
}) {
  return (
    <div
      aria-label={label}
      className="flex min-h-40 items-center gap-2 text-sm text-muted-foreground"
      role="status"
    >
      {loading ? <Spinner aria-hidden className="size-5" /> : null}
      <span>{label}</span>
    </div>
  );
}
