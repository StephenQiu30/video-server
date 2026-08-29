'use client';

import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from 'recharts';

import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';
import type { AdminDownloadAnalytics } from '@/services/analytics';

import { formatInteger, formatShortDate } from './analytics-format';

type DailyPoint = AdminDownloadAnalytics['daily'][number];

const trendConfig = {
  total: { color: 'var(--chart-1)', label: '全部任务' },
  succeeded: { color: 'var(--chart-2)', label: '成功任务' },
} satisfies ChartConfig;

export function DailyTrendPlot({
  maximum,
  points,
}: {
  maximum: number;
  points: DailyPoint[];
}) {
  const showDot = points.length === 1;

  return (
    <ChartContainer
      aria-describedby="daily-trend-description"
      aria-label="每日下载任务交互趋势图"
      className="h-full w-full aspect-auto"
      config={trendConfig}
      role="img"
    >
      <AreaChart
        accessibilityLayer
        data={points}
        margin={{ bottom: 4, left: -8, right: 4, top: 8 }}
      >
        <CartesianGrid
          stroke="var(--border)"
          strokeDasharray="3 4"
          vertical={false}
        />
        <XAxis
          axisLine={false}
          dataKey="date"
          minTickGap={48}
          tickFormatter={formatShortDate}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          axisLine={false}
          domain={[0, maximum]}
          tickFormatter={formatInteger}
          tickLine={false}
          width={42}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              indicator="line"
              labelFormatter={(label) => formatShortDate(String(label))}
            />
          }
          cursor={{
            stroke: 'var(--muted-foreground)',
            strokeDasharray: '3 4',
            strokeOpacity: 0.55,
            strokeWidth: 1,
          }}
        />
        <Area
          activeDot={{
            fill: 'var(--background)',
            r: 4,
            stroke: 'var(--color-total)',
            strokeWidth: 2,
          }}
          dataKey="total"
          dot={
            showDot
              ? {
                  fill: 'var(--background)',
                  r: 3,
                  stroke: 'var(--color-total)',
                  strokeWidth: 2,
                }
              : false
          }
          fill="var(--color-total)"
          fillOpacity={0.1}
          isAnimationActive={false}
          stroke="var(--color-total)"
          strokeWidth={2}
          type="natural"
        />
        <Area
          activeDot={{
            fill: 'var(--background)',
            r: 4,
            stroke: 'var(--color-succeeded)',
            strokeWidth: 2,
          }}
          dataKey="succeeded"
          dot={
            showDot
              ? {
                  fill: 'var(--background)',
                  r: 3,
                  stroke: 'var(--color-succeeded)',
                  strokeWidth: 2,
                }
              : false
          }
          fill="var(--color-succeeded)"
          fillOpacity={0.18}
          isAnimationActive={false}
          stroke="var(--color-succeeded)"
          strokeWidth={2}
          type="natural"
        />
        <ChartLegend content={<ChartLegendContent />} />
      </AreaChart>
    </ChartContainer>
  );
}
