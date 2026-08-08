'use client';

import {
  CopyIcon,
  DownloadSimpleIcon,
  ShieldCheckIcon,
} from '@phosphor-icons/react';

import FormatPicker from '@/components/format-picker';
import MediaCover from '@/components/media-cover';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import type { Inspection } from '@/types/video';
import { formatDuration } from '@/utils/format';

type InspectionViewProps = {
  busy: boolean;
  inspection: Inspection;
  onChange: (id: string) => void;
  onCreate: () => void;
  selectedId: string;
};

export default function InspectionView({
  busy,
  inspection,
  onChange,
  onCreate,
  selectedId,
}: InspectionViewProps) {
  const selected = inspection.formats.find(({ id }) => id === selectedId);

  async function copyInfo() {
    const text = `${inspection.title}\n${inspection.extractor_key}\n${inspection.provider_media_id}`;
    await navigator.clipboard?.writeText(text);
  }

  return (
    <section aria-labelledby="inspection-title" className="border-t">
      <div className="grid min-h-[560px] lg:grid-cols-[minmax(0,1.08fr)_minmax(420px,0.92fr)]">
        <div className="py-10 lg:border-r lg:pr-10">
          <MediaCover
            alt={`${inspection.title} 视频封面`}
            duration={formatDuration(inspection.duration_seconds)}
            platform={inspection.extractor_key}
            src={inspection.thumbnail_url}
          />
          <h2
            className="mt-8 text-balance text-2xl font-semibold tracking-tight sm:text-3xl"
            id="inspection-title"
          >
            {inspection.title}
          </h2>
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
            <span>平台：{inspection.extractor_key}</span>
            <Separator className="hidden h-4 sm:block" orientation="vertical" />
            <span>媒体 ID：{inspection.provider_media_id}</span>
            <Separator className="hidden h-4 sm:block" orientation="vertical" />
            <span>时长：{formatDuration(inspection.duration_seconds)}</span>
          </div>
        </div>

        <div className="py-10 lg:pl-10">
          <div className="mb-7 flex items-end justify-between gap-4">
            <div>
              <p className="mb-2 text-xs font-medium tracking-[0.18em] text-muted-foreground uppercase">
                Download format
              </p>
              <h2 className="text-2xl font-semibold tracking-tight">
                选择下载版本
              </h2>
            </div>
            <span className="text-sm text-muted-foreground">
              {inspection.formats.length} 个版本
            </span>
          </div>

          <FormatPicker
            formats={inspection.formats}
            onChange={onChange}
            selectedId={selectedId}
          />

          <div className="mt-7 space-y-3">
            <Button
              className="h-12 w-full text-base"
              disabled={!selectedId || busy}
              onClick={onCreate}
            >
              <DownloadSimpleIcon data-icon="inline-start" />
              {busy ? '正在创建任务…' : '开始下载'}
            </Button>
            <Button className="w-full" onClick={copyInfo} variant="ghost">
              <CopyIcon data-icon="inline-start" />
              复制视频信息
            </Button>
          </div>
        </div>
      </div>

      <div className="grid border-t py-7 lg:grid-cols-[3fr_1fr]">
        <div className="grid grid-cols-3 text-sm lg:border-r lg:pr-10">
          <Step active index="1" label="已识别视频" />
          <Step active={Boolean(selected)} index="2" label="已选择格式" />
          <Step index="3" label="等待下载" />
        </div>
        <p className="mt-6 flex items-start gap-2 text-xs leading-5 text-muted-foreground lg:mt-0 lg:pl-10">
          <ShieldCheckIcon className="mt-0.5 size-4 shrink-0" />
          仅下载你有权处理的公开内容；不支持
          Cookie、DRM、私有内容与直播播放列表。
        </p>
      </div>
    </section>
  );
}

function Step({
  active = false,
  index,
  label,
}: {
  active?: boolean;
  index: string;
  label: string;
}) {
  return (
    <span className="flex flex-col items-center gap-2 text-center">
      <span
        className={`grid size-7 place-items-center rounded-full border text-xs ${
          active ? 'border-foreground bg-foreground text-background' : ''
        }`}
      >
        {index}
      </span>
      <span className={active ? 'font-medium' : 'text-muted-foreground'}>
        {label}
      </span>
    </span>
  );
}
