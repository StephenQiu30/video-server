import { DailyTrendDataTable } from './daily-trend-data-table';
import { DailyTrendPlot } from './daily-trend-plot';

type DailyPoint = API.DownloadAnalyticsResponse['daily'][number];

export function DailyTrendChart({ daily }: { daily: DailyPoint[] }) {
  const points = [...daily].sort((left, right) =>
    left.date.localeCompare(right.date),
  );

  return (
    <div className="w-full">
      <div className="flex flex-col gap-2">
        <h2
          className="text-xl font-medium tracking-[-0.025em]"
          id="daily-trend-title"
        >
          每日下载趋势
        </h2>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          使用面积对比每日创建任务与成功完成任务。
        </p>
      </div>
      <div className="mt-8">
        <p className="sr-only" id="daily-trend-description">
          两层面积分别表示全部任务与成功任务，可悬浮或使用键盘读取单日数据，失败与取消的精确数值见图表后的数据表。
        </p>
        {points.length > 0 ? (
          <div className="h-[280px] w-full sm:h-[320px]">
            <DailyTrendPlot points={points} />
          </div>
        ) : (
          <p className="py-12 text-sm text-muted-foreground">
            当前周期还没有下载数据
          </p>
        )}
        <DailyTrendDataTable points={points} />
      </div>
    </div>
  );
}
