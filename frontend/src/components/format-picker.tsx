'use client';

import { CheckCircleFilled } from '@ant-design/icons';
import { Empty, Radio, Space, Typography } from 'antd';

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
      <Empty
        description="当前视频没有可用的下载版本。"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <Radio.Group
      aria-label="选择下载版本"
      onChange={(event) => onChange(event.target.value)}
      value={selectedId}
    >
      <Space direction="vertical">
        {formats.map((format) => {
          const selected = format.id === selectedId;
          const plan = format.plan;
          return (
            <Radio key={format.id} value={format.id}>
              <Typography.Text strong>
                {plan.height}P · {plan.container_preference.toUpperCase()}
              </Typography.Text>
              <br />
              <Typography.Text type="secondary">
                {plan.width}×{plan.height} ·{' '}
                {plan.video_codec_family.toUpperCase()} +{' '}
                {plan.audio_codec_family.toUpperCase()} ·{' '}
                {fpsLabels[plan.fps_bucket]}
              </Typography.Text>
              {selected ? (
                <Typography.Text type="success">
                  {' '}
                  <CheckCircleFilled /> 已选择
                </Typography.Text>
              ) : null}
            </Radio>
          );
        })}
      </Space>
    </Radio.Group>
  );
}
