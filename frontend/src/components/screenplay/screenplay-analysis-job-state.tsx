import { Robot } from '@phosphor-icons/react';

import AnalysisDeleteDialog from '@/components/analysis/analysis-delete-dialog';
import {
  screenplayAnalysisErrorMessage,
  stageLabels,
  statusLabels,
} from '@/components/analysis/analysis-panel-model';
import AnalysisStorageNotice from '@/components/analysis/analysis-storage-notice';
import { ScreenplayResultView } from '@/components/screenplay/screenplay-result-view';
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
import type { useAnalysisJob } from '@/hooks/useAnalysisJob';
import { localizedErrorMessage } from '@/lib/error-messages';
import type { AnalysisJob } from '@/types/video';

export function ScreenplayAnalysisJobState({
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
        aria-label={`剧本任务进度 ${job.progress}%`}
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
          <AlertTitle>剧本任务失败</AlertTitle>
          <AlertDescription>
            {screenplayAnalysisErrorMessage(job.error_code) ??
              localizedErrorMessage(job.error_code) ??
              '剧本分析或改写未能完成，请稍后重试。'}
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
        {cancellable ? <CancelControl state={state} /> : null}
        {['failed', 'cancelled'].includes(job.status) ? (
          <Button
            disabled={state.action === 'retry'}
            onClick={() => void state.retry()}
          >
            {state.action === 'retry' ? <Spinner aria-hidden /> : null}
            {state.action === 'retry' ? '正在重试' : '重试任务'}
          </Button>
        ) : null}
        <AnalysisDeleteDialog
          busy={state.action === 'delete'}
          onDelete={state.remove}
        />
      </div>
      {job.result && job.result.kind !== 'video_visual_analysis' ? (
        <div className="mt-10 pt-10">
          <Badge variant="neutral">上一版本结果</Badge>
          <ScreenplayResultView
            reportMarkdown={job.report_markdown}
            result={job.result}
          />
        </div>
      ) : null}
    </div>
  );
}

function CancelControl({
  state,
}: {
  state: ReturnType<typeof useAnalysisJob>;
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button disabled={state.action === 'cancel'} variant="outline">
          {state.action === 'cancel' ? <Spinner aria-hidden /> : null}
          取消任务
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent size="sm">
        <AlertDialogHeader>
          <AlertDialogMedia>
            <Robot aria-hidden />
          </AlertDialogMedia>
          <AlertDialogTitle>取消当前剧本任务？</AlertDialogTitle>
          <AlertDialogDescription>
            确认后将停止当前分析或改写。规范化剧本文档不会被删除。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>继续执行</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={state.cancel}>
            确认取消任务
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
