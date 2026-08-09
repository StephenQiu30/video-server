'use client';

import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';
import { FieldLabel } from '@/components/ui/field';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Separator } from '@/components/ui/separator';
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
      <Empty className="min-h-48 border-y">
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
      className="scrollbar-thin max-h-[360px] gap-0 overflow-y-auto"
      onValueChange={onChange}
      value={selectedId}
    >
      {formats.map((format, index) => {
        const selected = format.id === selectedId;
        const plan = format.plan;
        return (
          <div key={format.id}>
            {index > 0 ? <Separator /> : null}
            <FieldLabel
              className={cn(
                'min-h-[78px] cursor-pointer flex-row rounded-none border-0 px-3 py-3 transition-colors hover:bg-muted/60',
                selected && 'bg-accent hover:bg-accent',
              )}
              htmlFor={format.id}
            >
              <RadioGroupItem id={format.id} value={format.id} />
              <span className="min-w-0">
                <span className="flex items-baseline gap-2">
                  <strong className="text-lg tracking-[-0.02em]">
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
            </FieldLabel>
          </div>
        );
      })}
    </RadioGroup>
  );
}
