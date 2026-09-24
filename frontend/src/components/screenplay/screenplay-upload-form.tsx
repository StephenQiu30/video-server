'use client';

import { FileText, UploadSimple, X } from '@phosphor-icons/react';
import { type FormEvent, useRef } from 'react';

import {
  IntakeControlRow,
  IntakePickerButton,
  IntakeSubmitButton,
} from '@/components/intake/intake-control-row';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Form } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import { formatFileSize } from '@/lib/format';
import type { ImportPhase } from '@/lib/upload/import-lifecycle';

const phaseLabels: Record<ImportPhase, string> = {
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
  phase: ImportPhase;
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
    <Form className={workspace ? undefined : 'mt-2'} onSubmit={submit}>
      <IntakeControlRow className={workspace ? undefined : 'block'}>
        <IntakePickerButton
          aria-describedby={error ? 'screenplay-upload-error' : undefined}
          aria-invalid={fileInvalid || undefined}
          className={workspace ? undefined : 'h-control-upload w-full'}
          disabled={busy}
          onClick={() => inputRef.current?.click()}
        >
          <FileText
            aria-hidden
            className="size-5 shrink-0 text-muted-foreground"
          />
          <span className="min-w-0 flex-1">
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
        </IntakePickerButton>
        <Input
          accept=".docx,.pdf,.txt,.md,.markdown,.fountain"
          aria-label="选择剧本文档文件"
          className="sr-only h-px w-px border-0 p-0"
          disabled={busy}
          onChange={(event) => onFileSelect(event.target.files?.[0] ?? null)}
          onClick={(event) => {
            event.currentTarget.value = '';
          }}
          ref={inputRef}
          type="file"
        />
        {workspace ? (
          <IntakeSubmitButton disabled={busy}>
            {busy ? (
              <Spinner aria-hidden data-icon="inline-start" />
            ) : (
              <UploadSimple aria-hidden data-icon="inline-start" />
            )}
            {busy ? '处理中…' : '上传剧本'}
          </IntakeSubmitButton>
        ) : null}
      </IntakeControlRow>

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
        <div className="mt-4 py-4">
          <div className="mb-3 flex min-h-control-lg items-center justify-between gap-4">
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
                  <X aria-hidden data-icon="inline-start" />
                  取消上传
                </Button>
              ) : null}
            </div>
          </div>
          <Progress aria-label={phaseLabels[phase]} value={progress} />
        </div>
      ) : null}

      {!workspace ? (
        <Button className="mt-5 w-full" disabled={busy} size="lg" type="submit">
          {busy ? (
            <Spinner aria-hidden data-icon="inline-start" />
          ) : (
            <UploadSimple aria-hidden data-icon="inline-start" />
          )}
          {busy ? '处理中…' : '上传剧本'}
        </Button>
      ) : null}
    </Form>
  );
}
