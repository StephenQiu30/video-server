'use client';

import { ChartBarIcon } from '@phosphor-icons/react';
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts';

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
  total: { color: 'var(--chart-3)', label: '任务数' },
} satisfies ChartConfig;

export function SourceBreakdown({
  sources,
  total,
}: {
  sources: Source[];
  total: number;
}) {
  const sorted = [...sources].sort((left, right) => right.total - left.total);
  const visible = sorted.slice(0, 5).map((source) => {
    const share = total > 0 ? (source.total / total) * 100 : 0;
    return {
      ...source,
      name: source.source_name || source.source_key,
      share,
    };
  });
  const hiddenCount = Math.max(0, sorted.length - visible.length);

  return (
    <section aria-labelledby="source-breakdown-title">
      <h2
        className="flex items-center gap-2 text-base font-medium"
        id="source-breakdown-title"
      >
        <ChartBarIcon aria-hidden className="size-4 text-muted-foreground" />
        来源贡献
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        对比主要视频源的任务量与占比。
      </p>
      {sorted.length === 0 ? (
        <p className="py-12 text-sm text-muted-foreground">暂无来源数据。</p>
      ) : (
        <>
          <ChartContainer
            aria-describedby="source-breakdown-description"
            aria-label="视频来源任务贡献条形图"
            className="mt-5 h-52 w-full aspect-auto"
            config={sourceConfig}
            role="img"
          >
            <BarChart
              accessibilityLayer
              data={visible}
              margin={{ left: 0, right: 4, top: 8 }}
            >
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                axisLine={false}
                dataKey="name"
                tickLine={false}
                tickFormatter={(value) => {
                  const label = String(value);
                  return label.length > 5 ? `${label.slice(0, 4)}…` : label;
                }}
              />
              <YAxis
                axisLine={false}
                allowDecimals={false}
                tickLine={false}
                width={32}
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
                isAnimationActive={false}
                radius={[3, 3, 0, 0]}
              />
            </BarChart>
          </ChartContainer>
          <p className="sr-only" id="source-breakdown-description">
            条形图按任务数从高到低展示最多五个视频来源，精确数据见下方来源明细。
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
      <p className="mt-4 text-sm font-medium tabular-nums">
        {formatInteger(sorted.length)} 个来源
        {hiddenCount > 0
          ? ` · 其余 ${formatInteger(hiddenCount)} 个可在明细中查看`
          : ' · 已全部展示'}
      </p>
    </section>
  );
}
