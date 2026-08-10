'use client';

import { ArrowClockwise, DownloadSimple, Robot } from '@phosphor-icons/react';
import AnalysisConfigurator from '@/components/analysis-configurator';
import { stageLabels, statusLabels } from '@/components/analysis-panel-model';
import AnalysisResultView from '@/components/analysis-result-view';
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

  if (state.job?.status === 'succeeded' && state.job.result) {
    return (
      <section
        aria-label="AI 智能分析"
        className="mt-14 border-t py-12 sm:mt-16 sm:py-16"
      >
        <p className="eyebrow text-muted-foreground">03 / 内容分析</p>
        <div className="mt-6 flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-4xl">
            <h2 className="text-[32px] font-medium leading-[1.05] tracking-[-0.045em] sm:text-[44px]">
              {state.job.result.title}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="success">分析已完成</Badge>
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
            <Button onClick={state.restart} variant="outline">
              <ArrowClockwise />
              重新分析
            </Button>
          </div>
        </div>
        <AnalysisResultView
          reportMarkdown={state.job.report_markdown}
          result={state.job.result}
        />
      </section>
    );
  }

  return (
    <section
      aria-labelledby="analysis-title"
      className="mt-14 border-t py-12 sm:mt-16 sm:py-16"
    >
      <p className="eyebrow text-muted-foreground">03 / 内容分析</p>
      <div className="mt-6 flex items-start justify-between gap-6">
        <div className="max-w-3xl">
          <h2
            className="text-[32px] font-medium leading-none tracking-[-0.045em] sm:text-[44px]"
            id="analysis-title"
          >
            AI 智能分析
          </h2>
          <p className="mt-4 max-w-2xl leading-7 text-muted-foreground">
            由 AI 观察视频画面，生成连续分镜、视觉高光和资产目录。
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
    <div className="mt-10 max-w-3xl">
      <div className="flex justify-between gap-4 text-sm font-medium">
        <span>{statusLabels[job.status]}</span>
        <span className="font-mono">{job.progress}%</span>
      </div>
      <Progress
        aria-label={`分析进度 ${job.progress}%`}
        className="mt-3"
        value={job.progress}
      />
      <p className="mt-3 text-sm text-muted-foreground">
        当前阶段：{job.stage ? stageLabels[job.stage] : '等待调度'} · 第{' '}
        {job.attempt} 次尝试
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
          <Button onClick={state.restart}>重新分析</Button>
        ) : null}
      </div>
      <p className="mt-8 text-sm text-muted-foreground">
        分析结果会经过连续时间轴、严格结构与分镜证据校验。
      </p>
    </div>
  );
}
