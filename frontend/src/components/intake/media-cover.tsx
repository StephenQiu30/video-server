'use client';

import { ImageIcon } from '@phosphor-icons/react';
import Image from 'next/image';
import { useEffect, useState } from 'react';

import { AspectRatio } from '@/components/ui/aspect-ratio';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import {
  isPrivateThumbnailPath,
  loadPrivateThumbnail,
} from '@/services/media-assets';

type MediaCoverProps = {
  alt: string;
  className?: string;
  compact?: boolean;
  fallback?: {
    detail?: string | null;
    eyebrow?: string | null;
    title?: string | null;
  };
  priority?: boolean;
  pending?: boolean;
  src?: string | null;
};

export default function MediaCover({
  alt,
  className,
  compact = false,
  fallback,
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
  const fallbackTitle = fallback?.title?.trim() || alt;
  const fallbackEyebrow = fallback?.eyebrow?.trim() || '媒体内容';
  const fallbackDetail = fallback?.detail?.trim() || '封面未提供';
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
        <MediaCoverFallback
          compact={compact}
          detail={fallbackDetail}
          eyebrow={fallbackEyebrow}
          title={fallbackTitle}
        />
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

function MediaCoverFallback({
  compact,
  detail,
  eyebrow,
  title,
}: {
  compact: boolean;
  detail: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <div
      aria-label={`${title}（暂无封面）`}
      className="absolute inset-0 overflow-hidden bg-foreground text-background"
      role="img"
    >
      <div
        aria-hidden
        className="absolute -right-12 -top-16 size-44 rounded-full bg-primary/30"
      />
      <div
        aria-hidden
        className="absolute bottom-0 left-0 h-1 w-2/5 bg-primary"
      />
      <div
        className={cn(
          'relative flex h-full min-w-0 flex-col justify-between',
          compact ? 'gap-1 p-2' : 'gap-3 p-3 sm:p-4',
        )}
      >
        <Badge
          className={cn(
            'border-background/15 bg-background/10 font-normal text-background hover:bg-background/10',
            compact ? 'px-1.5 py-0 text-[9px]' : 'text-[10px]',
          )}
        >
          {eyebrow}
        </Badge>
        <div className="min-w-0">
          <p
            className={cn(
              'font-medium tracking-[-0.02em]',
              compact
                ? 'line-clamp-1 text-xs leading-tight'
                : 'line-clamp-2 text-sm leading-snug sm:text-base',
            )}
          >
            {title}
          </p>
        </div>
        <div
          className={cn(
            'min-w-0 text-background/65',
            compact
              ? 'text-[9px] leading-3'
              : 'text-[10px] leading-4 sm:text-xs',
          )}
        >
          <p className="truncate">{detail}</p>
          {!compact ? (
            <p className="mt-0.5 text-background/45">暂无封面</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
