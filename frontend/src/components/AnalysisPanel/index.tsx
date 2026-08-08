'use client';

import { ArrowClockwiseIcon, SparkleIcon } from '@phosphor-icons/react';
import { useEffect, useState } from 'react';

import AnalysisResultView from '@/components/AnalysisResultView';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useAnalysisJob } from '@/hooks/useAnalysisJob';
import type {
  AnalysisJob,
  AnalysisProfile,
  OutputLanguage,
} from '@/types/video';
import {
  cancellableAnalysisStatuses,
  stageLabels,
  statusLabels,
} from './status';

type AnalysisPanelProps = {
  downloadId: string;
  onJobChange?: (job: AnalysisJob | null) => void;
  pollIntervalMs?: number;
};

export default function AnalysisPanel({
  downloadId,
  onJobChange,
  pollIntervalMs = 1500,
}: AnalysisPanelProps) {
  const state = useAnalysisJob(downloadId, pollIntervalMs);
  const [profile, setProfile] = useState<AnalysisProfile>('standard-v1');
  const [language, setLanguage] = useState<OutputLanguage>('zh-CN');
  const { action, error, job } = state;

  useEffect(() => onJobChange?.(job), [job, onJobChange]);

  if (job?.status === 'succeeded' && job.result) {
    return (
      <section className="border-t pt-10">
        <div className="mb-7 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs tracking-[0.18em] text-muted-foreground uppercase">
              AI analysis
            </p>
            <h2 className="mt-2 text-2xl font-semibold">{job.result.title}</h2>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="secondary">分析已完成</Badge>
            <Button onClick={state.restart} variant="outline">
              <ArrowClockwiseIcon data-icon="inline-start" />
              重新分析
            </Button>
          </div>
        </div>
        <AnalysisResultView result={job.result} />
      </section>
    );
  }

  return (
    <section className="border-t py-10">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs tracking-[0.18em] text-muted-foreground uppercase">
            AI analysis
          </p>
          <h2 className="mt-2 text-2xl font-semibold">AI 智能分析</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            生成摘要、关键观点、章节和思维导图。
          </p>
        </div>
        <SparkleIcon className="size-6 text-brand" />
      </div>

      {error ? (
        <Alert className="mb-6" variant="destructive">
          <AlertTitle>分析服务暂时不可用</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {!job ? (
        <div className="grid gap-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
          <Field label="分析模板">
            <Select
              value={profile}
              onValueChange={(value) => setProfile(value as AnalysisProfile)}
            >
              <SelectTrigger aria-label="分析模板">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="standard-v1">标准分析</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field label="输出语言">
            <Select
              value={language}
              onValueChange={(value) => setLanguage(value as OutputLanguage)}
            >
              <SelectTrigger aria-label="输出语言">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="zh-CN">简体中文</SelectItem>
                <SelectItem value="en-US">English</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Button
            className="h-9"
            disabled={action === 'start'}
            onClick={() => state.start({ profile, output_language: language })}
          >
            开始 AI 分析
          </Button>
        </div>
      ) : (
        <AnalysisJobState job={job} state={state} />
      )}
    </section>
  );
}

function Field({
  children,
  label,
}: {
  children: React.ReactNode;
  label: string;
}) {
  return (
    <div className="grid gap-2 text-sm font-medium">
      <span>{label}</span>
      {children}
    </div>
  );
}

function AnalysisJobState({
  job,
  state,
}: {
  job: AnalysisJob;
  state: ReturnType<typeof useAnalysisJob>;
}) {
  return (
    <div className="max-w-3xl space-y-5">
      <div className="flex items-center justify-between gap-4">
        <strong>{statusLabels[job.status]}</strong>
        <span className="font-mono text-sm text-muted-foreground">
          {job.progress}%
        </span>
      </div>
      <Progress value={job.progress} />
      <p className="text-sm text-muted-foreground">
        当前阶段：{job.stage ? stageLabels[job.stage] : '等待调度'} · 第{' '}
        {job.attempt} 次尝试
      </p>
      <div className="flex gap-3">
        {cancellableAnalysisStatuses.has(job.status) ? (
          <Button onClick={state.cancel} variant="outline">
            取消分析
          </Button>
        ) : null}
        {job.status === 'failed' || job.status === 'cancelled' ? (
          <Button onClick={state.restart}>重新分析</Button>
        ) : null}
      </div>
    </div>
  );
}
