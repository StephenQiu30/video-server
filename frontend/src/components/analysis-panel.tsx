'use client';

import { ArrowClockwise, Robot, ShieldCheck } from '@phosphor-icons/react';
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
import { Field, FieldLabel } from '@/components/ui/field';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Spinner } from '@/components/ui/spinner';
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
  const [profile, setProfile] = useState<AnalysisProfile>('visual-shot-v1');
  const [language, setLanguage] = useState<OutputLanguage>('zh-CN');

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
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] lg:items-end">
          <AnalysisSelect
            id="analysis-profile"
            label="分析模板"
            onChange={(value) => setProfile(value as AnalysisProfile)}
            options={[['visual-shot-v1', '视觉分镜分析']]}
            value={profile}
          />
          <AnalysisSelect
            id="analysis-language"
            label="输出语言"
            onChange={(value) => setLanguage(value as OutputLanguage)}
            options={[
              ['zh-CN', '简体中文'],
              ['en-US', 'English'],
            ]}
            value={language}
          />
          <Button
            className="w-full lg:w-auto"
            disabled={state.action === 'start'}
            onClick={() => state.start({ profile, output_language: language })}
            size="lg"
          >
            {state.action === 'start' ? <Spinner aria-hidden /> : null}
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
  id,
  label,
  onChange,
  options,
  value,
}: {
  id: string;
  label: string;
  onChange: (value: string) => void;
  options: [string, string][];
  value: string;
}) {
  return (
    <Field>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Select onValueChange={onChange} value={value}>
        <SelectTrigger className="w-full" id={id}>
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
    </Field>
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
      <p className="mt-8 flex items-center gap-2 text-sm text-muted-foreground">
        <ShieldCheck className="text-success" />
        分析结果经连续时间轴与分镜证据校验；模型查看的抽帧会发送到所选云端服务。
      </p>
    </div>
  );
}
