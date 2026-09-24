'use client';

import { FileVideo } from '@phosphor-icons/react';
import { cn } from 'cn';
import { PageEmptyNotice } from '@/components/layout/page-empty-notice';
import { FieldLabel } from '@/components/ui/field';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { audioCodecLabel } from '@/lib/media-format';

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
  formats: API.FormatResponse[];
  mediaKind?: API.MediaKind;
  onChange: (id: string) => void;
  selectedId: string;
}) {
  if (!formats.length) {
    return (
      <PageEmptyNotice
        compact
        description="当前媒体没有可用的下载版本。"
        icon={<FileVideo aria-hidden />}
        title="没有可用格式"
      />
    );
  }

  return (
    <RadioGroup
      aria-label="选择下载版本"
      className="scrollbar-thin max-h-[min(45vh,22.5rem)] gap-1 overflow-y-auto"
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
                'min-h-10 w-full cursor-pointer flex-row rounded-md border-0 px-3 py-3 transition-colors has-data-[state=checked]:bg-muted/70 hover:bg-muted/50 hover:text-foreground',
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
                      <span className="font-mono text-xs text-foreground/70">
                        {plan.container_preference.toUpperCase()}
                      </span>
                    </span>
                    <span className="mt-1 block truncate text-xs text-foreground/70">
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
                    <span className="mt-1 block truncate text-xs text-foreground/70">
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
