import type { AdminDownloadAnalytics } from '@/services/analytics';

import { DailyTrendDataTable } from './daily-trend-data-table';
import {
  DailyTrendPlot,
  desktopFrame,
  mobileFrame,
  tabletFrame,
  trendSeries,
} from './daily-trend-plot';

type DailyPoint = AdminDownloadAnalytics['daily'][number];

export function DailyTrendChart({ daily }: { daily: DailyPoint[] }) {
  if (daily.length === 0) {
    return (
      <p className="py-12 text-sm text-muted-foreground">暂无趋势数据。</p>
    );
  }

  const points = [...daily].sort((left, right) =>
    left.date.localeCompare(right.date),
  );
  const maximum = Math.max(1, ...points.map((point) => point.total));

  return (
    <section
      aria-labelledby="daily-trend-title"
      className="hairline border-t pt-8"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-medium" id="daily-trend-title">
            每日下载趋势
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            对比每日创建、成功、失败和取消的下载任务。
          </p>
        </div>
        <ul
          aria-label="趋势图图例"
          className="flex flex-wrap gap-x-4 gap-y-2 text-xs"
        >
          {trendSeries.map((item) => (
            <li className="inline-flex items-center gap-2" key={item.key}>
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
            </li>
          ))}
        </ul>
      </div>

      <figure className="mt-7">
        <p className="sr-only" id="daily-trend-description">
          折线图纵轴从 0 到 {maximum}
          。四条曲线使用不同线型区分，精确数值见图表后的数据表。
        </p>
        <DailyTrendPlot
          className="h-auto w-full overflow-visible sm:hidden"
          frame={mobileFrame}
          maximum={maximum}
          points={points}
        />
        <DailyTrendPlot
          className="hidden h-auto w-full overflow-visible sm:block lg:hidden"
          frame={tabletFrame}
          maximum={maximum}
          points={points}
        />
        <DailyTrendPlot
          className="hidden h-auto w-full overflow-visible lg:block"
          frame={desktopFrame}
          maximum={maximum}
          points={points}
        />
        <DailyTrendDataTable points={points} />
      </figure>
    </section>
  );
}
