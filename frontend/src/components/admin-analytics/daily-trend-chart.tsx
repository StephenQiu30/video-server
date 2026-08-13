'use client';

import { useState } from 'react';

import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import type { AdminDownloadAnalytics } from '@/services/analytics';
import { formatInteger } from './analytics-format';
import { DailyTrendDataTable } from './daily-trend-data-table';
import {
  DailyTrendPlot,
  desktopFrame,
  mobileFrame,
  type SeriesKey,
  tabletFrame,
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
    <section aria-labelledby="daily-trend-title" className="pt-2">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-xl font-medium" id="daily-trend-title">
            每日下载趋势
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            对比每日创建、成功、失败和取消的下载任务。
          </p>
        </div>
        <div className="flex items-end gap-8">
          <dl className="hidden gap-6 sm:flex">
            <div>
              <dt className="text-[11px] text-muted-foreground">日均任务</dt>
              <dd className="mt-1 text-sm tabular-nums">
                {formatInteger(Math.round(average))}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] text-muted-foreground">单日峰值</dt>
              <dd className="mt-1 text-sm tabular-nums">
                {formatInteger(peak)}
              </dd>
            </div>
          </dl>
          <ToggleGroup
            aria-label="选择趋势系列"
            onValueChange={(value) => {
              if (value.length > 0) setVisibleSeries(value as SeriesKey[]);
            }}
            type="multiple"
            value={visibleSeries}
          >
            {trendSeries.map((item) => (
              <ToggleGroupItem
                aria-label={`${visibleSeries.includes(item.key) ? '隐藏' : '显示'}${item.label}趋势`}
                key={item.key}
                value={item.key}
              >
                <svg aria-hidden className="h-2 w-5" viewBox="0 0 20 8">
                  <title>{item.label}线型</title>
                  <line
                    className={item.stroke}
                    strokeDasharray={item.dashArray}
                    strokeLinecap="round"
                    strokeWidth={item.width}
                    x1="1"
                    x2="19"
                    y1="4"
                    y2="4"
                  />
                </svg>
                {item.label}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
      </div>

      <figure className="mt-7 overflow-hidden rounded-md bg-surface/55 px-2 pb-1 pt-3 sm:px-4 sm:pt-4">
        <p className="sr-only" id="daily-trend-description">
          折线图纵轴从 0 到 {maximum}
          。四条曲线使用不同线型区分，精确数值见图表后的数据表。
        </p>
        <DailyTrendPlot
          className="h-auto w-full overflow-visible sm:hidden"
          frame={mobileFrame}
          maximum={maximum}
          points={points}
          visibleSeries={visibleSeries}
        />
        <DailyTrendPlot
          className="hidden h-auto w-full overflow-visible sm:block lg:hidden"
          frame={tabletFrame}
          maximum={maximum}
          points={points}
          visibleSeries={visibleSeries}
        />
        <DailyTrendPlot
          className="hidden h-auto w-full overflow-visible lg:block"
          frame={desktopFrame}
          maximum={maximum}
          points={points}
          visibleSeries={visibleSeries}
        />
        <DailyTrendDataTable points={points} />
      </figure>
    </section>
  );
}
