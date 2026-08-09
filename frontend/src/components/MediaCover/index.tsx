import { PictureOutlined } from '@ant-design/icons';
import { Empty, Image, Tag, theme } from 'antd';
import { useState } from 'react';

import { formatDuration } from '@/utils/format';
import './index.less';

type MediaCoverProps = {
  alt: string;
  className?: string;
  durationSeconds?: number;
  platform?: string;
  src?: string | null;
};

export default function MediaCover({
  alt,
  className,
  durationSeconds,
  platform,
  src,
}: MediaCoverProps) {
  const { token } = theme.useToken();
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const source = src && src !== failedSource ? src : null;

  return (
    <div
      className={`media-cover${className ? ` ${className}` : ''}`}
      style={{ background: token.colorFillQuaternary }}
    >
      {source ? (
        <Image
          alt={alt}
          fallback=""
          onError={() => setFailedSource(source)}
          preview={false}
          src={source}
        />
      ) : (
        <div className="media-cover-empty">
          <Empty
            description="该视频未提供可用封面"
            image={<PictureOutlined style={{ fontSize: 40 }} />}
          />
        </div>
      )}
      {platform ? (
        <Tag className="media-cover-badge media-cover-platform" color="blue">
          {platform}
        </Tag>
      ) : null}
      {durationSeconds !== undefined ? (
        <span className="media-cover-badge media-cover-duration">
          {formatDuration(durationSeconds)}
        </span>
      ) : null}
    </div>
  );
}