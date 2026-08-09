'use client';

import Image from 'next/image';
import { useState } from 'react';

import { cn } from '@/lib/utils';

type MediaCoverProps = {
  alt: string;
  className?: string;
  duration?: string;
  platform?: string;
  priority?: boolean;
  src?: string | null;
};

export default function MediaCover({
  alt,
  className,
  duration,
  platform,
  priority = false,
  src,
}: MediaCoverProps) {
  const [failed, setFailed] = useState(false);
  const source = src && !failed ? src : '/logo.png';
  return (
    <div
      className={cn(
        'relative aspect-video overflow-hidden rounded-xl bg-[#f3f7fc]',
        className,
      )}
    >
      <Image
        alt={alt}
        className={cn(
          'object-cover',
          source === '/logo.png' && 'object-contain p-16',
        )}
        fill
        onError={() => setFailed(true)}
        priority={priority}
        sizes="(min-width: 1024px) 50vw, 100vw"
        src={source}
        unoptimized={source.startsWith('http')}
      />
      {platform ? (
        <span className="absolute bottom-3 left-3 rounded-md bg-white/94 px-2 py-1 text-xs font-medium text-primary shadow-sm">
          {platform}
        </span>
      ) : null}
      {duration ? (
        <span className="absolute bottom-3 right-3 rounded-md bg-[#252b33]/88 px-2 py-1 font-mono text-xs text-white">
          {duration}
        </span>
      ) : null}
    </div>
  );
}
