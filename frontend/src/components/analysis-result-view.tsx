'use client';

import type { ReactNode } from 'react';

import AnalysisReportPreview from '@/components/analysis-report-preview';
import { Button } from '@/components/ui/button';
import { Item, ItemGroup } from '@/components/ui/item';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { VideoAnalysisResult } from '@/types/video';
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
  reportMarkdown,
  result,
}: {
  onSelectTime?: (milliseconds: number) => void;
  reportMarkdown?: string | null;
  result: VideoAnalysisResult;
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
      <section className="mt-8 w-full">
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
          {reportMarkdown ? (
            <ResultTab value="report">报告预览</ResultTab>
          ) : null}
        </TabsList>
      </div>
      <TabsContent className="pt-7" value="shots">
        <ItemGroup asChild className="hairline gap-0 border-y">
          <ol>
            {result.shots.map((shot) => (
              <Item
                asChild
                className="hairline grid gap-4 rounded-none border-0 border-b px-0 py-6 last:border-b-0 sm:grid-cols-[72px_minmax(0,1fr)]"
                key={shot.id}
              >
                <li>
                  <TimeButton
                    milliseconds={shot.start_ms}
                    onSelect={onSelectTime}
                  />
                  <div>
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <strong className="font-medium">分镜 {shot.index}</strong>
                      <span className="text-xs text-muted-foreground">
                        {shot.shot_size} · {shot.camera_motion}
                      </span>
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
              </Item>
            ))}
          </ol>
        </ItemGroup>
      </TabsContent>
      <TabsContent className="pt-7" value="highlights">
        {result.highlights.length ? (
          <ItemGroup asChild className="hairline gap-0 border-y">
            <ul>
              {result.highlights.map((highlight) => (
                <Item
                  asChild
                  className="hairline block rounded-none border-0 border-b px-0 py-6 last:border-b-0"
                  key={highlight.id}
                >
                  <li>
                    <div className="flex items-start justify-between gap-4">
                      <strong className="font-medium">{highlight.title}</strong>
                      <span className="text-sm text-muted-foreground tabular-nums">
                        评分 {highlight.score}
                      </span>
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
                </Item>
              ))}
            </ul>
          </ItemGroup>
        ) : (
          <EmptyState>未识别出独立视觉高光。</EmptyState>
        )}
      </TabsContent>
      <TabsContent className="pt-7" value="assets">
        {result.assets.length ? (
          <ItemGroup asChild className="hairline gap-0 border-y">
            <ul>
              {result.assets.map((asset) => (
                <Item
                  asChild
                  className="hairline block rounded-none border-0 border-b px-0 py-6 last:border-b-0"
                  key={asset.id}
                >
                  <li>
                    <p className="text-xs text-muted-foreground">
                      {assetTypeLabels[asset.type] ?? asset.type}
                    </p>
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
                </Item>
              ))}
            </ul>
          </ItemGroup>
        ) : (
          <EmptyState>未识别出可复用的视觉资产。</EmptyState>
        )}
      </TabsContent>
      {reportMarkdown ? (
        <TabsContent className="pt-7" value="report">
          <AnalysisReportPreview markdown={reportMarkdown} />
        </TabsContent>
      ) : null}
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
    <Button
      className="mt-2 h-11 w-fit px-0 text-xs text-muted-foreground tabular-nums"
      disabled={!onSelect}
      onClick={() => onSelect?.(milliseconds)}
      type="button"
      variant="link"
    >
      {formatMilliseconds(milliseconds)}
    </Button>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl tabular-nums">{value}</p>
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
