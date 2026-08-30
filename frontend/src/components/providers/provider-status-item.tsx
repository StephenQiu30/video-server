'use client';

import { CaretDownIcon } from '@phosphor-icons/react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '@/components/ui/item';
import type { ProviderStatus } from '@/services/providers';

const STATUS_LABELS: Record<API.ProviderSupportStatus, string> = {
  unknown: '待验证',
  verified: '已验证',
  degraded: '服务降级',
  access_required: '需要平台授权',
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

export function ProviderStatusItem({ provider }: { provider: ProviderStatus }) {
  const capabilities = provider.capabilities
    .map((capability) => CAPABILITY_LABELS[capability])
    .join(' · ');

  return (
    <Collapsible>
      <Item
        className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-3 rounded-none border-0 px-0 py-5 sm:grid-cols-[minmax(12rem,0.8fr)_minmax(16rem,1.4fr)_auto] sm:items-start"
        role="listitem"
      >
        <ItemContent className="min-w-0">
          <ItemTitle className="line-clamp-none flex-wrap">
            <h2>{provider.display_name}</h2>
            <Badge variant={statusVariant(provider)}>
              {statusLabel(provider)}
            </Badge>
          </ItemTitle>
          <ItemDescription className="line-clamp-none">
            <span className="font-mono text-xs">{provider.key}</span> ·{' '}
            {integrationDescription(provider)}
          </ItemDescription>
        </ItemContent>
        <ItemContent className="col-span-2 row-start-2 min-w-0 sm:col-span-1 sm:col-start-2 sm:row-start-1">
          <ItemDescription className="line-clamp-none leading-6">
            {capabilities || '暂无已登记能力'}
          </ItemDescription>
        </ItemContent>
        <ItemActions className="col-start-2 row-start-1 sm:col-start-3">
          <CollapsibleTrigger asChild>
            <Button
              className="h-11 text-muted-foreground [&[data-state=open]>svg]:rotate-180"
              size="sm"
              variant="ghost"
            >
              验证详情
              <CaretDownIcon
                aria-hidden
                className="transition-transform motion-reduce:transition-none"
              />
            </Button>
          </CollapsibleTrigger>
        </ItemActions>
        <CollapsibleContent className="col-span-2 sm:col-span-3">
          <div className="mt-3 grid gap-5 text-sm leading-6 text-muted-foreground sm:grid-cols-2">
            <div>
              <p className="font-medium text-foreground">验证记录</p>
              <p className="mt-1">{latestCheckDescription(provider)}</p>
              <p>{mediaVerificationDescription(provider)}</p>
              <p>{analysisVerificationDescription(provider)}</p>
            </div>
            <div>
              <p className="font-medium text-foreground">访问与下一步</p>
              <p className="mt-1">{accessDescription(provider)}</p>
              {provider.user_action ? <p>{provider.user_action}</p> : null}
            </div>
          </div>
        </CollapsibleContent>
      </Item>
    </Collapsible>
  );
}

function statusLabel(provider: ProviderStatus): string {
  if (provider.download_supported) {
    if (provider.download_available) return '已支持下载';
    if (provider.status === 'access_required') return '已接入 · 当前不可用';
    if (provider.status === 'degraded') return '支持下载 · 当前降级';
    if (provider.status === 'rate_limited') return '支持下载 · 当前限流';
    if (provider.status === 'blocked') return '支持下载 · 当前受限';
    if (provider.status === 'unknown') return '支持下载 · 待复验';
    return '已支持下载';
  }
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
  if (!provider.registered) return '未登记';
  if (!provider.extractor_exists) return '已登记，暂无解析器';
  if (provider.status === 'disabled') return '仅识别链接，未开放下载';
  return provider.download_supported ? '下载解析器已部署' : '解析器已部署';
}

function accessDescription(provider: ProviderStatus): string {
  const anonymous = provider.access_modes.includes('anonymous');
  const operatorManaged = provider.access_modes.includes('operator_managed');
  if (operatorManaged && !anonymous) return '服务端受控线路已配置';
  if (operatorManaged) return '匿名公开内容 + 服务端受控线路';
  if (anonymous) return '仅匿名公开内容';
  return '当前未开放';
}

function latestCheckDescription(provider: ProviderStatus): string {
  if (!provider.last_checked_at || provider.last_check_succeeded === null) {
    return '状态检查：暂无当前版本记录';
  }
  const outcome = provider.last_check_succeeded ? '通过' : '未通过';
  return `状态检查：${formatDate(provider.last_checked_at, true)} · ${outcome}`;
}

function mediaVerificationDescription(provider: ProviderStatus): string {
  if (!provider.last_media_verified_at) return '真实下载：暂无当前版本证据';
  if (provider.download_available) {
    const sample = provider.access_modes.includes('anonymous')
      ? '公开样本'
      : provider.access_modes.includes('operator_managed')
        ? '受控线路样本'
        : '样本';
    return `${sample}下载：可用 · ${formatDate(provider.last_media_verified_at)}`;
  }
  return `真实下载：${formatDate(provider.last_media_verified_at)}`;
}

function analysisVerificationDescription(provider: ProviderStatus): string {
  if (!provider.last_verified_at) return '完整分析：暂无当前版本证据';
  return `完整分析：${formatDate(provider.last_verified_at)}`;
}

function formatDate(value: string, includeTime = false): string {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    ...(includeTime ? { timeStyle: 'short' as const } : {}),
  }).format(new Date(value));
}

function statusVariant(
  provider: ProviderStatus,
): 'destructive' | 'neutral' | 'success' | 'warning' {
  if (provider.download_available || provider.status === 'verified') {
    return 'success';
  }
  if (provider.status === 'unsupported' || provider.status === 'blocked') {
    return 'destructive';
  }
  if (
    provider.status === 'access_required' ||
    provider.status === 'degraded' ||
    provider.status === 'rate_limited'
  ) {
    return 'warning';
  }
  return 'neutral';
}
