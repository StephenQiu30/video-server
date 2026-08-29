'use client';

import { TrendUpIcon } from '@phosphor-icons/react';
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from 'recharts';

import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';
import type { AdminDownloadAnalytics } from '@/services/analytics';

import { formatPercent, formatShortDate } from './analytics-format';

type DailyPoint = AdminDownloadAnalytics['daily'][number];

const completionConfig = {
  rate: { color: 'var(--chart-4)', label: '成功率' },
} satisfies ChartConfig;

export function CompletionRateChart({ daily }: { daily: DailyPoint[] }) {
  const points = [...daily]
    .sort((left, right) => left.date.localeCompare(right.date))
    .map((point) => ({
      date: point.date,
      rate: point.total > 0 ? (point.succeeded / point.total) * 100 : 0,
    }));
  const latest = points.at(-1)?.rate ?? 0;

  return (
    <section aria-labelledby="completion-rate-title">
      <h2
        className="flex items-center gap-2 text-base font-medium"
        id="completion-rate-title"
      >
        <TrendUpIcon aria-hidden className="size-4 text-muted-foreground" />
        完成率走势
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        按天观察成功完成任务的比例变化。
      </p>
      <ChartContainer
        aria-label="每日下载成功率面积图"
        className="mt-5 h-52 w-full aspect-auto"
        config={completionConfig}
        role="img"
      >
        <AreaChart
          accessibilityLayer
          data={points}
          margin={{ left: 0, right: 8, top: 8 }}
        >
          <CartesianGrid stroke="var(--border)" vertical={false} />
          <XAxis
            axisLine={false}
            dataKey="date"
            minTickGap={40}
            tickFormatter={formatShortDate}
            tickLine={false}
          />
          <YAxis
            axisLine={false}
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
            tickLine={false}
            ticks={[0, 50, 100]}
            width={40}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                formatter={(value, name) => (
                  <div className="flex min-w-32 items-center justify-between gap-5">
                    <span className="text-muted-foreground">
                      {String(name) === 'rate' ? '成功率' : String(name)}
                    </span>
                    <span className="font-mono font-medium tabular-nums">
                      {formatPercent(Number(value))}
                    </span>
                  </div>
                )}
                indicator="dot"
                labelFormatter={(label) => formatShortDate(String(label))}
              />
            }
            cursor={false}
          />
          <Area
            dataKey="rate"
            fill="var(--color-rate)"
            fillOpacity={0.28}
            isAnimationActive={false}
            stroke="var(--color-rate)"
            strokeWidth={2}
            type="natural"
          />
        </AreaChart>
      </ChartContainer>
      <p className="mt-4 text-sm font-medium tabular-nums">
        最近一天 {formatPercent(latest)}
      </p>
      <table className="sr-only">
        <caption>每日下载成功率精确数据</caption>
        <thead>
          <tr>
            <th scope="col">日期</th>
            <th scope="col">成功率</th>
          </tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.date}>
              <th scope="row">{point.date}</th>
              <td>{formatPercent(point.rate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
