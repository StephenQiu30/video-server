'use client';

import { DownloadSimple, X } from '@phosphor-icons/react';
import type { FormEvent, KeyboardEvent } from 'react';
import { IntakeSubmitButton } from '@/components/intake/intake-control-row';
import { Button } from '@/components/ui/button';
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field';
import { Form } from '@/components/ui/form';
import { Spinner } from '@/components/ui/spinner';
import { Textarea } from '@/components/ui/textarea';

export function LinkDownloadForm({
  busy,
  disabled,
  hasResult,
  invalid,
  onInspect,
  onUrlChange,
  url,
}: {
  busy: boolean;
  disabled: boolean;
  hasResult: boolean;
  invalid: boolean;
  onInspect: () => void;
  onUrlChange: (value: string) => void;
  url: string;
}) {
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onInspect();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (
      event.key === 'Enter' &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      onInspect();
    }
  };

  return (
    <Form className="flex flex-col gap-4" onSubmit={submit}>
      <Field data-invalid={invalid || undefined}>
        <FieldLabel htmlFor="public-media-input">公开视频地址</FieldLabel>
        <Textarea
          aria-describedby={invalid ? 'download-workspace-error' : undefined}
          aria-invalid={invalid || undefined}
          autoComplete="url"
          disabled={disabled}
          id="public-media-input"
          maxLength={4096}
          onChange={(event) => onUrlChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="粘贴公开媒体链接，或包含链接的完整分享文案"
          rows={3}
          value={url}
        />
        <FieldDescription>
          支持完整分享文案。按 Enter 解析，Shift+Enter 换行。
        </FieldDescription>
      </Field>
      <div className="flex items-center justify-end gap-2">
        {url ? (
          <Button
            aria-label="清空链接"
            disabled={disabled}
            onClick={() => onUrlChange('')}
            size="lg"
            type="button"
            variant="ghost"
          >
            <X aria-hidden data-icon="inline-start" />
            清空
          </Button>
        ) : null}
        <IntakeSubmitButton disabled={disabled} size="lg">
          {busy ? (
            <Spinner aria-hidden data-icon="inline-start" />
          ) : (
            <DownloadSimple aria-hidden data-icon="inline-start" />
          )}
          {busy ? '解析中…' : hasResult ? '重新解析' : '解析媒体'}
        </IntakeSubmitButton>
      </div>
    </Form>
  );
}
