'use client';

import type { ReactNode } from 'react';

import EvidenceList from '@/components/evidence-list';
import MindMapTree from '@/components/mind-map-tree';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { AnalysisResult } from '@/types/video';
import { formatMilliseconds } from '@/utils/format';

export default function AnalysisResultView({
  result,
}: {
  result: AnalysisResult;
}) {
  return (
    <Tabs className="mt-10 gap-0" defaultValue="summary">
      <div className="overflow-x-auto">
        <TabsList
          className="h-auto w-max gap-7 rounded-none p-0"
          variant="line"
        >
          <ResultTab value="summary">摘要</ResultTab>
          <ResultTab value="points">关键观点</ResultTab>
          <ResultTab value="actions">行动项</ResultTab>
          <ResultTab value="mind-map">思维导图</ResultTab>
        </TabsList>
      </div>
      <TabsContent className="pt-9" value="summary">
        <section>
          <h3 className="text-xl font-medium tracking-[-0.02em]">摘要</h3>
          <p className="mt-4 max-w-4xl text-base leading-8 text-muted-foreground">
            {result.summary.text}
          </p>
        </section>
        <EvidenceList
          className="mt-9"
          items={result.key_points}
          title="关键要点"
        />
        <div className="mt-12 grid gap-12 lg:grid-cols-2">
          <Chapters result={result} />
          <section>
            <h3 className="text-xl font-medium tracking-[-0.02em]">
              思维导图预览
            </h3>
            <MindMapTree className="mt-5" root={result.mind_map} />
          </section>
        </div>
      </TabsContent>
      <TabsContent className="pt-9" value="points">
        <EvidenceList items={result.key_points} title="关键观点" />
      </TabsContent>
      <TabsContent className="pt-9" value="actions">
        <EvidenceList items={result.action_items} title="行动建议" />
      </TabsContent>
      <TabsContent className="pt-9" value="mind-map">
        <MindMapTree root={result.mind_map} />
      </TabsContent>
    </Tabs>
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

function Chapters({ result }: { result: AnalysisResult }) {
  return (
    <section>
      <h3 className="text-xl font-medium tracking-[-0.02em]">章节</h3>
      <ol className="mt-5 divide-y border-y">
        {result.chapters.map((chapter) => (
          <li
            className="grid grid-cols-[64px_minmax(0,1fr)] gap-4 py-5"
            key={`${chapter.start_ms}-${chapter.title}`}
          >
            <span className="font-mono text-xs text-muted-foreground">
              {formatMilliseconds(chapter.start_ms)}
            </span>
            <span>
              <strong className="text-sm font-medium">{chapter.title}</strong>
              <span className="mt-1 block text-sm leading-6 text-muted-foreground">
                {chapter.summary}
              </span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
