'use client';

import AnalysisReportPreview from '@/components/analysis/analysis-report-preview';
import {
  Detail,
  EvidenceIds,
  EvidenceList,
  languageLabel,
  Metric,
  ResultTab,
} from '@/components/screenplay/screenplay-result-primitives';
import { Item, ItemGroup } from '@/components/ui/item';
import { Tabs, TabsContent, TabsList } from '@/components/ui/tabs';
import type { ScreenplayAnalysisResult } from '@/types/video';

export default function ScreenplayAnalysisResultView({
  reportMarkdown,
  result,
}: {
  reportMarkdown?: string | null;
  result: ScreenplayAnalysisResult;
}) {
  return (
    <Tabs className="mt-10 gap-0" defaultValue="overview">
      <div className="grid gap-5 py-4 sm:grid-cols-3">
        <Metric label="逐场景覆盖" value={`${result.scenes.length}`} />
        <Metric label="主要人物" value={`${result.characters.length}`} />
        <Metric label="输出语言" value={languageLabel(result.language)} />
      </div>
      <div className="mt-9 max-w-none">
        <h2 className="text-xl font-medium tracking-[-0.02em]">故事概览</h2>
        <dl className="mt-5 grid gap-5">
          <Detail label="一句话梗概">
            <span className="text-lg leading-8">{result.logline}</span>
          </Detail>
          <Detail label="故事梗概">
            <span className="leading-7 text-muted-foreground">
              {result.synopsis}
            </span>
          </Detail>
        </dl>
      </div>
      <ResultTabs reportMarkdown={reportMarkdown} />
      <TabsContent className="pt-7" value="overview">
        <section className="max-w-none">
          <h3 className="text-xl font-medium tracking-[-0.02em]">结构与节奏</h3>
          <p className="mt-3 leading-7 text-muted-foreground">
            {result.structure.pacing_summary}
          </p>
        </section>
        <EvidenceList
          heading="幕结构"
          items={result.structure.acts}
          className="mt-8"
        />
        <EvidenceList
          heading="关键转折"
          items={result.structure.turning_points}
          className="mt-8"
        />
      </TabsContent>
      <TabsContent className="pt-7" value="characters">
        {result.characters.length ? (
          <ItemGroup asChild className="gap-2">
            <ul>
              {result.characters.map((character) => (
                <Item
                  asChild
                  className="block rounded-md border-0 px-0 py-6"
                  key={character.id}
                >
                  <li>
                    <strong className="font-medium">{character.name}</strong>
                    <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
                      <Detail label="目标">{character.goal}</Detail>
                      <Detail label="冲突">{character.conflict}</Detail>
                      <Detail label="人物弧">{character.arc}</Detail>
                    </dl>
                    <EvidenceIds ids={character.evidence_scene_ids} />
                  </li>
                </Item>
              ))}
            </ul>
          </ItemGroup>
        ) : (
          <p className="py-7 text-muted-foreground">
            本次结果没有独立人物条目。
          </p>
        )}
      </TabsContent>
      <TabsContent className="pt-7" value="scenes">
        <ItemGroup asChild className="gap-2">
          <ol>
            {result.scenes.map((scene, index) => (
              <Item
                asChild
                className="grid gap-4 rounded-md border-0 px-0 py-6 sm:grid-cols-[88px_minmax(0,1fr)]"
                key={scene.id}
              >
                <li>
                  <span className="text-sm text-muted-foreground tabular-nums">
                    场景 {index + 1}
                  </span>
                  <div>
                    <strong className="font-medium">{scene.purpose}</strong>
                    <p className="mt-2 leading-7 text-muted-foreground">
                      {scene.conflict} · {scene.turn}
                    </p>
                    <p className="mt-3 text-sm">节奏：{scene.pacing}</p>
                    {scene.findings.length ? (
                      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                        {scene.findings.map((finding) => (
                          <li key={finding}>{finding}</li>
                        ))}
                      </ul>
                    ) : null}
                    <EvidenceIds ids={[scene.source_scene_id]} />
                  </div>
                </li>
              </Item>
            ))}
          </ol>
        </ItemGroup>
      </TabsContent>
      <TabsContent className="pt-7" value="dialogue">
        <EvidenceList heading="对白发现" items={result.dialogue_findings} />
      </TabsContent>
      <TabsContent className="pt-7" value="revisions">
        <EvidenceList heading="优点" items={result.strengths} />
        <EvidenceList
          heading="优先修改"
          items={result.priority_revisions}
          className="mt-10"
        />
      </TabsContent>
      {reportMarkdown ? (
        <TabsContent className="pt-7" value="report">
          <AnalysisReportPreview markdown={reportMarkdown} />
        </TabsContent>
      ) : null}
    </Tabs>
  );
}

function ResultTabs({ reportMarkdown }: { reportMarkdown?: string | null }) {
  return (
    <div className="mt-10 overflow-x-auto">
      <TabsList className="h-auto w-max gap-7 rounded-none p-0" variant="line">
        <ResultTab value="overview">结构</ResultTab>
        <ResultTab value="characters">人物</ResultTab>
        <ResultTab value="scenes">场景</ResultTab>
        <ResultTab value="dialogue">对白</ResultTab>
        <ResultTab value="revisions">修改建议</ResultTab>
        {reportMarkdown ? <ResultTab value="report">完整报告</ResultTab> : null}
      </TabsList>
    </div>
  );
}
