'use client';

import { Area, AreaChart, CartesianGrid, Line, XAxis, YAxis } from 'recharts';

import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';
import type { AdminDownloadAnalytics } from '@/services/analytics';

import { formatInteger, formatShortDate } from './analytics-format';

export type SeriesKey = 'total' | 'succeeded' | 'failed' | 'cancelled';
type DailyPoint = AdminDownloadAnalytics['daily'][number];

export const trendSeries: Array<{
  color: string;
  dashArray?: string;
  key: SeriesKey;
  label: string;
  width: number;
}> = [
  {
    color: 'var(--chart-1)',
    key: 'total',
    label: '全部',
    width: 2.5,
  },
  {
    color: 'var(--chart-2)',
    dashArray: '7 4',
    key: 'succeeded',
    label: '成功',
    width: 2,
  },
  {
    color: 'var(--chart-5)',
    dashArray: '2 5',
    key: 'failed',
    label: '失败',
    width: 1.75,
  },
  {
    color: 'var(--chart-3)',
    dashArray: '8 3 2 3',
    key: 'cancelled',
    label: '取消',
    width: 1.5,
  },
];

const trendConfig = {
  total: { color: 'var(--chart-1)', label: '全部' },
  succeeded: { color: 'var(--chart-2)', label: '成功' },
  failed: { color: 'var(--chart-5)', label: '失败' },
  cancelled: { color: 'var(--chart-3)', label: '取消' },
} satisfies ChartConfig;

export function DailyTrendPlot({
  maximum,
  points,
  visibleSeries,
}: {
  maximum: number;
  points: DailyPoint[];
  visibleSeries: SeriesKey[];
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
        {visibleSeries.includes('total') ? (
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
            fillOpacity={0.06}
            stroke="var(--color-total)"
            strokeWidth={2.5}
            type="monotone"
          />
        ) : null}
        {trendSeries
          .filter(
            (series) =>
              series.key !== 'total' && visibleSeries.includes(series.key),
          )
          .map((series) => (
            <Line
              activeDot={{
                fill: 'var(--background)',
                r: 3.5,
                stroke: `var(--color-${series.key})`,
                strokeWidth: 2,
              }}
              dataKey={series.key}
              dot={
                showDot
                  ? {
                      fill: 'var(--background)',
                      r: 2.75,
                      stroke: `var(--color-${series.key})`,
                      strokeWidth: 2,
                    }
                  : false
              }
              key={series.key}
              stroke={`var(--color-${series.key})`}
              strokeDasharray={series.dashArray}
              strokeWidth={series.width}
              type="monotone"
            />
          ))}
      </AreaChart>
    </ChartContainer>
  );
}
