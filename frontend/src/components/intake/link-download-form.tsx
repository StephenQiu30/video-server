'use client';

import { DownloadSimple, LinkSimple, X } from '@phosphor-icons/react';
import type { FormEvent, KeyboardEvent } from 'react';
import { IntakeSubmitButton } from '@/components/intake/intake-control-row';
import { Form } from '@/components/ui/form';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupText,
  InputGroupTextarea,
} from '@/components/ui/input-group';
import { Spinner } from '@/components/ui/spinner';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

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
    <Form onSubmit={submit}>
      <InputGroup>
        <InputGroupTextarea
          aria-describedby={invalid ? 'download-workspace-error' : undefined}
          aria-invalid={invalid ? true : undefined}
          aria-label="公开视频地址"
          autoComplete="url"
          disabled={disabled}
          maxLength={4096}
          onChange={(event) => onUrlChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="粘贴媒体链接或平台分享文案"
          rows={2}
          value={url}
        />
        <InputGroupAddon align="block-end" className="justify-between">
          <InputGroupText>
            <LinkSimple aria-hidden />
            支持完整分享文案
          </InputGroupText>
          <div className="flex items-center gap-2">
            {url ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <InputGroupButton
                    aria-label="清空链接"
                    disabled={disabled}
                    onClick={() => onUrlChange('')}
                    size="icon-sm"
                  >
                    <X aria-hidden />
                  </InputGroupButton>
                </TooltipTrigger>
                <TooltipContent>清空链接</TooltipContent>
              </Tooltip>
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
        </InputGroupAddon>
      </InputGroup>
    </Form>
  );
}
