'use client';

import { useState } from 'react';

import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import type { AdminDownloadAnalytics } from '@/services/analytics';
import { formatInteger } from './analytics-format';
import { DailyTrendDataTable } from './daily-trend-data-table';
import {
  DailyTrendPlot,
  type SeriesKey,
  trendSeries,
} from './daily-trend-plot';

type DailyPoint = AdminDownloadAnalytics['daily'][number];

export function DailyTrendChart({ daily }: { daily: DailyPoint[] }) {
  const [visibleSeries, setVisibleSeries] = useState<SeriesKey[]>(
    trendSeries.map((item) => item.key),
  );

  if (daily.length === 0) {
    return (
      <p className="py-12 text-sm text-muted-foreground">暂无趋势数据。</p>
    );
  }

  const points = [...daily].sort((left, right) =>
    left.date.localeCompare(right.date),
  );
  const maximum = Math.max(1, ...points.map((point) => point.total));
  const average =
    points.reduce((total, point) => total + point.total, 0) / points.length;
  const peak = Math.max(...points.map((point) => point.total));

  return (
    <section aria-labelledby="daily-trend-title">
      <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-lg font-medium" id="daily-trend-title">
            下载趋势
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            按天对比任务创建与完成情况。
          </p>
        </div>
        <dl className="flex gap-8 md:justify-end">
          <div>
            <dt className="text-[11px] text-muted-foreground">日均任务</dt>
            <dd className="mt-1 text-sm tabular-nums">
              {formatInteger(Math.round(average))}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] text-muted-foreground">单日峰值</dt>
            <dd className="mt-1 text-sm tabular-nums">{formatInteger(peak)}</dd>
          </div>
        </dl>
      </div>
      <div className="mt-5 flex items-center justify-between gap-4">
        <p className="hidden text-xs text-muted-foreground sm:block">
          点击图例可隐藏或显示系列
        </p>
        <ToggleGroup
          aria-label="选择趋势系列"
          className="w-full justify-between gap-0 sm:w-auto sm:justify-end sm:gap-1"
          onValueChange={(value) => {
            if (value.length > 0) setVisibleSeries(value as SeriesKey[]);
          }}
          type="multiple"
          value={visibleSeries}
        >
          {trendSeries.map((item) => (
            <ToggleGroupItem
              aria-label={`${visibleSeries.includes(item.key) ? '隐藏' : '显示'}${item.label}趋势`}
              className="min-w-0 flex-1 px-2 sm:flex-none"
              key={item.key}
              value={item.key}
            >
              <span
                aria-hidden
                className="w-5 border-t-2"
                style={{
                  borderColor: item.color,
                  borderTopStyle: item.dashArray ? 'dashed' : 'solid',
                }}
              />
              {item.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </div>

      <figure className="mt-3 overflow-hidden rounded-md bg-surface/70 px-2 pb-1 pt-3 sm:px-4 sm:pt-4">
        <p className="sr-only" id="daily-trend-description">
          折线图纵轴从 0 到 {maximum}
          。四条曲线使用不同线型区分，可悬浮或使用键盘读取单日数据，精确数值见图表后的数据表。
        </p>
        <div className="h-64 w-full sm:h-72 xl:h-80">
          <DailyTrendPlot
            maximum={maximum}
            points={points}
            visibleSeries={visibleSeries}
          />
        </div>
        <DailyTrendDataTable points={points} />
      </figure>
    </section>
  );
}
