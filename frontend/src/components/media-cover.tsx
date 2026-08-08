'use client';

import Image from 'next/image';
import { useState } from 'react';

import fallbackCover from '@/assets/product-launch-stage.webp';
import { cn } from '@/lib/utils';

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
  const [failed, setFailed] = useState(false);
  const source = src && !failed ? src : fallbackCover;

  return (
    <div
      className={cn(
        'relative aspect-video overflow-hidden rounded-md bg-muted',
        className,
      )}
    >
      <Image
        alt={alt}
        className="object-cover"
        fill
        onError={() => setFailed(true)}
        priority
        sizes="(min-width: 1024px) 52vw, 100vw"
        src={source}
        unoptimized={typeof source === 'string'}
      />
      {platform ? (
        <span className="absolute bottom-3 left-3 rounded bg-black/78 px-2 py-1 text-xs font-medium text-white">
          {platform}
        </span>
      ) : null}
      {duration ? (
        <span className="absolute right-3 bottom-3 rounded bg-black/78 px-2 py-1 font-mono text-xs text-white">
          {duration}
        </span>
      ) : null}
    </div>
  );
}
