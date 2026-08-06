import { Card, Image, Space, Typography } from 'antd';
import {
  formatDuration,
  type MediaSummary as MediaSummaryModel,
} from '@/utils/videoData';

export default function MediaSummary({ media }: { media: MediaSummaryModel }) {
  return (
    <Card aria-label="视频摘要" size="small">
      <Space align="start" size="middle" wrap>
        {media.thumbnailUrl ? (
          <Image
            src={media.thumbnailUrl}
            alt="视频缩略图"
            width={160}
            height={90}
            preview={false}
          />
        ) : null}
        <div>
          <Typography.Title
            level={3}
            style={{ margin: 0, overflowWrap: 'anywhere' }}
          >
            {media.title}
          </Typography.Title>
          <Typography.Text type="secondary">
            {media.platform} · {formatDuration(media.durationSeconds)}
          </Typography.Text>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            解析结果有效期至 {new Date(media.expiresAt).toLocaleString()}
          </Typography.Paragraph>
        </div>
      </Space>
    </Card>
  );
}
