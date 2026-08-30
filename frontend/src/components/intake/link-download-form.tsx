'use client';

import { DownloadSimple, LinkSimple, X } from '@phosphor-icons/react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
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
    <form
      className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_148px]"
      onSubmit={submit}
    >
      <InputGroup className="h-16 rounded-md bg-input sm:h-[68px]">
        <InputGroupInput
          aria-describedby={invalid ? 'download-workspace-error' : undefined}
          aria-invalid={invalid ? true : undefined}
          aria-label="公开视频地址"
          autoComplete="url"
          className="h-full px-2 text-[15px]"
          disabled={disabled}
          maxLength={4096}
          onChange={(event) => onUrlChange(event.target.value)}
          placeholder="粘贴公开的视频链接"
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
                  className="size-11"
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
      <Button
        className="h-16 px-6 text-[15px] sm:h-[68px]"
        disabled={disabled}
        type="submit"
      >
        {busy ? <Spinner aria-hidden /> : <DownloadSimple aria-hidden />}
        {busy ? '解析中…' : hasResult ? '重新解析' : '解析媒体'}
      </Button>
    </form>
  );
}
