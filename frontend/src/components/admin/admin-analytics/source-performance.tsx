'use client';

import { CaretDownIcon } from '@phosphor-icons/react';

import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import type { AdminDownloadAnalytics } from '@/services/analytics';

import { formatInteger } from './analytics-format';
import { SourcePerformanceDetails } from './source-performance-details';

type Source = AdminDownloadAnalytics['sources'][number];

export function SourcePerformance({ sources }: { sources: Source[] }) {
  const sorted = [...sources].sort((left, right) => right.total - left.total);
  if (sorted.length === 0) return null;

  return (
    <Collapsible>
      <section aria-labelledby="source-performance-title">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-medium" id="source-performance-title">
              来源明细
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              需要精确对比时，再展开各视频源的完整数据。
            </p>
          </div>
          <CollapsibleTrigger asChild>
            <Button
              className="group h-10 w-full justify-between bg-surface sm:w-auto"
              type="button"
              variant="ghost"
            >
              查看 {formatInteger(sorted.length)} 个来源
              <CaretDownIcon
                aria-hidden
                className="transition-transform group-data-[state=open]:rotate-180"
              />
            </Button>
          </CollapsibleTrigger>
        </div>
        <CollapsibleContent>
          <SourcePerformanceDetails sources={sorted} />
        </CollapsibleContent>
      </section>
    </Collapsible>
  );
}
