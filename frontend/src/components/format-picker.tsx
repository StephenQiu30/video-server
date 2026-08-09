'use client';

import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { cn } from '@/lib/utils';
import type { MediaFormat } from '@/types/video';

const fpsLabels = {
  fps_30: '最高 30 FPS',
  fps_60: '最高 60 FPS',
  above_60: '高帧率',
};

export default function FormatPicker({
  formats,
  onChange,
  selectedId,
}: {
  formats: MediaFormat[];
  onChange: (id: string) => void;
  selectedId: string;
}) {
  if (!formats.length) {
    return (
      <p className="border-y py-10 text-sm text-muted-foreground">
        当前视频没有可用的下载版本。
      </p>
    );
  }

  return (
    <RadioGroup
      aria-label="选择下载版本"
      className="scrollbar-thin max-h-[370px] overflow-y-auto border-y border-border"
      onValueChange={onChange}
      value={selectedId}
    >
      {formats.map((format, index) => {
        const selected = format.id === selectedId;
        const plan = format.plan;
        return (
          <label
            className={cn(
              'grid min-h-[86px] cursor-pointer grid-cols-[auto_1fr] items-center gap-4 px-4 transition-colors hover:bg-[#f8fbff]',
              index > 0 && 'border-t border-border',
              selected && 'bg-[#f2f7ff]',
            )}
            htmlFor={format.id}
            key={format.id}
          >
            <RadioGroupItem id={format.id} value={format.id} />
            <span className="min-w-0">
              <span className="flex items-baseline gap-2">
                <strong className="text-xl tracking-[-0.02em]">
                  {plan.height}P
                </strong>
                <span className="text-sm text-muted-foreground">
                  {plan.container_preference.toUpperCase()}
                </span>
              </span>
              <span className="mt-1 block truncate text-sm text-muted-foreground">
                {plan.width}×{plan.height} ·{' '}
                {plan.video_codec_family.toUpperCase()} ·{' '}
                {plan.audio_codec_family.toUpperCase()} ·{' '}
                {fpsLabels[plan.fps_bucket]}
              </span>
            </span>
          </label>
        );
      })}
    </RadioGroup>
  );
}
