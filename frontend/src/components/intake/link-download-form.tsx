'use client';

import { DownloadSimple, LinkSimple, X } from '@phosphor-icons/react';
import { cn } from 'cn';
import type { FormEvent } from 'react';
import {
  IntakeControlRow,
  IntakeSubmitButton,
  intakeControlHeightClassName,
} from '@/components/intake/intake-control-row';
import { Form } from '@/components/ui/form';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
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

  return (
    <Form onSubmit={submit}>
      <IntakeControlRow>
        <InputGroup className={cn(intakeControlHeightClassName)}>
          <InputGroupTextarea
            aria-describedby={invalid ? 'download-workspace-error' : undefined}
            aria-invalid={invalid ? true : undefined}
            aria-label="公开视频地址"
            autoComplete="url"
            className="flex-1 field-sizing-fixed h-full min-h-0 max-h-full overflow-y-auto px-2 py-5 text-[15px] leading-6 sm:py-6"
            disabled={disabled}
            maxLength={4096}
            onChange={(event) => onUrlChange(event.target.value)}
            placeholder="粘贴媒体链接或平台分享文案"
            rows={1}
            value={url}
          />
          <InputGroupAddon align="inline-start" className="gap-2 pl-4">
            <LinkSimple aria-hidden className="text-muted-foreground" />
          </InputGroupAddon>
          {url ? (
            <InputGroupAddon align="inline-end" className="pr-3">
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
            </InputGroupAddon>
          ) : null}
        </InputGroup>
        <IntakeSubmitButton disabled={disabled}>
          {busy ? (
            <Spinner aria-hidden data-icon="inline-start" />
          ) : (
            <DownloadSimple aria-hidden data-icon="inline-start" />
          )}
          {busy ? '解析中…' : hasResult ? '重新解析' : '解析媒体'}
        </IntakeSubmitButton>
      </IntakeControlRow>
    </Form>
  );
}
