import ScreenplayAnalysisResultView from '@/components/screenplay/screenplay-analysis-result-view';
import ScreenplayRewriteResultView from '@/components/screenplay/screenplay-rewrite-result-view';

export function ScreenplayResultView({
  reportMarkdown,
  result,
}: {
  reportMarkdown?: string | null;
  result: NonNullable<API.AnalysisResponse['result']>;
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
