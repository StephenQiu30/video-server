import { ArrowClockwise, DownloadSimple } from '@phosphor-icons/react';

import AnalysisDeleteDialog from '@/components/analysis-delete-dialog';
import AnalysisRetryWindow from '@/components/analysis-retry-window';
import { ScreenplayResultView } from '@/components/screenplay-result-view';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { analysisMarkdownUrl, analysisReportUrl } from '@/services/analysis';
import type { AnalysisJob } from '@/types/video';

export function ScreenplayCompletedAnalysis({
  action,
  job,
  onDelete,
  onRetry,
}: {
  action: string | null;
  job: AnalysisJob;
  onDelete: () => Promise<void>;
  onRetry: () => Promise<void>;
}) {
  if (
    !job.result ||
    !['screenplay_analysis', 'screenplay_rewrite'].includes(job.result.kind)
  ) {
    return null;
  }
  const formats = new Set(
    job.report?.status === 'available'
      ? job.report.artifacts.map((artifact) => artifact.format)
      : [],
  );
  const reportAvailable = formats.has('markdown') && formats.has('docx');
  const title =
    job.result.kind === 'screenplay_analysis'
      ? job.result.title
      : '剧本改写已完成';
  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="max-w-4xl">
          <h2
            className="text-[32px] font-medium leading-[1.05] tracking-[-0.045em] sm:text-[44px]"
            id="screenplay-analysis-title"
          >
            {title}
          </h2>
          <p className="mt-3 text-sm text-muted-foreground">
            {job.result.kind === 'screenplay_rewrite'
              ? 'AI 改写 · 完整正文请在下方查看或导出'
              : 'AI 剧本分析 · 所有结论均绑定源场景证据'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="success">已完成</Badge>
          <span className="text-sm text-muted-foreground tabular-nums">
            第 {job.run_no} 次执行
          </span>
          {reportAvailable ? (
            <>
              <Button asChild variant="outline">
                <a
                  download={`screenplay-analysis-${job.id}.md`}
                  href={analysisMarkdownUrl(job.id)}
                >
                  <DownloadSimple aria-hidden />
                  导出 Markdown
                </a>
              </Button>
              <Button asChild>
                <a
                  download={`screenplay-analysis-${job.id}.docx`}
                  href={analysisReportUrl(job.id)}
                >
                  <DownloadSimple aria-hidden />
                  导出 DOCX
                </a>
              </Button>
            </>
          ) : null}
          <Button
            disabled={action === 'retry'}
            onClick={() => void onRetry()}
            variant="outline"
          >
            <ArrowClockwise aria-hidden />
            {action === 'retry' ? '正在重新执行' : '重新执行'}
          </Button>
          <AnalysisDeleteDialog
            busy={action === 'delete'}
            onDelete={onDelete}
          />
        </div>
      </div>
      {!reportAvailable ? (
        <Alert className="mt-8" variant="destructive">
          <AlertTitle>报告已过期或暂时不可用</AlertTitle>
          <AlertDescription>
            结构化结果仍可查看；重新执行后会生成新的 Markdown 和 DOCX。
          </AlertDescription>
        </Alert>
      ) : null}
      <div className="mt-5">
        <AnalysisRetryWindow job={job} />
      </div>
      <ScreenplayResultView
        reportMarkdown={job.report_markdown}
        result={job.result}
      />
    </>
  );
}
