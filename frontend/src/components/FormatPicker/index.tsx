import { CheckCircleFilled } from '@ant-design/icons';
import { Card, Empty, theme, Typography } from 'antd';

import type { MediaFormat } from '@/types/video';
import './index.less';

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
  const { token } = theme.useToken();

  if (!formats.length) {
    return (
      <Empty
        description="当前视频没有可用的下载版本。"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <div className="format-picker" role="radiogroup" aria-label="选择下载版本">
      {formats.map((format) => {
        const selected = format.id === selectedId;
        return (
          <Card
            variant="outlined"
            className={`format-card${selected ? ' format-card--selected' : ''}`}
            hoverable
            key={format.id}
            onClick={() => onChange(format.id)}
            role="radio"
            aria-checked={selected}
            tabIndex={0}
          >
            <div className="format-card-main">
              <div className="format-label">
                <Typography.Text strong className="format-resolution">
                  {format.plan.height}P
                </Typography.Text>
                <Typography.Text type="secondary" className="format-container">
                  {format.plan.container_preference.toUpperCase()}
                </Typography.Text>
              </div>
              <div className="format-meta">
                <Typography.Text type="secondary">
                  {format.plan.width}×{format.plan.height} ·{' '}
                  {format.plan.video_codec_family.toUpperCase()} +{' '}
                  {format.plan.audio_codec_family.toUpperCase()} ·{' '}
                  {fpsLabels[format.plan.fps_bucket]}
                </Typography.Text>
              </div>
            </div>
            {selected ? (
              <CheckCircleFilled
                className="format-check"
                style={{ color: token.colorPrimary }}
              />
            ) : null}
          </Card>
        );
      })}
    </div>
  );
}