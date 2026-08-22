'use client';

import { ArrowClockwise, DownloadSimple, Robot } from '@phosphor-icons/react';
import AnalysisArticleResultView from '@/components/analysis/analysis-article-result-view';
import AnalysisConfigurator from '@/components/analysis/analysis-configurator';
import AnalysisDeleteDialog from '@/components/analysis/analysis-delete-dialog';
import {
  stageLabels,
  statusLabels,
} from '@/components/analysis/analysis-panel-model';
import AnalysisResultView from '@/components/analysis/analysis-result-view';
import AnalysisStorageNotice from '@/components/analysis/analysis-storage-notice';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import { useAnalysisJob } from '@/hooks/useAnalysisJob';
import { localizedErrorMessage } from '@/lib/error-messages';
import { analysisMarkdownUrl, analysisReportUrl } from '@/services/analysis';
import type { AnalysisJob } from '@/types/video';

export default function AnalysisPanel({
  downloadId,
  pollIntervalMs = 1500,
}: {
  downloadId: string;
  pollIntervalMs?: number;
}) {
  const state = useAnalysisJob(downloadId, pollIntervalMs);

  if (
    state.job?.status === 'succeeded' &&
    (state.job.result?.kind === 'video_visual_analysis' ||
      state.job.result?.kind === 'video_article')
  ) {
    const formats = new Set(
      state.job.report?.status === 'available'
        ? state.job.report.artifacts.map((artifact) => artifact.format)
        : [],
    );
    const reportAvailable = formats.has('markdown') && formats.has('docx');
    return (
      <section
        aria-label="AI 智能分析"
        className="mt-14 border-t py-12 sm:mt-16 sm:py-16"
      >
        <div className="flex flex-col gap-6">
          <div className="min-w-0 w-full">
            <h2 className="w-full text-[32px] font-medium leading-[1.05] tracking-[-0.045em] sm:text-[44px]">
              {state.job.result.title}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="success">已完成</Badge>
            <span className="text-sm text-muted-foreground tabular-nums">
              第 {state.job.run_no} 次执行
            </span>
            {reportAvailable ? (
              <>
                <Button asChild variant="outline">
                  <a
                    download={`analysis-report-${state.job.id}.md`}
                    href={analysisMarkdownUrl(state.job.id)}
                  >
                    <DownloadSimple />
                    导出 Markdown
                  </a>
                </Button>
                <Button asChild>
                  <a
                    download={`analysis-report-${state.job.id}.docx`}
                    href={analysisReportUrl(state.job.id)}
                  >
                    <DownloadSimple />
                    导出 DOCX
                  </a>
                </Button>
              </>
            ) : null}
            <Button
              disabled={state.action === 'retry'}
              onClick={() => void state.retry()}
              variant="outline"
            >
              <ArrowClockwise />
              {state.action === 'retry' ? '正在重新分析' : '重新分析'}
            </Button>
            <AnalysisDeleteDialog
              busy={state.action === 'delete'}
              onDelete={state.remove}
            />
          </div>
        </div>
        {!reportAvailable ? (
          <Alert className="mt-8" variant="destructive">
            <AlertTitle>报告已清理或暂时不可用</AlertTitle>
            <AlertDescription>
              分析结果仍可查看，但报告文件已被清理或暂时不可读取。你可以重新分析以生成新报告。
            </AlertDescription>
          </Alert>
        ) : null}
        <div className="mt-5">
          <AnalysisStorageNotice />
        </div>
        {state.job.result.kind === 'video_article' ? (
          <AnalysisArticleResultView
            reportMarkdown={state.job.report_markdown}
            result={state.job.result}
          />
        ) : (
          <AnalysisResultView
            reportMarkdown={state.job.report_markdown}
            result={state.job.result}
          />
        )}
      </section>
    );
  }

  return (
    <section
      aria-labelledby="analysis-title"
      className="mt-14 border-t py-12 sm:mt-16 sm:py-16"
    >
      <div className="flex items-start justify-between gap-6">
        <div className="max-w-3xl">
          <h2
            className="text-[32px] font-medium leading-none tracking-[-0.045em] sm:text-[44px]"
            id="analysis-title"
          >
            AI 智能分析
          </h2>
          <p className="mt-4 max-w-2xl leading-7 text-muted-foreground">
            由 AI 观察视频画面，生成连续分镜、视觉高光、资产目录，或将视频整理成文章。
          </p>
        </div>
      </div>

      {state.error ? (
        <Alert className="mt-6" variant="destructive">
          <AlertTitle>操作未完成</AlertTitle>
          <AlertDescription>{state.error}</AlertDescription>
        </Alert>
      ) : null}

      {!state.job ? (
        <AnalysisConfigurator
          busy={state.action === 'start'}
          onStart={state.start}
        />
      ) : (
        <AnalysisJobState job={state.job} state={state} />
      )}
    </section>
  );
}

function AnalysisJobState({
  job,
  state,
}: {
  job: AnalysisJob;
  state: ReturnType<typeof useAnalysisJob>;
}) {
  const cancellable = ['queued', 'running', 'retry_wait'].includes(job.status);
  return (
    <div className="mt-10 w-full">
      <div className="flex justify-between gap-4 text-sm font-medium">
        <span>{statusLabels[job.status]}</span>
        <span className="tabular-nums">{job.progress}%</span>
      </div>
      <Progress
        aria-label={`分析进度 ${job.progress}%`}
        className="mt-3"
        value={job.progress}
      />
      <p className="mt-3 text-sm text-muted-foreground">
        第 {job.run_no} 次执行 · 当前阶段：
        {job.stage ? stageLabels[job.stage] : '等待调度'} ·{' '}
        {job.attempt > 0
          ? `本次第 ${job.attempt} 个技术尝试`
          : '尚未开始技术尝试'}
      </p>
      <div className="mt-2">
        <AnalysisStorageNotice />
      </div>
      {job.status === 'failed' ? (
        <Alert className="mt-6" variant="destructive">
          <AlertTitle>分析失败</AlertTitle>
          <AlertDescription>
            {localizedErrorMessage(job.error_code) ??
              'AI 分析未能完成，请稍后重试。'}
          </AlertDescription>
        </Alert>
      ) : null}
      <p aria-live="polite" className="mt-2 text-xs text-muted-foreground">
        {state.socketStatus === 'connected'
          ? '实时状态已连接'
          : state.socketStatus === 'degraded'
            ? '实时连接中断，正在低频恢复'
            : '正在连接实时状态'}
      </p>
      <div className="mt-7 flex flex-wrap gap-3">
        {cancellable ? (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button disabled={state.action === 'cancel'} variant="outline">
                {state.action === 'cancel' ? <Spinner aria-hidden /> : null}
                取消分析
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent size="sm">
              <AlertDialogHeader>
                <AlertDialogMedia>
                  <Robot aria-hidden />
                </AlertDialogMedia>
                <AlertDialogTitle>取消当前分析任务？</AlertDialogTitle>
                <AlertDialogDescription>
                  确认后将停止当前分析。你之后仍可重新发起分析任务。
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>继续分析</AlertDialogCancel>
                <AlertDialogAction variant="destructive" onClick={state.cancel}>
                  确认取消分析
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ) : null}
        {['failed', 'cancelled'].includes(job.status) ? (
          <Button
            disabled={state.action === 'retry'}
            onClick={() => void state.retry()}
          >
            {state.action === 'retry' ? <Spinner aria-hidden /> : null}
            {state.action === 'retry' ? '正在重试' : '重试分析'}
          </Button>
        ) : null}
        <AnalysisDeleteDialog
          busy={state.action === 'delete'}
          onDelete={state.remove}
        />
      </div>
      <p className="mt-8 text-sm text-muted-foreground">
        分析结果会经过连续时间轴、严格结构与分镜证据校验。
      </p>
      {job.result?.kind === 'video_visual_analysis' ||
      job.result?.kind === 'video_article' ? (
        <div className="mt-10 border-t pt-10">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="neutral">
              {job.report?.status === 'publishing'
                ? '新报告发布中'
                : job.report?.status === 'publish_failed'
                  ? '报告发布失败，等待恢复'
                  : '上一版本报告'}
            </Badge>
            {job.current_report_id ? (
              <>
                <Button asChild size="sm" variant="outline">
                  <a href={analysisMarkdownUrl(job.id)}>下载上一版 Markdown</a>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <a href={analysisReportUrl(job.id)}>下载上一版 DOCX</a>
                </Button>
              </>
            ) : null}
          </div>
          {job.result.kind === 'video_article' ? (
            <AnalysisArticleResultView
              reportMarkdown={job.report_markdown}
              result={job.result}
            />
          ) : (
            <AnalysisResultView
              reportMarkdown={job.report_markdown}
              result={job.result}
            />
          )}
        </div>
      ) : null}
    </div>
  );
}
