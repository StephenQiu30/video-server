'use client';

import { PictureOutlined } from '@ant-design/icons';
import { Empty, Image } from 'antd';
import { useState } from 'react';

type MediaCoverProps = {
  alt: string;
  className?: string;
  duration?: string;
  platform?: string;
  src?: string | null;
};

export default function MediaCover({
  alt,
  className,
  duration,
  platform,
  src,
}: MediaCoverProps) {
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const source = src && src !== failedSource ? src : null;

  return (
    <div className={`media-cover${className ? ` ${className}` : ''}`}>
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
        <span className="media-cover-badge media-cover-platform">
          {platform}
        </span>
      ) : null}
      {duration ? (
        <span className="media-cover-badge media-cover-duration">
          {duration}
        </span>
      ) : null}
    </div>
  );
}
