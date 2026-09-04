'use client';

import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';
import { FieldLabel } from '@/components/ui/field';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { audioCodecLabel } from '@/lib/media-format';
import { cn } from '@/lib/utils';
import type { MediaFormat, MediaKind } from '@/types/video';

const fpsLabels = {
  fps_30: '最高 30 FPS',
  fps_60: '最高 60 FPS',
  above_60: '高帧率',
};

export default function FormatPicker({
  formats,
  mediaKind = 'image_gallery',
  onChange,
  selectedId,
}: {
  formats: MediaFormat[];
  mediaKind?: MediaKind;
  onChange: (id: string) => void;
  selectedId: string;
}) {
  if (!formats.length) {
    return (
      <Empty className="min-h-48 border-0">
        <EmptyHeader>
          <EmptyTitle>没有可用格式</EmptyTitle>
          <EmptyDescription>当前视频没有可用的下载版本。</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <RadioGroup
      aria-label="选择下载版本"
      className="scrollbar-thin max-h-[360px] gap-1 overflow-y-auto"
      onValueChange={onChange}
      value={selectedId}
    >
      {formats.map((format) => {
        const selected = format.id === selectedId;
        const plan = format.plan;
        return (
          <div key={format.id}>
            <FieldLabel
              className={cn(
                'min-h-[62px] cursor-pointer flex-row rounded-md border-0 px-2 py-3 transition-colors has-data-[state=checked]:bg-muted/70 hover:bg-muted/50 hover:text-foreground',
                selected ? 'text-foreground' : 'text-muted-foreground',
              )}
              htmlFor={format.id}
            >
              <RadioGroupItem id={format.id} value={format.id} />
              <span className="min-w-0">
                {plan ? (
                  <>
                    <span className="flex items-baseline gap-2">
                      <strong className="text-[15px] tracking-[-0.02em]">
                        {plan.height}P
                      </strong>
                      <span className="font-mono text-xs text-muted-foreground">
                        {plan.container_preference.toUpperCase()}
                      </span>
                    </span>
                    <span className="mt-1 block truncate text-xs text-muted-foreground">
                      {plan.width}×{plan.height} ·{' '}
                      {plan.video_codec_family.toUpperCase()} ·{' '}
                      {audioCodecLabel(plan.audio_codec_family)} ·{' '}
                      {fpsLabels[plan.fps_bucket]}
                    </span>
                  </>
                ) : (
                  <>
                    <span className="flex items-baseline gap-2">
                      <strong className="text-[15px] tracking-[-0.02em]">
                        {format.display_name}
                      </strong>
                    </span>
                    <span className="mt-1 block truncate text-xs text-muted-foreground">
                      {mediaKind === 'video_collection'
                        ? '视频合集 · 视频 ZIP'
                        : '官方图文 · 原图 ZIP'}
                    </span>
                  </>
                )}
              </span>
            </FieldLabel>
          </div>
        );
      })}
    </RadioGroup>
  );
}
