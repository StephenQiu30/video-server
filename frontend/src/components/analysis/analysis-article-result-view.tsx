'use client';

import AnalysisReportPreview from '@/components/analysis/analysis-report-preview';
import { Item, ItemGroup } from '@/components/ui/item';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { VideoArticleResult } from '@/types/video';
import { formatMilliseconds } from '@/utils/format';

export default function AnalysisArticleResultView({
  reportMarkdown,
  result,
}: {
  reportMarkdown?: string | null;
  result: VideoArticleResult;
}) {
  return (
    <Tabs className="mt-10 gap-0" defaultValue="article">
      <div className="grid gap-5 border-y py-6 sm:grid-cols-3">
        <Metric label="文章章节" value={`${result.sections.length}`} />
        <Metric
          label="视频时长"
          value={formatMilliseconds(result.media.duration_ms)}
        />
        <Metric label="核心观点" value={`${result.key_points.length}`} />
      </div>
      <section className="mt-8 w-full">
        <h3 className="text-xl font-medium tracking-[-0.02em]">导读</h3>
        <p className="mt-3 text-base leading-8 text-muted-foreground">
          {result.lead}
        </p>
      </section>
      <div className="mt-10 overflow-x-auto">
        <TabsList className="h-auto w-max gap-7 rounded-none p-0" variant="line">
          <Tab value="article">文章正文</Tab>
          <Tab value="points">核心观点</Tab>
          {reportMarkdown ? <Tab value="report">报告预览</Tab> : null}
        </TabsList>
      </div>
      <TabsContent className="pt-7" value="article">
        <ItemGroup asChild className="hairline gap-0 border-y">
          <ol>
            {result.sections.map((section, index) => (
              <Item
                asChild
                className="hairline block rounded-none border-0 border-b px-0 py-7 last:border-b-0"
                key={section.id}
              >
                <li>
                  <p className="text-xs text-muted-foreground">章节 {index + 1}</p>
                  <h4 className="mt-2 text-xl font-medium">{section.title}</h4>
                  <p className="mt-4 whitespace-pre-line leading-8 text-muted-foreground">
                    {section.body}
                  </p>
                  <div className="mt-5 space-y-1 text-sm text-muted-foreground">
                    {section.evidence.map((evidence) => (
                      <p key={`${evidence.start_ms}-${evidence.end_ms}-${evidence.note}`}>
                        <span className="text-xs tabular-nums">
                          {formatMilliseconds(evidence.start_ms)}–
                          {formatMilliseconds(evidence.end_ms)}
                        </span>{' '}
                        {evidence.note}
                      </p>
                    ))}
                  </div>
                </li>
              </Item>
            ))}
          </ol>
        </ItemGroup>
      </TabsContent>
      <TabsContent className="pt-7" value="points">
        <ul className="list-disc space-y-3 border-y py-6 pl-5 leading-7 text-muted-foreground">
          {result.key_points.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
        {result.limitations.length ? (
          <div className="mt-8 border-y py-6">
            <h4 className="font-medium">说明与局限</h4>
            <ul className="mt-3 list-disc space-y-2 pl-5 leading-7 text-muted-foreground">
              {result.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <p className="mt-8 leading-7 text-muted-foreground">{result.closing}</p>
      </TabsContent>
      {reportMarkdown ? (
        <TabsContent className="pt-7" value="report">
          <AnalysisReportPreview markdown={reportMarkdown} />
        </TabsContent>
      ) : null}
    </Tabs>
  );
}

function Tab({ children, value }: { children: string; value: string }) {
  return (
    <TabsTrigger
      className="rounded-none border-x-0 border-t-0 border-b border-transparent px-0 pt-0 pb-3 data-[state=active]:border-foreground"
      value={value}
    >
      {children}
    </TabsTrigger>
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
