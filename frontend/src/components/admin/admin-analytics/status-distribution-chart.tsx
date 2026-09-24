'use client';

import { CheckCircleIcon } from '@phosphor-icons/react';
import { Label, Pie, PieChart } from 'recharts';

import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';
import {
  Item,
  ItemActions,
  ItemContent,
  ItemGroup,
  ItemTitle,
} from '@/components/ui/item';

import { formatInteger, formatPercent } from './analytics-format';

enum DownloadAnalyticsStatusCode {
  Succeeded = 'succeeded',
  Active = 'active',
  Failed = 'failed',
  Cancelled = 'cancelled',
}

const statusConfig = {
  [DownloadAnalyticsStatusCode.Succeeded]: {
    color: 'var(--chart-1)',
    label: '成功',
  },
  [DownloadAnalyticsStatusCode.Active]: {
    color: 'var(--chart-2)',
    label: '进行中',
  },
  [DownloadAnalyticsStatusCode.Failed]: {
    color: 'var(--chart-3)',
    label: '失败',
  },
  [DownloadAnalyticsStatusCode.Cancelled]: {
    color: 'var(--chart-4)',
    label: '取消',
  },
} satisfies ChartConfig;

export function StatusDistributionChart({
  summary,
}: {
  summary: API.DownloadAnalyticsResponse['summary'];
}) {
  const data: Array<{
    fill: string;
    status: DownloadAnalyticsStatusCode;
    value: number;
  }> = [
    {
      fill: `var(--color-${DownloadAnalyticsStatusCode.Succeeded})`,
      status: DownloadAnalyticsStatusCode.Succeeded,
      value: summary.succeeded,
    },
    {
      fill: `var(--color-${DownloadAnalyticsStatusCode.Active})`,
      status: DownloadAnalyticsStatusCode.Active,
      value: summary.active,
    },
    {
      fill: `var(--color-${DownloadAnalyticsStatusCode.Failed})`,
      status: DownloadAnalyticsStatusCode.Failed,
      value: summary.failed,
    },
    {
      fill: `var(--color-${DownloadAnalyticsStatusCode.Cancelled})`,
      status: DownloadAnalyticsStatusCode.Cancelled,
      value: summary.cancelled,
    },
  ];

  return (
    <div className="w-full">
      <h2
        className="flex items-center gap-2 text-xl font-medium tracking-[-0.025em]"
        id="status-distribution-title"
      >
        <CheckCircleIcon aria-hidden className="size-4 text-muted-foreground" />
        任务状态
      </h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
        当前周期的完成结构与异常占比。
      </p>
      <div className="mt-8 grid gap-10 sm:grid-cols-[minmax(16rem,18rem)_minmax(0,1fr)] sm:items-center sm:gap-14">
        <ChartContainer
          aria-label="下载任务状态环形图"
          className="mx-auto h-64 w-full max-w-72 aspect-square sm:mx-0"
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
              innerRadius={78}
              isAnimationActive={false}
              nameKey="status"
              outerRadius={108}
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
        <ItemGroup className="grid grid-cols-2 gap-x-8 gap-y-8 sm:grid-cols-4 sm:gap-x-10">
          {data.map((item) => (
            <Item
              className="min-w-0 items-start"
              key={item.status}
              role="listitem"
            >
              <ItemContent className="gap-0">
                <ItemTitle className="flex items-center gap-2">
                  <span
                    aria-hidden
                    className="size-1.5 rounded-full"
                    style={{ backgroundColor: statusConfig[item.status].color }}
                  />
                  {statusConfig[item.status].label}
                </ItemTitle>
                <ItemActions className="mt-2 items-baseline gap-2 tabular-nums">
                  <span className="text-lg font-medium">
                    {formatInteger(item.value)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatPercent(
                      summary.total > 0
                        ? (item.value / summary.total) * 100
                        : 0,
                    )}
                  </span>
                </ItemActions>
              </ItemContent>
            </Item>
          ))}
        </ItemGroup>
      </div>
    </div>
  );
}
