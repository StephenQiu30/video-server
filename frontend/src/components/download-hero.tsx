'use client';

import {
  ClockCounterClockwise,
  LinkSimple,
  SlidersHorizontal,
  SpinnerGap,
  X,
} from '@phosphor-icons/react';
import type { FormEvent } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@/components/ui/input-group';
import { Separator } from '@/components/ui/separator';
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
    <section className="pt-16 sm:pt-20 lg:pt-24">
      <div className="text-center">
        <h1 className="text-balance text-[clamp(2.4rem,5vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.035em]">
          粘贴链接，剩下的交给帧取
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-muted-foreground">
          解析 Bilibili、YouTube、抖音等公开视频，比较可用格式并跟踪下载任务。
        </p>
      </div>

      <form
        className="mx-auto mt-10 grid max-w-[944px] gap-2.5 sm:grid-cols-[minmax(0,1fr)_132px]"
        onSubmit={submit}
      >
        <InputGroup className="h-14 rounded-lg bg-card">
          <InputGroupInput
            aria-label="公开视频地址"
            autoComplete="url"
            className="h-full px-2 text-[15px]"
            maxLength={4096}
            onChange={(event) => onUrlChange(event.target.value)}
            placeholder="粘贴公开视频链接"
            value={url}
          />
          <InputGroupAddon align="inline-start" className="gap-2 pl-3">
            <LinkSimple aria-hidden className="text-foreground" />
            {inspection ? (
              <Badge className="hidden sm:inline-flex" variant="neutral">
                {inspection.extractor_key}
              </Badge>
            ) : null}
          </InputGroupAddon>
          {url ? (
            <InputGroupAddon align="inline-end" className="pr-2">
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
          ) : null}
        </InputGroup>
        <Button className="h-14 px-8 text-[15px]" disabled={busy} type="submit">
          {busy ? <SpinnerGap className="animate-spin" /> : null}
          {busy ? '解析中…' : inspection ? '重新解析' : '解析'}
        </Button>
      </form>

      <WorkflowSteps hasInspection={Boolean(inspection)} />
      {!inspection ? <CapabilityGrid /> : null}
    </section>
  );
}

function WorkflowSteps({ hasInspection }: { hasInspection: boolean }) {
  const steps = [
    ['01', '链接'],
    ['02', '格式'],
    ['03', '下载'],
  ] as const;
  return (
    <ol className="mx-auto mb-14 mt-9 flex max-w-[760px] items-center text-sm sm:mb-16">
      {steps.map(([index, label], position) => {
        const active = position === 0 || (position === 1 && hasInspection);
        const current = position === (hasInspection ? 1 : 0);
        return (
          <li
            aria-current={current ? 'step' : undefined}
            className={position < 2 ? 'flex min-w-0 flex-1 items-center' : ''}
            key={index}
          >
            <span
              className={
                active
                  ? 'shrink-0 font-medium text-primary'
                  : 'shrink-0 text-muted-foreground'
              }
            >
              <span className="font-mono">{index}</span>{' '}
              <span className="ml-1">{label}</span>
            </span>
            {position < 2 ? (
              <Separator className="mx-4 min-w-4 flex-1 sm:mx-8" />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

function CapabilityGrid() {
  const items = [
    {
      icon: LinkSimple,
      title: '公开链接解析',
      description: '验证地址并读取可用媒体信息。',
    },
    {
      icon: SlidersHorizontal,
      title: '格式比较',
      description: '按清晰度、封装与编码选择版本。',
    },
    {
      icon: ClockCounterClockwise,
      title: '任务可追踪',
      description: '从排队到完成，持续查看执行状态。',
    },
  ];

  return (
    <div className="mb-8 grid border-y sm:grid-cols-3 sm:divide-x">
      {items.map(({ description, icon: Icon, title }, index) => (
        <div
          className={
            index > 0
              ? 'border-t px-5 py-6 sm:border-t-0 sm:px-7'
              : 'px-5 py-6 sm:px-7'
          }
          key={title}
        >
          <Icon aria-hidden className="mb-4 size-5 text-muted-foreground" />
          <h2 className="font-medium">{title}</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        </div>
      ))}
    </div>
  );
}
