'use client';

import { Area, AreaChart, CartesianGrid, XAxis } from 'recharts';

import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';

import { ANALYTICS_CHART_COLOR, formatShortDate } from './analytics-format';

type DailyPoint = API.DownloadAnalyticsResponse['daily'][number];

const trendConfig = {
  total: { color: ANALYTICS_CHART_COLOR, label: '全部任务' },
  succeeded: { color: ANALYTICS_CHART_COLOR, label: '成功任务' },
} satisfies ChartConfig;

export function DailyTrendPlot({ points }: { points: DailyPoint[] }) {
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
        margin={{ left: 8, right: 8 }}
      >
        <defs>
          <linearGradient id="fillTotal" x1="0" y1="0" x2="0" y2="1">
            <stop
              offset="5%"
              stopColor="var(--color-total)"
              stopOpacity={0.8}
            />
            <stop
              offset="95%"
              stopColor="var(--color-total)"
              stopOpacity={0.1}
            />
          </linearGradient>
          <linearGradient id="fillSucceeded" x1="0" y1="0" x2="0" y2="1">
            <stop
              offset="5%"
              stopColor="var(--color-succeeded)"
              stopOpacity={0.8}
            />
            <stop
              offset="95%"
              stopColor="var(--color-succeeded)"
              stopOpacity={0.1}
            />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} />
        <XAxis
          axisLine={false}
          dataKey="date"
          minTickGap={32}
          tickFormatter={formatShortDate}
          tickLine={false}
          tickMargin={8}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(label) => formatShortDate(String(label))}
            />
          }
          cursor={false}
        />
        <Area
          dataKey="total"
          fill="url(#fillTotal)"
          isAnimationActive={false}
          stroke="var(--color-total)"
          strokeWidth={2}
          type="natural"
        />
        <Area
          dataKey="succeeded"
          fill="url(#fillSucceeded)"
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
