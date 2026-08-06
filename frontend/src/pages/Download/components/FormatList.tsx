import { Radio, Space, Tag, Typography } from 'antd';
import { formatBytes, type MediaFormat } from '@/utils/videoData';

type Props = {
  formats: MediaFormat[];
  value: string | null;
  onChange: (value: string) => void;
};

export default function FormatList({ formats, value, onChange }: Props) {
  return (
    <Radio.Group
      aria-label="清晰度选择"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      style={{ width: '100%' }}
    >
      <Space orientation="vertical" size="small" style={{ width: '100%' }}>
        {formats.map((format) => (
          <Radio key={format.id} value={format.id} style={{ width: '100%' }}>
            <Space wrap>
              <Typography.Text strong>{format.label}</Typography.Text>
              {format.container ? <Tag>{format.container}</Tag> : null}
              {format.fps ? (
                <Typography.Text type="secondary">
                  {format.fps} FPS
                </Typography.Text>
              ) : null}
              <Typography.Text type="secondary">
                {formatBytes(format.estimatedSizeBytes)}
              </Typography.Text>
              {format.requiresMerge ? (
                <Tag color="blue">将自动合并音视频</Tag>
              ) : null}
            </Space>
          </Radio>
        ))}
      </Space>
    </Radio.Group>
  );
}
