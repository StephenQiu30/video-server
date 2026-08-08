'use client';

import { CheckCircleIcon } from '@phosphor-icons/react';

import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { cn } from '@/lib/utils';
import type { MediaFormat } from '@/types/video';

type FormatPickerProps = {
  formats: MediaFormat[];
  onChange: (id: string) => void;
  selectedId: string;
};

const fpsLabels = {
  fps_30: '最高 30 FPS',
  fps_60: '最高 60 FPS',
  above_60: '高帧率',
};

export default function FormatPicker({
  formats,
  onChange,
  selectedId,
}: FormatPickerProps) {
  if (!formats.length) {
    return (
      <p className="border-y py-8 text-sm text-muted-foreground">
        当前视频没有可用的下载版本。
      </p>
    );
  }

  return (
    <RadioGroup
      aria-label="选择下载版本"
      className="gap-0 overflow-hidden rounded-md border"
      onValueChange={onChange}
      value={selectedId}
    >
      {formats.map((format, index) => {
        const selected = format.id === selectedId;
        const plan = format.plan;
        return (
          <label
            className={cn(
              'relative grid cursor-pointer grid-cols-[auto_1fr_auto] items-center gap-4 px-5 py-5 transition-colors hover:bg-muted/50',
              index > 0 && 'border-t',
              selected && 'bg-blue-50/60 ring-1 ring-inset ring-brand',
            )}
            htmlFor={format.id}
            key={format.id}
          >
            <RadioGroupItem id={format.id} value={format.id} />
            <span className="min-w-0">
              <span className="block font-medium">
                {plan.height}P · {plan.container_preference.toUpperCase()} ·
                视频 + 音频
              </span>
              <span className="mt-1 block truncate text-sm text-muted-foreground">
                {plan.width}×{plan.height} ·{' '}
                {plan.video_codec_family.toUpperCase()} ·{' '}
                {fpsLabels[plan.fps_bucket]}
              </span>
            </span>
            {selected ? (
              <span className="flex items-center gap-1 text-xs font-medium text-brand">
                <CheckCircleIcon weight="fill" /> 推荐
              </span>
            ) : null}
          </label>
        );
      })}
    </RadioGroup>
  );
}
