'use client';

import {
  ArrowClockwise,
  Robot,
  ShieldCheck,
  SpinnerGap,
} from '@phosphor-icons/react';
import { useState } from 'react';
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

export default function AnalysisPanel({
  downloadId,
  pollIntervalMs = 1500,
}: {
  downloadId: string;
  pollIntervalMs?: number;
}) {
  const state = useAnalysisJob(downloadId, pollIntervalMs);
  const [profile, setProfile] = useState<AnalysisProfile>('standard-v1');
  const [language, setLanguage] = useState<OutputLanguage>('zh-CN');

  if (state.job?.status === 'succeeded' && state.job.result) {
    return (
      <section aria-label="AI 智能分析" className="border-b py-10">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <h2 className="text-3xl font-semibold tracking-[-0.035em]">
              {state.job.result.title}
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="success">分析已完成</Badge>
            <Button onClick={state.restart} variant="outline">
              <ArrowClockwise />
              重新分析
            </Button>
          </div>
        </div>
        <AnalysisResultView result={state.job.result} />
      </section>
    );
  }

  return (
    <section aria-labelledby="analysis-title" className="border-b py-10">
      <div className="flex items-start justify-between gap-5">
        <div>
          <h2
            className="text-3xl font-semibold tracking-[-0.035em]"
            id="analysis-title"
          >
            AI 智能分析
          </h2>
          <p className="mt-3 text-muted-foreground">
            生成摘要、关键观点、章节和思维导图。
          </p>
        </div>
        <Robot aria-hidden className="text-muted-foreground" size={28} />
      </div>

      {state.error ? (
        <Alert className="mt-6" variant="destructive">
          <AlertTitle>操作未完成</AlertTitle>
          <AlertDescription>{state.error}</AlertDescription>
        </Alert>
      ) : null}

      {!state.job ? (
        <div className="mt-8 grid gap-5 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
          <AnalysisSelect
            label="分析模板"
            onChange={(value) => setProfile(value as AnalysisProfile)}
            options={[['standard-v1', '标准分析']]}
            value={profile}
          />
          <AnalysisSelect
            label="输出语言"
            onChange={(value) => setLanguage(value as OutputLanguage)}
            options={[
              ['zh-CN', '简体中文'],
              ['en-US', 'English'],
            ]}
            value={language}
          />
          <Button
            disabled={state.action === 'start'}
            onClick={() => state.start({ profile, output_language: language })}
            size="lg"
          >
            {state.action === 'start' ? (
              <SpinnerGap className="animate-spin" />
            ) : null}
            开始 AI 分析
          </Button>
        </div>
      ) : (
        <AnalysisJobState job={state.job} state={state} />
      )}
    </section>
  );
}

function AnalysisSelect({
  label,
  onChange,
  options,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  options: [string, string][];
  value: string;
}) {
  return (
    <div className="grid gap-2 text-sm font-medium">
      <span>{label}</span>
      <Select onValueChange={onChange} value={value}>
        <SelectTrigger aria-label={label}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map(([option, name]) => (
            <SelectItem key={option} value={option}>
              {name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
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
  const cancellable = ['queued', 'running', 'retry_wait'].includes(job.status);
  return (
    <div className="mt-8 max-w-2xl">
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
      <div className="mt-6 flex gap-3">
        {cancellable ? (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button disabled={state.action === 'cancel'} variant="outline">
                {state.action === 'cancel' ? (
                  <SpinnerGap className="animate-spin" />
                ) : null}
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
      <p className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
        <ShieldCheck className="text-success" />
        分析结果经证据校验，观点均来自视频转录内容。
      </p>
    </div>
  );
}
