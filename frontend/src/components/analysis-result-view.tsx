'use client';

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
    <Tabs className="mt-8" defaultValue="summary">
      <div className="overflow-x-auto">
        <TabsList>
          <TabsTrigger value="summary">摘要</TabsTrigger>
          <TabsTrigger value="points">关键观点</TabsTrigger>
          <TabsTrigger value="actions">行动项</TabsTrigger>
          <TabsTrigger value="mind-map">思维导图</TabsTrigger>
        </TabsList>
      </div>
      <TabsContent className="pt-7" value="summary">
        <section>
          <h3 className="text-lg font-semibold">摘要</h3>
          <p className="mt-3 max-w-3xl leading-7 text-muted-foreground">
            {result.summary.text}
          </p>
        </section>
        <EvidenceList
          className="mt-9"
          items={result.key_points}
          title="关键要点"
        />
        <div className="mt-10 grid gap-10 lg:grid-cols-2">
          <Chapters result={result} />
          <section>
            <h3 className="text-lg font-semibold">思维导图预览</h3>
            <MindMapTree className="mt-4" root={result.mind_map} />
          </section>
        </div>
      </TabsContent>
      <TabsContent className="pt-7" value="points">
        <EvidenceList items={result.key_points} title="关键观点" />
      </TabsContent>
      <TabsContent className="pt-7" value="actions">
        <EvidenceList items={result.action_items} title="行动建议" />
      </TabsContent>
      <TabsContent className="pt-7" value="mind-map">
        <MindMapTree root={result.mind_map} />
      </TabsContent>
    </Tabs>
  );
}

function Chapters({ result }: { result: AnalysisResult }) {
  return (
    <section>
      <h3 className="text-lg font-semibold">章节</h3>
      <ol className="mt-4 divide-y border-y">
        {result.chapters.map((chapter) => (
          <li
            className="grid grid-cols-[64px_1fr] gap-4 py-4"
            key={`${chapter.start_ms}-${chapter.title}`}
          >
            <span className="font-mono text-xs text-muted-foreground">
              {formatMilliseconds(chapter.start_ms)}
            </span>
            <span>
              <strong className="text-sm">{chapter.title}</strong>
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
