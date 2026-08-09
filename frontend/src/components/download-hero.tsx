'use client';

import { LinkSimple, SpinnerGap, XCircle } from '@phosphor-icons/react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
    <section className="pt-12 sm:pt-10">
      <div className="text-center">
        <h1 className="text-balance text-[32px] font-semibold tracking-[-0.035em] sm:text-[38px]">
          粘贴链接，剩下的交给帧取
        </h1>
        <p className="mt-3 text-[15px] text-muted-foreground sm:text-base">
          粘贴 Bilibili、YouTube、抖音等公开视频链接
        </p>
      </div>

      <form
        className="mx-auto mt-8 flex max-w-[944px] flex-col overflow-hidden rounded-xl border border-input bg-white shadow-[0_1px_2px_rgba(18,32,52,0.04)] sm:h-[72px] sm:flex-row sm:items-stretch"
        onSubmit={submit}
      >
        {inspection ? (
          <span className="flex h-12 shrink-0 items-center border-b px-5 text-sm font-semibold text-[#e94776] sm:h-auto sm:border-r sm:border-b-0">
            {inspection.extractor_key}
          </span>
        ) : null}
        <div className="relative min-w-0 flex-1">
          <LinkSimple className="absolute left-4 top-1/2 size-5 -translate-y-1/2 text-foreground" />
          <Input
            aria-label="公开视频地址"
            autoComplete="url"
            className="h-14 rounded-none border-0 pl-12 pr-11 shadow-none focus-visible:shadow-none sm:h-full"
            maxLength={4096}
            onChange={(event) => onUrlChange(event.target.value)}
            placeholder="粘贴公开视频链接"
            value={url}
          />
          {url ? (
            <button
              aria-label="清空链接"
              className="focus-ring absolute right-3 top-1/2 grid size-8 -translate-y-1/2 place-items-center rounded-lg text-[#a3a9b2] hover:bg-muted"
              onClick={() => onUrlChange('')}
              type="button"
            >
              <XCircle size={17} weight="fill" />
            </button>
          ) : null}
        </div>
        <Button
          className="h-14 rounded-none px-9 text-base sm:h-auto sm:min-w-40"
          disabled={busy}
          type="submit"
        >
          {busy ? <SpinnerGap className="animate-spin" /> : null}
          {busy ? '解析中…' : inspection ? '重新解析' : '解析'}
        </Button>
      </form>

      <WorkflowSteps hasInspection={Boolean(inspection)} />
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
    <div className="mx-auto mb-14 mt-8 grid max-w-[760px] grid-cols-3 items-center gap-5 text-sm sm:mb-[68px] sm:gap-10">
      {steps.map(([index, label], position) => {
        const active = position === 0 || (position === 1 && hasInspection);
        return (
          <div className="flex min-w-0 items-center gap-4" key={index}>
            <span
              className={
                active ? 'font-semibold text-primary' : 'text-muted-foreground'
              }
            >
              {index} <span className="ml-1 hidden sm:inline">{label}</span>
            </span>
            {position < 2 ? (
              <span className="h-px min-w-4 flex-1 bg-border" />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
