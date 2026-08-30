import { ChartLineUpIcon } from '@phosphor-icons/react';

import type { AdminDownloadAnalytics } from '@/services/analytics';
import { DailyTrendDataTable } from './daily-trend-data-table';
import { DailyTrendPlot } from './daily-trend-plot';

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
    <section aria-labelledby="daily-trend-title">
      <h2
        className="flex items-center gap-2 text-lg font-medium"
        id="daily-trend-title"
      >
        <ChartLineUpIcon aria-hidden className="size-5 text-muted-foreground" />
        每日下载趋势
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        使用面积对比每日创建任务与成功完成任务。
      </p>
      <figure className="mt-6 py-2 sm:py-4">
        <p className="sr-only" id="daily-trend-description">
          面积图纵轴从 0 到 {maximum}
          。两层面积分别表示全部任务与成功任务，可悬浮或使用键盘读取单日数据，失败与取消的精确数值见图表后的数据表。
        </p>
        <div className="h-72 w-full sm:h-80 xl:h-96">
          <DailyTrendPlot maximum={maximum} points={points} />
        </div>
        <DailyTrendDataTable points={points} />
      </figure>
    </section>
  );
}
