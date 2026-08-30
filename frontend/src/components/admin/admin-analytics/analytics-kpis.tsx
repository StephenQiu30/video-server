import {
  CheckCircleIcon,
  DownloadSimpleIcon,
  HardDrivesIcon,
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
      progress: summary.success_rate,
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
    <section aria-labelledby="analytics-overview-title">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h2 className="text-lg font-medium" id="analytics-overview-title">
            周期概览
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            当前统计周期的核心下载指标。
          </p>
        </div>
        <p className="hidden text-xs text-muted-foreground sm:block">
          数据自动汇总
        </p>
      </div>
      <dl className="mt-7 grid grid-cols-2 gap-x-6 gap-y-10 lg:grid-cols-4 lg:gap-10">
        {metrics.map((metric) => {
          return (
            <div className="min-w-0" key={metric.label}>
              <dt className="flex items-center gap-2 text-xs text-muted-foreground">
                <metric.icon aria-hidden className="size-4" />
                {metric.label}
              </dt>
              <dd className="mt-3 text-[clamp(1.9rem,4vw,3rem)] font-medium leading-none tracking-[-0.055em] tabular-nums">
                {metric.value}
              </dd>
              <dd className="mt-3 min-h-9 text-xs leading-5 text-muted-foreground sm:min-h-0">
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
    </section>
  );
}
