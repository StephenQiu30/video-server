import ScreenplayAnalysisResultView from '@/components/screenplay-analysis-result-view';
import ScreenplayRewriteResultView from '@/components/screenplay-rewrite-result-view';
import type { AnalysisResult } from '@/types/video';

export function ScreenplayResultView({
  reportMarkdown,
  result,
}: {
  reportMarkdown?: string | null;
  result: AnalysisResult;
}) {
  if (result.kind === 'screenplay_analysis') {
    return (
      <ScreenplayAnalysisResultView
        reportMarkdown={reportMarkdown}
        result={result}
      />
    );
  }
  if (result.kind === 'screenplay_rewrite') {
    return (
      <ScreenplayRewriteResultView
        reportMarkdown={reportMarkdown}
        result={result}
      />
    );
  }
  return null;
}
