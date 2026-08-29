'use client';

import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  XAxis,
  YAxis,
} from 'recharts';

import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';
import type { AdminDownloadAnalytics } from '@/services/analytics';

import { formatInteger, formatPercent } from './analytics-format';

type Source = AdminDownloadAnalytics['sources'][number];

const sourceConfig = {
  total: { color: 'var(--chart-2)', label: '任务数' },
} satisfies ChartConfig;

export function SourceBreakdown({
  sources,
  total,
}: {
  sources: Source[];
  total: number;
}) {
  const sorted = [...sources].sort((left, right) => right.total - left.total);
  const visible = sorted.slice(0, 6).map((source) => {
    const share = total > 0 ? (source.total / total) * 100 : 0;
    return {
      ...source,
      displayValue: `${formatInteger(source.total)} · ${formatPercent(share)}`,
      name: source.source_name || source.source_key,
      share,
    };
  });
  const hiddenCount = Math.max(0, sorted.length - visible.length);

  return (
    <section
      aria-labelledby="source-breakdown-title"
      className="hairline border-y py-8"
    >
      <div className="flex items-end justify-between gap-6">
        <div>
          <h2 className="text-lg font-medium" id="source-breakdown-title">
            来源贡献
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            直观看出各平台贡献的任务量与占比。
          </p>
        </div>
        <p className="shrink-0 text-xs text-muted-foreground tabular-nums">
          {formatInteger(sorted.length)} 个来源
        </p>
      </div>
      {sorted.length === 0 ? (
        <p className="py-12 text-sm text-muted-foreground">暂无来源数据。</p>
      ) : (
        <>
          <ChartContainer
            aria-describedby="source-breakdown-description"
            aria-label="视频来源任务贡献横向条形图"
            className="mt-6 h-72 w-full aspect-auto"
            config={sourceConfig}
            role="img"
          >
            <BarChart
              accessibilityLayer
              data={visible}
              layout="vertical"
              margin={{ left: 0, right: 92 }}
            >
              <CartesianGrid horizontal={false} stroke="var(--border)" />
              <XAxis
                axisLine={false}
                domain={[0, 'dataMax']}
                hide
                tickLine={false}
                type="number"
              />
              <YAxis
                axisLine={false}
                dataKey="name"
                tickLine={false}
                tickMargin={10}
                type="category"
                width={76}
              />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    formatter={(value, _name, item) => (
                      <div className="grid min-w-36 grid-cols-[1fr_auto] items-center gap-x-5 gap-y-1">
                        <span className="col-span-2 font-medium">
                          {String(item.payload.name)}
                        </span>
                        <span className="text-muted-foreground">任务数</span>
                        <span className="text-right font-mono font-medium tabular-nums">
                          {formatInteger(Number(value))}
                        </span>
                        <span className="text-muted-foreground">占比</span>
                        <span className="text-right font-mono font-medium tabular-nums">
                          {formatPercent(Number(item.payload.share))}
                        </span>
                      </div>
                    )}
                    hideIndicator
                    hideLabel
                  />
                }
                cursor={{ fill: 'var(--muted)', opacity: 0.7 }}
              />
              <Bar
                dataKey="total"
                fill="var(--color-total)"
                radius={[0, 3, 3, 0]}
              >
                <LabelList
                  className="fill-muted-foreground text-[11px]"
                  dataKey="displayValue"
                  offset={8}
                  position="right"
                />
              </Bar>
            </BarChart>
          </ChartContainer>
          <p className="sr-only" id="source-breakdown-description">
            横向条形图按任务数从高到低展示最多六个视频来源，精确数据见下方来源明细。
          </p>
          <ol className="sr-only">
            {visible.map((source) => (
              <li key={source.source_key}>
                <meter
                  aria-label={`${source.name}占全部下载的${formatPercent(source.share)}`}
                  max={100}
                  min={0}
                  value={Number(source.share.toFixed(1))}
                >
                  {formatPercent(source.share)}
                </meter>
              </li>
            ))}
          </ol>
        </>
      )}
      {hiddenCount > 0 ? (
        <p className="hairline mt-6 border-t pt-4 text-xs text-muted-foreground">
          其余 {formatInteger(hiddenCount)} 个来源可在下方明细中查看
        </p>
      ) : null}
    </section>
  );
}
