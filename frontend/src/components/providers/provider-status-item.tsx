'use client';

import { CaretDownIcon } from '@phosphor-icons/react';
import { cn } from 'cn';
import { useId, useState } from 'react';
import { ProviderAuthorizationDialog } from '@/components/providers/provider-authorization-dialog';
import { isCurrentlyAvailable } from '@/components/providers/provider-availability';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TableCell, TableHead, TableRow } from '@/components/ui/table';

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

export function ProviderStatusItem({
  provider,
}: {
  provider: API.ProviderListResponse['items'][number];
}) {
  const [expanded, setExpanded] = useState(false);
  const detailsId = useId();
  const capabilities = provider.capabilities
    .map((capability) => CAPABILITY_LABELS[capability])
    .join(' · ');

  return (
    <>
      <TableRow>
        <TableHead
          className="max-w-0 px-4 py-5 text-left align-middle whitespace-normal"
          scope="row"
        >
          <div className="flex min-w-0 flex-col gap-1">
            <h2 className="font-medium">{provider.display_name}</h2>
            <p className="truncate font-mono text-xs font-normal text-muted-foreground">
              {provider.key} · {integrationDescription(provider)}
            </p>
          </div>
        </TableHead>
        <TableCell className="px-4 py-5 whitespace-normal">
          <div className="flex flex-wrap gap-1.5">
            <Badge variant={statusVariant(provider)}>
              {statusLabel(provider)}
            </Badge>
            <Badge variant="outline">
              {accessStateLabel(provider.access_state)}
            </Badge>
          </div>
        </TableCell>
        <TableCell className="px-4 py-5 text-sm leading-6 text-muted-foreground whitespace-normal">
          {capabilities || '暂无已登记能力'}
        </TableCell>
        <TableCell className="px-4 py-5 text-right whitespace-nowrap">
          <Button
            aria-controls={expanded ? detailsId : undefined}
            aria-expanded={expanded}
            className="text-muted-foreground"
            onClick={() => setExpanded((current) => !current)}
            size="sm"
            variant="ghost"
          >
            验证详情
            <CaretDownIcon
              aria-hidden
              className={cn(
                'transition-transform motion-reduce:transition-none',
                expanded && 'rotate-180',
              )}
            />
          </Button>
        </TableCell>
      </TableRow>
      {expanded ? (
        <TableRow>
          <TableCell colSpan={4} className="bg-muted/20 px-4 py-5">
            <div
              className="grid gap-5 text-sm leading-6 text-muted-foreground sm:grid-cols-2"
              id={detailsId}
            >
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
                {provider.access_state === 'authorization_required' &&
                provider.access_modes.includes('operator_managed') &&
                provider.authorization_action !== 'none' ? (
                  <div className="mt-3">
                    <ProviderAuthorizationDialog provider={provider} />
                  </div>
                ) : null}
              </div>
            </div>
          </TableCell>
        </TableRow>
      ) : null}
    </>
  );
}

function accessStateLabel(state: API.ProviderAccessState): string {
  const labels: Record<API.ProviderAccessState, string> = {
    public_probe: '公开线路待验证',
    public_ready: '公开线路可用',
    guest_probe: '游客线路待验证',
    guest_ready: '游客线路可用',
    authorization_required: '需要授权或平台验证',
    operator_probe: '受控线路待验证',
    operator_ready: '受控线路可用',
    degraded: '服务降级',
    blocked: '出口受限',
    disabled: '已停用',
    unsupported: '不支持',
  };
  return labels[state];
}

function statusLabel(
  provider: API.ProviderListResponse['items'][number],
): string {
  if (provider.download_supported) {
    if (isCurrentlyAvailable(provider)) return '当前可用';
    if (provider.status === 'access_required') return '已接入 · 当前不可用';
    if (provider.status === 'degraded') return '支持下载 · 当前降级';
    if (provider.status === 'rate_limited') return '支持下载 · 当前限流';
    if (provider.status === 'blocked') return '支持下载 · 当前受限';
    if (provider.download_available) {
      return '近期媒体样本通过';
    }
    if (provider.status === 'unknown') return '支持下载 · 待复验';
    return '已接入 · 待重新验证';
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

function integrationDescription(
  provider: API.ProviderListResponse['items'][number],
): string {
  if (!provider.registered) return '未登记';
  if (!provider.extractor_exists) return '已登记，暂无解析器';
  if (provider.status === 'disabled') return '仅识别链接，未开放下载';
  return provider.download_supported ? '下载解析器已部署' : '解析器已部署';
}

function accessDescription(
  provider: API.ProviderListResponse['items'][number],
): string {
  const anonymous = provider.access_modes.includes('anonymous');
  const guest = provider.access_modes.includes('guest');
  const operatorManaged = provider.access_modes.includes('operator_managed');
  if (!guest && provider.default_access_policy_id === null) {
    if (operatorManaged && !anonymous) return '服务端受控线路已配置';
    if (operatorManaged) return '匿名公开内容 + 服务端受控线路';
    if (anonymous) return '仅匿名公开内容';
  }
  const routes = [
    anonymous && '匿名公开内容',
    guest && '自动准备的游客线路',
    operatorManaged && '服务端受控线路',
  ].filter(Boolean);
  if (routes.length === 0) return '当前未开放';
  const defaultRoute =
    provider.default_access_policy_id === 'public_session'
      ? '游客线路'
      : provider.default_access_policy_id === 'public'
        ? '匿名公开线路'
        : provider.default_access_policy_id === 'operator_public' ||
            provider.default_access_policy_id === 'personal_entitled'
          ? '服务端受控线路'
          : null;
  return `${routes.join(' + ')}${
    defaultRoute ? ` · 默认：${defaultRoute}` : ''
  }`;
}

function latestCheckDescription(
  provider: API.ProviderListResponse['items'][number],
): string {
  if (!provider.last_checked_at || provider.last_check_succeeded === null) {
    return '状态检查：暂无当前版本记录';
  }
  const outcome = provider.last_check_succeeded ? '通过' : '未通过';
  return `状态检查：${formatDate(provider.last_checked_at, true)} · ${outcome}`;
}

function mediaVerificationDescription(
  provider: API.ProviderListResponse['items'][number],
): string {
  if (!provider.last_media_verified_at) return '真实下载：暂无当前版本证据';
  if (provider.download_available) {
    const sample =
      provider.default_access_policy_id === 'public_session'
        ? '游客线路样本'
        : provider.default_access_policy_id === 'operator_public' ||
            provider.default_access_policy_id === 'personal_entitled'
          ? '受控线路样本'
          : provider.access_modes.includes('operator_managed') &&
              !provider.access_modes.includes('anonymous')
            ? '受控线路样本'
            : provider.access_modes.includes('anonymous')
              ? '公开样本'
              : '样本';
    return `${sample}下载：可用 · ${formatDate(
      provider.last_media_verified_at,
    )}`;
  }
  return `真实下载：${formatDate(provider.last_media_verified_at)}`;
}

function analysisVerificationDescription(
  provider: API.ProviderListResponse['items'][number],
): string {
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
  provider: API.ProviderListResponse['items'][number],
): 'destructive' | 'secondary' | 'default' {
  if (
    isCurrentlyAvailable(provider) ||
    (!provider.download_supported && provider.status === 'verified')
  ) {
    return 'default';
  }
  if (provider.status === 'unsupported' || provider.status === 'blocked') {
    return 'destructive';
  }
  if (
    provider.status === 'access_required' ||
    provider.status === 'degraded' ||
    provider.status === 'rate_limited'
  ) {
    return 'secondary';
  }
  return 'secondary';
}
