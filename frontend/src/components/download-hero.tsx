'use client';

import {
  DownloadSimple,
  LinkSimple,
  SpinnerGap,
  X,
} from '@phosphor-icons/react';
import type { FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@/components/ui/input-group';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { Inspection } from '@/types/video';

type DownloadHeroProps = {
  busy: boolean;
  inspection: Inspection | null;
  onInspect: () => void;
  onUrlChange: (value: string) => void;
  url: string;
};

export default function DownloadHero({
  busy,
  inspection,
  onInspect,
  onUrlChange,
  url,
}: DownloadHeroProps) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onInspect();
  }

  return (
    <section className="pt-14 sm:pt-16 lg:pt-[72px]">
      <p className="eyebrow text-muted-foreground">01 / 解析媒体</p>
      <div className="mt-6">
        <h1 className="text-[clamp(3.2rem,5.4vw,4.25rem)] font-medium leading-[0.96] tracking-[-0.06em] sm:whitespace-nowrap">
          把视频，
          <span className="block sm:ml-[0.85em] sm:inline">带回本地。</span>
        </h1>
        <p className="mt-5 max-w-2xl text-[15px] leading-7 text-muted-foreground">
          粘贴你有权处理的公开视频链接，读取媒体信息，选择画质并创建可追踪的下载任务。
        </p>
      </div>

      <form
        className="mt-8 grid gap-2 sm:grid-cols-[minmax(0,1fr)_148px] lg:mt-9"
        onSubmit={submit}
      >
        <InputGroup className="h-16 rounded-md bg-input sm:h-[68px]">
          <InputGroupInput
            aria-label="公开视频地址"
            autoComplete="url"
            className="h-full px-2 text-[15px]"
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
                    onClick={() => onUrlChange('')}
                    size="icon-sm"
                  >
                    <X aria-hidden />
                  </InputGroupButton>
                </TooltipTrigger>
                <TooltipContent>清空链接</TooltipContent>
              </Tooltip>
            </InputGroupAddon>
          ) : (
            <InputGroupAddon align="inline-end" className="hidden pr-4 sm:flex">
              <kbd className="rounded bg-background px-2 py-1 font-mono text-[11px] font-normal text-muted-foreground">
                ⌘V
              </kbd>
            </InputGroupAddon>
          )}
        </InputGroup>
        <Button
          className="h-16 px-6 text-[15px] sm:h-[68px]"
          disabled={busy}
          type="submit"
        >
          {busy ? (
            <SpinnerGap className="animate-spin" />
          ) : (
            <DownloadSimple aria-hidden />
          )}
          {busy ? '解析中…' : inspection ? '重新解析' : '解析媒体'}
        </Button>
      </form>

      {!inspection ? <EmptyWorkflow /> : null}
    </section>
  );
}

function EmptyWorkflow() {
  return (
    <div className="mt-16 grid gap-10 border-t pt-7 sm:grid-cols-2 lg:mt-20">
      <div>
        <p className="eyebrow text-muted-foreground">02 / 选择画质</p>
        <p className="mt-3 max-w-sm text-sm leading-6 text-muted-foreground">
          解析完成后，按分辨率、编码与兼容性选择可用版本。
        </p>
      </div>
      <div>
        <p className="eyebrow text-muted-foreground">03 / 创建任务</p>
        <p className="mt-3 max-w-sm text-sm leading-6 text-muted-foreground">
          下载、封装、校验与保存状态会持续更新，随时可从记录中继续。
        </p>
      </div>
    </div>
  );
}
