'use client';

import { ImageBrokenIcon, ImageIcon } from '@phosphor-icons/react';
import Image from 'next/image';
import { useEffect, useState } from 'react';

import { AspectRatio } from '@/components/ui/aspect-ratio';
import { cn } from '@/lib/utils';
import {
  isPrivateThumbnailPath,
  loadPrivateThumbnail,
} from '@/services/media-assets';

type MediaCoverProps = {
  alt: string;
  className?: string;
  priority?: boolean;
  pending?: boolean;
  src?: string | null;
};

export default function MediaCover({
  alt,
  className,
  pending = false,
  priority = false,
  src,
}: MediaCoverProps) {
  const privateSource = isPrivateThumbnailPath(src);
  const [loadedPrivateSource, setLoadedPrivateSource] = useState<{
    objectUrl: string;
    source: string;
  } | null>(null);
  const [failedSource, setFailedSource] = useState<string | null>(null);

  useEffect(() => {
    if (!privateSource || !src) return;
    const controller = new AbortController();
    let objectUrl: string | null = null;
    setFailedSource(null);
    setLoadedPrivateSource(null);

    void loadPrivateThumbnail(src, controller.signal)
      .then((image) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(image);
        setLoadedPrivateSource({ objectUrl, source: src });
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailedSource(src);
      });

    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [privateSource, src]);

  const resolvedSource = privateSource
    ? loadedPrivateSource?.source === src
      ? loadedPrivateSource.objectUrl
      : null
    : src;
  const unavailable = !src || failedSource === src;
  const loading = Boolean(
    privateSource && src && !resolvedSource && !unavailable,
  );
  const generating = pending && !src;
  return (
    <AspectRatio
      className={cn(
        'relative overflow-hidden rounded-none bg-muted',
        className,
      )}
      ratio={1.86}
    >
      {loading ? (
        <div
          aria-label={`${alt}（封面加载中）`}
          className="absolute inset-0 animate-pulse bg-muted"
          role="img"
        />
      ) : generating ? (
        <div
          aria-label={`${alt}（封面生成中）`}
          className="absolute inset-0 flex animate-pulse flex-col items-center justify-center gap-3 text-muted-foreground"
          role="img"
        >
          <ImageIcon aria-hidden className="size-7" />
          <span className="text-xs">封面生成中</span>
        </div>
      ) : unavailable || !resolvedSource ? (
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
          src={resolvedSource}
          unoptimized
        />
      )}
    </AspectRatio>
  );
}
