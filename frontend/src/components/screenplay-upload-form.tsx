'use client';

import { FileText, UploadSimple, X } from '@phosphor-icons/react';
import { type FormEvent, useRef } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import type { DocumentImportPhase } from '@/services/document-import';
import { formatFileSize } from '@/utils/format-file-size';

const phaseLabels: Record<DocumentImportPhase, string> = {
  idle: '准备上传',
  hashing: '正在计算文件校验值',
  creating: '正在创建剧本文档',
  uploading: '正在分片上传',
  completing: '正在提交解析验证',
  cancelling: '正在取消上传',
};

type ScreenplayUploadFormProps = {
  busy: boolean;
  canCancel: boolean;
  error: string | null;
  file: File | null;
  fileInvalid: boolean;
  layout?: 'dialog' | 'workspace';
  onCancel: () => void;
  onFileSelect: (file: File | null) => void;
  onStart: () => void;
  phase: DocumentImportPhase;
  progress: number;
};

export function ScreenplayUploadForm({
  busy,
  canCancel,
  error,
  file,
  fileInvalid,
  layout = 'dialog',
  onCancel,
  onFileSelect,
  onStart,
  phase,
  progress,
}: ScreenplayUploadFormProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const workspace = layout === 'workspace';
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onStart();
  };

  return (
    <form className={workspace ? undefined : 'mt-2'} onSubmit={submit}>
      <div
        className={
          workspace
            ? 'grid gap-2 sm:grid-cols-[minmax(0,1fr)_148px]'
            : undefined
        }
      >
        <Button
          aria-describedby={error ? 'screenplay-upload-error' : undefined}
          aria-invalid={fileInvalid || undefined}
          className={
            workspace
              ? 'h-16 min-w-0 justify-start px-4 text-left font-normal sm:h-[68px]'
              : 'h-20 w-full justify-start px-4 text-left font-normal'
          }
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          type="button"
          variant="secondary"
        >
          <FileText aria-hidden className="size-5 text-muted-foreground" />
          <span className="min-w-0">
            <span
              className="block line-clamp-2 break-words text-[15px] leading-5 font-medium"
              title={file?.name}
            >
              {file?.name ?? '选择剧本文档'}
            </span>
            <span className="mt-0.5 block truncate text-xs text-muted-foreground">
              {file
                ? formatFileSize(file.size)
                : 'DOCX、PDF、TXT、Markdown 或 Fountain'}
            </span>
          </span>
        </Button>
        <input
          accept=".docx,.pdf,.txt,.md,.markdown,.fountain"
          aria-label="选择剧本文档文件"
          className="sr-only"
          disabled={busy}
          onChange={(event) => onFileSelect(event.target.files?.[0] ?? null)}
          onClick={(event) => {
            event.currentTarget.value = '';
          }}
          ref={inputRef}
          type="file"
        />
        {workspace ? (
          <Button
            className="h-16 px-6 text-[15px] sm:h-[68px]"
            disabled={busy}
            type="submit"
          >
            {busy ? <Spinner aria-hidden /> : <UploadSimple aria-hidden />}
            {busy ? '处理中…' : '上传剧本'}
          </Button>
        ) : null}
      </div>

      {error ? (
        <Alert
          className="mt-3"
          id="screenplay-upload-error"
          variant="destructive"
        >
          <AlertTitle>无法上传剧本</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {busy ? (
        <div className="mt-4 border-y py-4">
          <div className="mb-3 flex min-h-11 items-center justify-between gap-4">
            <p aria-live="polite" className="text-sm" role="status">
              {phaseLabels[phase]}
            </p>
            <div className="flex items-center gap-3">
              <span
                aria-hidden
                className="text-xs tabular-nums text-muted-foreground"
              >
                {progress}%
              </span>
              {canCancel ? (
                <Button
                  onClick={onCancel}
                  size="sm"
                  type="button"
                  variant="ghost"
                >
                  <X aria-hidden />
                  取消上传
                </Button>
              ) : null}
            </div>
          </div>
          <Progress aria-label={phaseLabels[phase]} value={progress} />
        </div>
      ) : null}

      {!workspace ? (
        <Button className="mt-5 h-11 w-full" disabled={busy} type="submit">
          {busy ? <Spinner aria-hidden /> : <UploadSimple aria-hidden />}
          {busy ? '处理中…' : '上传剧本'}
        </Button>
      ) : null}
    </form>
  );
}
