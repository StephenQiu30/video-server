'use client';

import AnalysisConfigurator from '@/components/analysis/analysis-configurator';
import { useAnalysisJob } from '@/components/analysis/use-analysis-job';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { ScreenplayAnalysisJobState } from '@/components/screenplay/screenplay-analysis-job-state';
import { ScreenplayCompletedAnalysis } from '@/components/screenplay/screenplay-completed-analysis';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';

export default function ScreenplayAnalysisPanel({
  documentId,
  pollIntervalMs = 1500,
}: {
  documentId: string;
  pollIntervalMs?: number;
}) {
  const state = useAnalysisJob(documentId, pollIntervalMs, 'screenplay');

  if (state.loading && state.action !== 'start') {
    return (
      <div className="py-12" role="status">
        <Spinner aria-hidden className="mr-2 inline" />
        正在读取分析记录
      </div>
    );
  }
  if (state.errorKind === 'load' && state.error) {
    return (
      <PageErrorNotice
        compact
        title="暂时无法读取分析记录"
        message={state.error}
        onRetry={() => void state.retryPoll()}
      />
    );
  }
  const succeeded =
    state.job?.status === 'succeeded' &&
    state.job.result &&
    state.job.result.kind !== 'video_visual_analysis';

  return (
    <div className="mt-14 py-12 sm:mt-16 sm:py-16">
      {succeeded && state.job ? (
        <>
          {state.error ? (
            <FeedbackNotice
              action={
                state.errorKind === 'sync' ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void state.retryPoll()}
                  >
                    恢复同步
                  </Button>
                ) : undefined
              }
              className="mb-8"
              description={state.error}
              title="操作未完成"
              tone="error"
            />
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
            <FeedbackNotice
              action={
                state.errorKind === 'sync' ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void state.retryPoll()}
                  >
                    恢复同步
                  </Button>
                ) : undefined
              }
              className="mt-6"
              description={state.error}
              title="操作未完成"
              tone="error"
            />
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
    </div>
  );
}
