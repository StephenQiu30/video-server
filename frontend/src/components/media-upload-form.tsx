'use client';

import { FileVideo, UploadSimple, X } from '@phosphor-icons/react';
import { type FormEvent, useRef } from 'react';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import type { MediaImportPhase } from '@/services/media-import';

const phaseLabels: Record<MediaImportPhase, string> = {
  idle: '准备上传',
  hashing: '正在计算文件校验值',
  creating: '正在创建上传任务',
  uploading: '正在分片上传',
  completing: '正在提交服务端验证',
  cancelling: '正在取消上传',
};

export function MediaUploadForm({
  busy,
  canCancel,
  file,
  fileInvalid,
  onCancel,
  onFileSelect,
  onRightsChange,
  onStart,
  phase,
  progress,
  rightsAccepted,
  rightsInvalid,
}: {
  busy: boolean;
  canCancel: boolean;
  file: File | null;
  fileInvalid: boolean;
  onCancel: () => void;
  onFileSelect: (file: File | null) => void;
  onRightsChange: (accepted: boolean) => void;
  onStart: () => void;
  phase: MediaImportPhase;
  progress: number;
  rightsAccepted: boolean;
  rightsInvalid: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onStart();
  };

  return (
    <form onSubmit={submit}>
      <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_148px]">
        <Button
          aria-describedby={
            fileInvalid ? 'download-workspace-error' : undefined
          }
          aria-invalid={fileInvalid || undefined}
          className="h-16 min-w-0 justify-start px-4 text-left font-normal sm:h-[68px]"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          variant="secondary"
        >
          <FileVideo aria-hidden className="size-5 text-muted-foreground" />
          <span className="min-w-0">
            <span className="block truncate text-[15px] font-medium">
              {file?.name ?? '选择本地 MP4 视频'}
            </span>
            <span className="mt-0.5 block truncate text-xs text-muted-foreground">
              {file
                ? formatFileSize(file.size)
                : '文件将直接分片上传到隔离存储'}
            </span>
          </span>
        </Button>
        <input
          accept="video/mp4,.mp4"
          aria-label="选择本地 MP4 视频文件"
          className="sr-only"
          disabled={busy}
          onChange={(event) => onFileSelect(event.target.files?.[0] ?? null)}
          onClick={(event) => {
            event.currentTarget.value = '';
          }}
          ref={inputRef}
          type="file"
        />
        <Button
          className="h-16 px-6 text-[15px] sm:h-[68px]"
          disabled={busy}
          type="submit"
        >
          {busy ? <Spinner aria-hidden /> : <UploadSimple aria-hidden />}
          {busy ? '处理中…' : '上传并验证'}
        </Button>
      </div>

      <div className="mt-4 flex min-h-11 items-start gap-3">
        <Checkbox
          aria-describedby={
            rightsInvalid ? 'download-workspace-error' : undefined
          }
          aria-invalid={rightsInvalid || undefined}
          checked={rightsAccepted}
          disabled={busy}
          id="media-upload-rights"
          onCheckedChange={(checked) => onRightsChange(checked === true)}
        />
        <Label
          className="-mt-1 min-h-11 cursor-pointer items-start py-1 text-sm leading-6 font-normal text-muted-foreground"
          htmlFor="media-upload-rights"
        >
          我确认有权上传并分析此视频；系统会重算哈希并验证
          MP4，原始字节不会被转码或修复。
        </Label>
      </div>

      {busy ? (
        <div className="mt-4 border-y py-4">
          <div className="mb-3 flex min-h-11 items-center justify-between gap-4">
            <p aria-live="polite" className="text-sm" role="status">
              {phaseLabels[phase]}
            </p>
            <div className="flex items-center gap-3">
              <span
                aria-hidden
                className="text-xs text-muted-foreground tabular-nums"
              >
                {progress}%
              </span>
              {canCancel ? (
                <Button onClick={onCancel} size="sm" variant="ghost">
                  <X aria-hidden />
                  取消上传
                </Button>
              ) : null}
            </div>
          </div>
          <Progress aria-label={phaseLabels[phase]} value={progress} />
        </div>
      ) : null}
    </form>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB'];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits: value >= 100 ? 0 : 1,
  }).format(value)} ${units[unit]}`;
}
