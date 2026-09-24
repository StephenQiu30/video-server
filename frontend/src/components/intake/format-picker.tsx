'use client';

import { FileVideo } from '@phosphor-icons/react';
import { PageEmptyNotice } from '@/components/layout/page-empty-notice';
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldLabel,
  FieldTitle,
} from '@/components/ui/field';
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
      className="scrollbar-thin max-h-[min(45vh,22.5rem)] overflow-y-auto"
      onValueChange={onChange}
      value={selectedId}
    >
      {formats.map((format) => {
        const plan = format.plan;
        return (
          <FieldLabel htmlFor={format.id} key={format.id}>
            <Field orientation="horizontal">
              <RadioGroupItem id={format.id} value={format.id} />
              <FieldContent>
                <FieldTitle>
                  {plan
                    ? `${plan.height}P · ${plan.container_preference.toUpperCase()}`
                    : format.display_name}
                </FieldTitle>
                <FieldDescription>
                  {plan
                    ? `${plan.width}×${plan.height} · ${plan.video_codec_family.toUpperCase()} · ${audioCodecLabel(plan.audio_codec_family)} · ${fpsLabels[plan.fps_bucket]}`
                    : mediaKind === 'video_collection'
                      ? '视频合集 · 视频 ZIP'
                      : '官方图文 · 原图 ZIP'}
                </FieldDescription>
              </FieldContent>
            </Field>
          </FieldLabel>
        );
      })}
    </RadioGroup>
  );
}
