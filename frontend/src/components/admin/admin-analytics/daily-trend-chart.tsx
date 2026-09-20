import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DailyTrendDataTable } from './daily-trend-data-table';
import { DailyTrendPlot } from './daily-trend-plot';

type DailyPoint = API.DownloadAnalyticsResponse['daily'][number];

const periodLabels = {
  7: '最近 7 天',
  30: '最近 30 天',
  90: '最近 3 个月',
} as const;

export function DailyTrendChart({
  daily,
  days,
  onDaysChange,
}: {
  daily: DailyPoint[];
  days: 7 | 30 | 90;
  onDaysChange: (days: 7 | 30 | 90) => void;
}) {
  const points = [...daily].sort((left, right) =>
    left.date.localeCompare(right.date),
  );

  return (
    <Card
      aria-labelledby="daily-trend-title"
      className="border-0 bg-transparent py-0 text-foreground shadow-none ring-0"
      role="region"
    >
      <CardHeader className="flex items-center gap-2 px-0 py-0 sm:flex-row">
        <div className="grid flex-1 gap-1">
          <CardTitle id="daily-trend-title">每日下载趋势</CardTitle>
          <CardDescription>
            使用面积对比每日创建任务与成功完成任务。
          </CardDescription>
        </div>
        <Select
          value={String(days)}
          onValueChange={(value) => {
            if (value) onDaysChange(Number(value) as 7 | 30 | 90);
          }}
        >
          <SelectTrigger
            aria-label="统计周期"
            className="w-full rounded-lg sm:ml-auto sm:w-40"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="rounded-xl">
            {Object.entries(periodLabels).map(([value, label]) => (
              <SelectItem className="rounded-lg" key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent className="px-0 pt-6">
        <p className="sr-only" id="daily-trend-description">
          两层面积分别表示全部任务与成功任务，可悬浮或使用键盘读取单日数据，失败与取消的精确数值见图表后的数据表。
        </p>
        {points.length > 0 ? (
          <div className="h-[250px] w-full">
            <DailyTrendPlot points={points} />
          </div>
        ) : (
          <p className="py-12 text-sm text-muted-foreground">
            当前周期还没有下载数据
          </p>
        )}
        <DailyTrendDataTable points={points} />
      </CardContent>
    </Card>
  );
}
