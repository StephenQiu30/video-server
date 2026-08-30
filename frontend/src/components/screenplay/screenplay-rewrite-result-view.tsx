'use client';

import AnalysisReportPreview from '@/components/analysis/analysis-report-preview';
import {
  languageLabel,
  Metric,
  ResultTab,
} from '@/components/screenplay/screenplay-result-primitives';
import { Tabs, TabsContent, TabsList } from '@/components/ui/tabs';
import type { ScreenplayRewriteResult } from '@/types/video';

const categoryLabels: Record<string, string> = {
  character: '人物',
  honorific: '称谓',
  location: '地点',
  other: '其他',
  term: '术语',
  title: '标题',
};

export default function ScreenplayRewriteResultView({
  reportMarkdown,
  result,
}: {
  reportMarkdown?: string | null;
  result: ScreenplayRewriteResult;
}) {
  return (
    <Tabs className="mt-10 gap-0" defaultValue="summary">
      <div className="grid gap-5 py-4 sm:grid-cols-3">
        <Metric label="源场景" value={`${result.source_scene_count}`} />
        <Metric label="输出场景" value={`${result.output_scene_count}`} />
        <Metric
          label="语言"
          value={`${languageLabel(result.source_language)} → ${languageLabel(result.target_language)}`}
        />
      </div>
      <div className="mt-10 overflow-x-auto">
        <TabsList
          className="h-auto w-max gap-7 rounded-none p-0"
          variant="line"
        >
          <ResultTab value="summary">术语与摘要</ResultTab>
          {reportMarkdown ? (
            <ResultTab value="report">改写正文</ResultTab>
          ) : null}
        </TabsList>
      </div>
      <TabsContent className="pt-7" value="summary">
        <section aria-labelledby="rewrite-glossary-title">
          <h3
            className="text-xl font-medium tracking-[-0.02em]"
            id="rewrite-glossary-title"
          >
            统一术语
          </h3>
          {result.glossary.length ? (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[560px] border-collapse text-left text-sm">
                <caption className="sr-only">剧本改写统一术语表</caption>
                <thead>
                  <tr className="text-muted-foreground">
                    <th className="py-3 pr-5 font-normal">原文</th>
                    <th className="py-3 pr-5 font-normal">统一写法</th>
                    <th className="py-3 font-normal">类别</th>
                  </tr>
                </thead>
                <tbody>
                  {result.glossary.map((term) => (
                    <tr key={`${term.category}:${term.source}`}>
                      <td className="py-4 pr-5 font-medium">{term.source}</td>
                      <td className="py-4 pr-5">{term.target}</td>
                      <td className="py-4 text-muted-foreground">
                        {categoryLabels[term.category] ?? term.category}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-4 py-7 text-muted-foreground">
              本次改写没有需要单独统一的术语。
            </p>
          )}
        </section>
        <section
          className="mt-10 max-w-4xl"
          aria-labelledby="rewrite-summary-title"
        >
          <h3
            className="text-xl font-medium tracking-[-0.02em]"
            id="rewrite-summary-title"
          >
            修改摘要
          </h3>
          <ul className="mt-4 list-disc space-y-2 pl-5 leading-7 text-muted-foreground">
            {result.change_summary.map((summary) => (
              <li key={summary}>{summary}</li>
            ))}
          </ul>
        </section>
      </TabsContent>
      {reportMarkdown ? (
        <TabsContent className="pt-7" value="report">
          <p className="mb-6 max-w-3xl text-sm leading-6 text-muted-foreground">
            以下正文由受限 AI 按源场景顺序确定性合并，仅用于改写与本地化参考。
          </p>
          <AnalysisReportPreview markdown={reportMarkdown} />
        </TabsContent>
      ) : null}
    </Tabs>
  );
}
