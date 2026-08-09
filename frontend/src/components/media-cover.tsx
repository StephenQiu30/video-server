'use client';

import { ImageBrokenIcon } from '@phosphor-icons/react';
import Image from 'next/image';
import { useState } from 'react';

import { AspectRatio } from '@/components/ui/aspect-ratio';
import { cn } from '@/lib/utils';

type MediaCoverProps = {
  alt: string;
  className?: string;
  priority?: boolean;
  src?: string | null;
};

export default function MediaCover({
  alt,
  className,
  priority = false,
  src,
}: MediaCoverProps) {
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const unavailable = !src || failedSource === src;
  return (
    <AspectRatio
      className={cn(
        'relative overflow-hidden rounded-none bg-muted',
        className,
      )}
      ratio={1.86}
    >
      {unavailable ? (
        <div
          aria-label={`${alt}（封面不可用）`}
          className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-muted-foreground"
          role="img"
        >
          <ImageBrokenIcon aria-hidden className="size-7" />
          <span className="text-xs">封面不可用</span>
        </div>
      ) : (
        <Image
          alt={alt}
          className="object-cover"
          fill
          onError={() => setFailedSource(src)}
          priority={priority}
          sizes="(min-width: 1024px) 50vw, 100vw"
          src={src}
          unoptimized={src.startsWith('http')}
        />
      )}
    </AspectRatio>
  );
}
