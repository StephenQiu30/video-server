import { Progress } from '@/components/ui/progress';
import type { AdminDownloadAnalytics } from '@/services/analytics';

import { formatInteger, formatPercent } from './analytics-format';

type Source = AdminDownloadAnalytics['sources'][number];

export function SourceBreakdown({
  sources,
  total,
}: {
  sources: Source[];
  total: number;
}) {
  const sorted = [...sources].sort((left, right) => right.total - left.total);

  return (
    <section aria-labelledby="source-breakdown-title" className="pt-2">
      <h2 className="text-xl font-medium" id="source-breakdown-title">
        视频源分布
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        各视频源在当前统计周期内的下载任务占比。
      </p>
      {sorted.length === 0 ? (
        <p className="py-12 text-sm text-muted-foreground">暂无来源数据。</p>
      ) : (
        <ol className="mt-7 space-y-6">
          {sorted.map((source) => {
            const share = total > 0 ? (source.total / total) * 100 : 0;
            return (
              <li key={source.source_key}>
                <div className="flex items-end justify-between gap-5">
                  <div className="min-w-0">
                    <p className="truncate font-medium">
                      {source.source_name || source.source_key}
                    </p>
                    {source.source_name !== source.source_key ? (
                      <p className="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">
                        {source.source_key}
                      </p>
                    ) : null}
                  </div>
                  <p className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                    {formatInteger(source.total)} · {formatPercent(share)}
                  </p>
                </div>
                <meter
                  aria-label={`${source.source_name || source.source_key}占全部下载的${formatPercent(share)}`}
                  className="sr-only"
                  max={100}
                  min={0}
                  value={Number(share.toFixed(1))}
                >
                  {formatPercent(share)}
                </meter>
                <Progress
                  aria-hidden
                  className="mt-2 h-2"
                  value={Math.min(100, share)}
                />
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
