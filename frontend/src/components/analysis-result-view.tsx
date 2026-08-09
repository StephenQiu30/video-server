'use client';

import type { ReactNode } from 'react';

import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { AnalysisResult } from '@/types/video';
import { formatMilliseconds } from '@/utils/format';

const assetTypeLabels: Record<string, string> = {
  person: '人物',
  location: '地点',
  object: '物体',
  product: '产品',
  logo: '标志',
  on_screen_text: '画面文字',
};

export default function AnalysisResultView({
  onSelectTime,
  result,
}: {
  onSelectTime?: (milliseconds: number) => void;
  result: AnalysisResult;
}) {
  return (
    <Tabs className="mt-10 gap-0" defaultValue="shots">
      <div className="grid gap-5 border-y py-6 sm:grid-cols-3">
        <Metric label="分镜数量" value={`${result.shot_count}`} />
        <Metric
          label="视频时长"
          value={formatMilliseconds(result.media.duration_ms)}
        />
        <Metric label="视觉资产" value={`${result.assets.length}`} />
      </div>
      <section className="mt-8 max-w-4xl">
        <h3 className="text-xl font-medium tracking-[-0.02em]">视觉摘要</h3>
        <p className="mt-3 text-base leading-8 text-muted-foreground">
          {result.summary.text}
        </p>
      </section>
      <div className="mt-10 overflow-x-auto">
        <TabsList
          className="h-auto w-max gap-7 rounded-none p-0"
          variant="line"
        >
          <ResultTab value="shots">分镜</ResultTab>
          <ResultTab value="highlights">高光</ResultTab>
          <ResultTab value="assets">资产</ResultTab>
        </TabsList>
      </div>
      <TabsContent className="pt-7" value="shots">
        <ol className="divide-y border-y">
          {result.shots.map((shot) => (
            <li
              className="grid gap-4 py-6 sm:grid-cols-[72px_minmax(0,1fr)]"
              key={shot.id}
            >
              <TimeButton
                milliseconds={shot.start_ms}
                onSelect={onSelectTime}
              />
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <strong className="font-medium">分镜 {shot.index}</strong>
                  <Badge variant="outline">{shot.shot_size}</Badge>
                  <Badge variant="outline">{shot.camera_motion}</Badge>
                </div>
                <p className="mt-2 leading-7 text-muted-foreground">
                  {shot.description}
                </p>
                {shot.visual_tags.length ? (
                  <p className="mt-3 text-xs text-muted-foreground">
                    {shot.visual_tags.join(' · ')}
                  </p>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      </TabsContent>
      <TabsContent className="pt-7" value="highlights">
        {result.highlights.length ? (
          <ul className="grid gap-4 md:grid-cols-2">
            {result.highlights.map((highlight) => (
              <li className="border p-5" key={highlight.id}>
                <div className="flex items-start justify-between gap-4">
                  <strong className="font-medium">{highlight.title}</strong>
                  <Badge>{highlight.score}</Badge>
                </div>
                <p className="mt-3 leading-7 text-muted-foreground">
                  {highlight.description}
                </p>
                <p className="mt-3 text-sm">{highlight.reason}</p>
                <TimeButton
                  milliseconds={highlight.start_ms}
                  onSelect={onSelectTime}
                />
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>未识别出独立视觉高光。</EmptyState>
        )}
      </TabsContent>
      <TabsContent className="pt-7" value="assets">
        {result.assets.length ? (
          <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {result.assets.map((asset) => (
              <li className="border p-5" key={asset.id}>
                <Badge variant="outline">
                  {assetTypeLabels[asset.type] ?? asset.type}
                </Badge>
                <strong className="mt-3 block font-medium">
                  {asset.label}
                </strong>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {asset.description}
                </p>
                <TimeButton
                  milliseconds={asset.first_seen_ms}
                  onSelect={onSelectTime}
                />
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>未识别出可复用的视觉资产。</EmptyState>
        )}
      </TabsContent>
    </Tabs>
  );
}

function TimeButton({
  milliseconds,
  onSelect,
}: {
  milliseconds: number;
  onSelect?: (milliseconds: number) => void;
}) {
  return (
    <button
      className="mt-3 w-fit font-mono text-xs text-muted-foreground underline-offset-4 enabled:hover:underline disabled:no-underline"
      disabled={!onSelect}
      onClick={() => onSelect?.(milliseconds)}
      type="button"
    >
      {formatMilliseconds(milliseconds)}
    </button>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-2xl">{value}</p>
    </div>
  );
}

function ResultTab({
  children,
  value,
}: {
  children: ReactNode;
  value: string;
}) {
  return (
    <TabsTrigger
      className="rounded-none border-x-0 border-t-0 border-b border-transparent px-0 pt-0 pb-3 data-[state=active]:border-foreground"
      value={value}
    >
      {children}
    </TabsTrigger>
  );
}

function EmptyState({ children }: { children: ReactNode }) {
  return <p className="border-y py-8 text-muted-foreground">{children}</p>;
}
