'use client';

import Image from 'next/image';
import { useState } from 'react';

import { AspectRatio } from '@/components/ui/aspect-ratio';
import { Badge } from '@/components/ui/badge';
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
    <AspectRatio
      className={cn(
        'relative overflow-hidden rounded-lg bg-muted ring-1 ring-foreground/10',
        className,
      )}
      ratio={16 / 9}
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
        <Badge
          className="absolute bottom-3 left-3 bg-card/95 text-foreground backdrop-blur"
          variant="outline"
        >
          {platform}
        </Badge>
      ) : null}
      {duration ? (
        <Badge className="absolute right-3 bottom-3 bg-foreground/85 font-mono text-background">
          {duration}
        </Badge>
      ) : null}
    </AspectRatio>
  );
}
