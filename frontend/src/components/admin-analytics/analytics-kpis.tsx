import {
  DatabaseIcon,
  GaugeIcon,
  TrayIcon,
  UsersThreeIcon,
} from '@phosphor-icons/react';

import { Progress } from '@/components/ui/progress';
import type { AdminDownloadAnalytics } from '@/services/analytics';

import {
  formatBytes,
  formatDuration,
  formatInteger,
  formatPercent,
} from './analytics-format';

export function AnalyticsKpis({
  summary,
}: {
  summary: AdminDownloadAnalytics['summary'];
}) {
  const metrics = [
    {
      label: '下载总数',
      icon: TrayIcon,
      value: formatInteger(summary.total),
      detail: `成功 ${formatInteger(summary.succeeded)} · 进行中 ${formatInteger(summary.active)}`,
    },
    {
      label: '成功率',
      icon: GaugeIcon,
      value: formatPercent(summary.success_rate),
      detail: `失败 ${formatInteger(summary.failed)} · 取消 ${formatInteger(summary.cancelled)}`,
      progress: summary.success_rate,
    },
    {
      label: '独立用户',
      icon: UsersThreeIcon,
      value: formatInteger(summary.unique_users),
      detail: '周期内创建下载的用户',
    },
    {
      label: '下载数据量',
      icon: DatabaseIcon,
      value: formatBytes(summary.downloaded_bytes),
      detail: `平均视频时长 ${formatDuration(summary.average_duration_seconds)}`,
    },
  ];

  return (
    <dl className="grid gap-x-10 gap-y-9 sm:grid-cols-2 xl:grid-cols-4 xl:gap-x-0">
      {metrics.map((metric, index) => {
        const Icon = metric.icon;
        return (
          <div
            className={
              index === 0 ? 'min-w-0' : 'hairline min-w-0 xl:border-l xl:pl-8'
            }
            key={metric.label}
          >
            <dt className="flex items-center gap-2 text-xs text-muted-foreground">
              <Icon aria-hidden className="size-4" />
              {metric.label}
            </dt>
            <dd className="mt-3 font-mono text-[clamp(2rem,4vw,3rem)] font-medium leading-none tracking-[-0.055em] tabular-nums">
              {metric.value}
            </dd>
            <dd className="mt-3 text-xs text-muted-foreground">
              {metric.detail}
            </dd>
            {metric.progress === undefined ? null : (
              <dd className="mt-4">
                <Progress
                  aria-label={`下载成功率 ${formatPercent(metric.progress)}`}
                  className="h-1 bg-muted"
                  value={metric.progress}
                />
              </dd>
            )}
          </div>
        );
      })}
    </dl>
  );
}
