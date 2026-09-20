import {
  CheckCircleIcon,
  DownloadSimpleIcon,
  HardDrivesIcon,
  UsersThreeIcon,
} from '@phosphor-icons/react';

import {
  Item,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemTitle,
} from '@/components/ui/item';

import {
  formatBytes,
  formatDuration,
  formatInteger,
  formatPercent,
} from './analytics-format';

export function AnalyticsKpis({
  summary,
}: {
  summary: API.DownloadAnalyticsResponse['summary'];
}) {
  const metrics = [
    {
      icon: DownloadSimpleIcon,
      label: '下载总数',
      value: formatInteger(summary.total),
      detail: `成功 ${formatInteger(summary.succeeded)} · 进行中 ${formatInteger(summary.active)}`,
    },
    {
      icon: CheckCircleIcon,
      label: '成功率',
      value: formatPercent(summary.success_rate),
      detail: `失败 ${formatInteger(summary.failed)} · 取消 ${formatInteger(summary.cancelled)}`,
    },
    {
      icon: UsersThreeIcon,
      label: '独立用户',
      value: formatInteger(summary.unique_users),
      detail: '周期内创建下载的用户',
    },
    {
      icon: HardDrivesIcon,
      label: '下载数据量',
      value: formatBytes(summary.downloaded_bytes),
      detail: `平均视频时长 ${formatDuration(summary.average_duration_seconds)}`,
    },
  ];

  return (
    <div>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between sm:gap-6">
        <div>
          <h2 className="text-xl font-medium tracking-[-0.025em]">周期概览</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            当前统计周期的核心下载指标。
          </p>
        </div>
        <p className="text-xs text-muted-foreground sm:block">数据自动汇总</p>
      </div>
      <ItemGroup className="mt-10 grid grid-cols-2 gap-x-8 gap-y-12 sm:grid-cols-4 sm:gap-10">
        {metrics.map((metric) => {
          return (
            <Item
              className="min-w-0 items-start rounded-none border-0 px-0 py-0"
              key={metric.label}
              role="listitem"
            >
              <ItemContent className="gap-0">
                <ItemTitle className="flex items-center gap-2 text-xs font-normal text-muted-foreground">
                  <metric.icon aria-hidden className="size-4" />
                  {metric.label}
                </ItemTitle>
                <p className="mt-3 text-[clamp(2rem,4vw,3.25rem)] font-medium leading-none tracking-[-0.055em] tabular-nums">
                  {metric.value}
                </p>
                <ItemDescription className="mt-3 min-h-9 leading-5 sm:min-h-0">
                  {metric.detail}
                </ItemDescription>
              </ItemContent>
            </Item>
          );
        })}
      </ItemGroup>
    </div>
  );
}
