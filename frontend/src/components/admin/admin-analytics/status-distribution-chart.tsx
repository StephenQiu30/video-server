'use client';

import { CheckCircleIcon } from '@phosphor-icons/react';
import { Label, Pie, PieChart } from 'recharts';

import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';
import type { AdminDownloadAnalytics } from '@/services/analytics';

import { formatInteger, formatPercent } from './analytics-format';

const statusConfig = {
  succeeded: { color: 'var(--chart-2)', label: '成功' },
  active: { color: 'var(--chart-1)', label: '进行中' },
  failed: { color: 'var(--chart-5)', label: '失败' },
  cancelled: { color: 'var(--chart-3)', label: '取消' },
} satisfies ChartConfig;

export function StatusDistributionChart({
  summary,
}: {
  summary: AdminDownloadAnalytics['summary'];
}) {
  const data: Array<{
    fill: string;
    status: keyof typeof statusConfig;
    value: number;
  }> = [
    {
      fill: 'var(--color-succeeded)',
      status: 'succeeded',
      value: summary.succeeded,
    },
    {
      fill: 'var(--color-active)',
      status: 'active',
      value: summary.active,
    },
    {
      fill: 'var(--color-failed)',
      status: 'failed',
      value: summary.failed,
    },
    {
      fill: 'var(--color-cancelled)',
      status: 'cancelled',
      value: summary.cancelled,
    },
  ];

  return (
    <section aria-labelledby="status-distribution-title">
      <h2
        className="flex items-center gap-2 text-base font-medium"
        id="status-distribution-title"
      >
        <CheckCircleIcon aria-hidden className="size-4 text-muted-foreground" />
        任务状态
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        当前周期的完成结构与异常占比。
      </p>
      <ChartContainer
        aria-label="下载任务状态环形图"
        className="mx-auto mt-3 h-52 w-full max-w-64 aspect-square"
        config={statusConfig}
        role="img"
      >
        <PieChart accessibilityLayer>
          <ChartTooltip
            content={<ChartTooltipContent hideLabel nameKey="status" />}
            cursor={false}
          />
          <Pie
            data={data}
            dataKey="value"
            innerRadius={62}
            isAnimationActive={false}
            nameKey="status"
            outerRadius={84}
            stroke="var(--background)"
            strokeWidth={3}
          >
            <Label
              content={({ viewBox }) => {
                if (!viewBox || !('cx' in viewBox) || !('cy' in viewBox)) {
                  return null;
                }
                return (
                  <text
                    dominantBaseline="middle"
                    textAnchor="middle"
                    x={viewBox.cx}
                    y={viewBox.cy}
                  >
                    <tspan
                      className="fill-foreground text-2xl font-medium tabular-nums"
                      x={viewBox.cx}
                      y={viewBox.cy}
                    >
                      {formatInteger(summary.total)}
                    </tspan>
                    <tspan
                      className="fill-muted-foreground text-[11px]"
                      x={viewBox.cx}
                      y={(viewBox.cy ?? 0) + 21}
                    >
                      全部任务
                    </tspan>
                  </text>
                );
              }}
            />
          </Pie>
        </PieChart>
      </ChartContainer>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
        {data.map((item) => (
          <div className="min-w-0" key={item.status}>
            <dt className="flex items-center gap-2 text-xs text-muted-foreground">
              <span
                aria-hidden
                className="size-1.5 rounded-full"
                style={{ backgroundColor: item.fill }}
              />
              {statusConfig[item.status].label}
            </dt>
            <dd className="mt-1 flex items-baseline gap-2 tabular-nums">
              <span className="text-base font-medium">
                {formatInteger(item.value)}
              </span>
              <span className="text-[11px] text-muted-foreground">
                {formatPercent(
                  summary.total > 0 ? (item.value / summary.total) * 100 : 0,
                )}
              </span>
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
