'use client';

import { ArrowClockwiseIcon } from '@phosphor-icons/react';

import { BackLink } from '@/components/layout/back-link';
import { PageHeader } from '@/components/layout/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Item, ItemGroup } from '@/components/ui/item';
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
      <BackLink className="mb-4" fallbackHref="/" />
      <PageHeader
        action={
          <Button
            disabled={state.loading}
            onClick={state.retry}
            variant="secondary"
          >
            <ArrowClockwiseIcon aria-hidden />
            刷新状态
          </Button>
        }
        description="平台状态同时区分已接入、真实下载证据、完整链路验证和受控会话要求。已接入不代表所有内容类型都可用；这里只展示当前版本的能力与验证状态，不展示账号、Cookie、出口或探针地址。"
        title="平台状态"
        titleId="provider-status-title"
      />

      <div className="mt-10 sm:mt-12">
        {state.loading && !state.data ? (
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
          <ItemGroup aria-label="平台能力状态" asChild className="gap-0">
            <ul>
              {state.data.items.map((provider) => (
                <ProviderRow key={provider.key} provider={provider} />
              ))}
            </ul>
          </ItemGroup>
        ) : null}
      </div>
    </section>
  );
}

function ProviderRow({ provider }: { provider: ProviderStatus }) {
  return (
    <Item
      asChild
      className="grid gap-4 rounded-none border-0 px-0 py-6 md:grid-cols-[minmax(10rem,0.8fr)_minmax(18rem,1.4fr)_minmax(12rem,1fr)] md:items-start"
    >
      <li>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-medium">{provider.display_name}</h2>
            <Badge variant={statusVariant(provider.status)}>
              {statusLabel(provider)}
            </Badge>
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {provider.key}
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            {integrationDescription(provider)}
          </p>
        </div>
        <div>
          {provider.capabilities.length > 0 ? (
            <p className="text-sm leading-6 text-muted-foreground">
              {provider.capabilities
                .map((capability) => CAPABILITY_LABELS[capability])
                .join(' · ')}
            </p>
          ) : (
            <span className="text-sm text-muted-foreground">
              暂无已登记能力
            </span>
          )}
        </div>
        <div className="text-sm leading-6 text-muted-foreground">
          <p>{accessDescription(provider)}</p>
          <p className="mt-1">{mediaVerificationDescription(provider)}</p>
          <p>{analysisVerificationDescription(provider)}</p>
          {provider.user_action ? (
            <p className="mt-2">{provider.user_action}</p>
          ) : null}
        </div>
      </li>
    </Item>
  );
}

function statusLabel(provider: ProviderStatus): string {
  if (
    provider.status === 'unknown' &&
    provider.registered &&
    provider.extractor_exists
  ) {
    return '已接入，待验证';
  }
  return STATUS_LABELS[provider.status];
}

function integrationDescription(provider: ProviderStatus): string {
  if (!provider.registered) return '接入：未登记';
  if (!provider.extractor_exists) return '接入：已登记，暂无解析器';
  return '接入：解析器已部署';
}

function accessDescription(provider: ProviderStatus): string {
  if (provider.access_modes.includes('operator_managed')) {
    return '访问：匿名优先，必要时使用已批准的运维会话';
  }
  if (provider.access_modes.includes('anonymous'))
    return '访问：仅匿名公开内容';
  return '访问：当前未开放';
}

function mediaVerificationDescription(provider: ProviderStatus): string {
  if (!provider.last_media_verified_at) return '最近真实下载：暂无当前版本证据';
  return `最近真实下载：${formatVerificationDate(provider.last_media_verified_at)}`;
}

function analysisVerificationDescription(provider: ProviderStatus): string {
  if (!provider.last_verified_at) return '最近完整分析：暂无当前版本证据';
  return `最近完整分析：${formatVerificationDate(provider.last_verified_at)}`;
}

function formatVerificationDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
  }).format(new Date(value));
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
