'use client';

import AnalysisConfigurator from '@/components/analysis/analysis-configurator';
import { ScreenplayAnalysisJobState } from '@/components/screenplay/screenplay-analysis-job-state';
import { ScreenplayCompletedAnalysis } from '@/components/screenplay/screenplay-completed-analysis';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useAnalysisJob } from '@/hooks/useAnalysisJob';

export default function ScreenplayAnalysisPanel({
  documentId,
  pollIntervalMs = 1500,
}: {
  documentId: string;
  pollIntervalMs?: number;
}) {
  const state = useAnalysisJob(documentId, pollIntervalMs, 'screenplay');
  const succeeded =
    state.job?.status === 'succeeded' &&
    state.job.result &&
    state.job.result.kind !== 'video_visual_analysis';

  return (
    <section
      aria-labelledby="screenplay-analysis-title"
      className="mt-14 border-t py-12 sm:mt-16 sm:py-16"
    >
      {succeeded && state.job ? (
        <>
          {state.error ? (
            <Alert className="mb-8" variant="destructive">
              <AlertTitle>操作未完成</AlertTitle>
              <AlertDescription>{state.error}</AlertDescription>
            </Alert>
          ) : null}
          <ScreenplayCompletedAnalysis
            action={state.action}
            job={state.job}
            onDelete={state.remove}
            onRetry={state.retry}
          />
        </>
      ) : (
        <>
          <div className="max-w-3xl">
            <h2
              className="text-[32px] font-medium leading-none tracking-[-0.045em] sm:text-[44px]"
              id="screenplay-analysis-title"
            >
              剧本分析与改写
            </h2>
            <p className="mt-4 max-w-2xl leading-7 text-muted-foreground">
              选择综合分析、结构审阅或中英文改写。任务始终绑定这份规范化剧本，不会修改原文。
            </p>
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
              inputKind="screenplay"
              onStart={state.start}
            />
          ) : (
            <ScreenplayAnalysisJobState job={state.job} state={state} />
          )}
        </>
      )}
    </section>
  );
}
