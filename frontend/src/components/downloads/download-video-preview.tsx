'use client';

import {
  MediaPlayer,
  type MediaPlayerInstance,
  MediaProvider,
  Poster,
} from '@vidstack/react';
import {
  DefaultVideoLayout,
  defaultLayoutIcons,
} from '@vidstack/react/player/layouts/default';
import { type Ref, useEffect } from 'react';
import { mediaFrameAspectRatio } from '@/components/intake/media-cover';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AspectRatio } from '@/components/ui/aspect-ratio';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useVideoPreviewSource } from '@/hooks/useVideoPreviewSource';

type Props = {
  container?: 'mp4' | 'webm';
  downloadId: string;
  poster?: string | null;
  title: string;
  playerRef?: Ref<MediaPlayerInstance>;
  onReadyChange?: (ready: boolean) => void;
};

export default function DownloadVideoPreview({
  container,
  downloadId,
  poster,
  title,
  playerRef,
  onReadyChange,
}: Props) {
  const preview = useVideoPreviewSource(downloadId);
  useEffect(() => {
    if (preview.loading || preview.error || !preview.source)
      onReadyChange?.(false);
    return () => onReadyChange?.(false);
  }, [preview.loading, preview.error, preview.source, onReadyChange]);

  if (preview.loading) {
    return (
      <AspectRatio ratio={mediaFrameAspectRatio}>
        <Skeleton
          aria-label="正在准备视频预览"
          className="size-full rounded-none"
        />
      </AspectRatio>
    );
  }

  if (preview.error || !preview.source) {
    return (
      <AspectRatio ratio={mediaFrameAspectRatio}>
        <div className="flex size-full items-center bg-muted p-5 sm:p-8">
          <Alert variant="warning">
            <AlertTitle>暂时无法预览视频</AlertTitle>
            <AlertDescription>
              {preview.error ?? '没有可用的视频预览地址。'}
            </AlertDescription>
            <Button className="mt-4" onClick={preview.reload} variant="outline">
              重新加载预览
            </Button>
          </Alert>
        </div>
      </AspectRatio>
    );
  }

  return (
    <AspectRatio className="overflow-hidden" ratio={mediaFrameAspectRatio}>
      <MediaPlayer
        ref={playerRef}
        ariaLabel={`${title}视频预览`}
        aspectRatio="auto"
        className="size-full overflow-hidden rounded-none bg-black"
        crossOrigin="anonymous"
        key={preview.source}
        load="eager"
        onCanPlay={() => onReadyChange?.(true)}
        onError={() => {
          onReadyChange?.(false);
          preview.reportPlaybackError();
        }}
        playsInline
        poster={poster ?? undefined}
        src={
          container
            ? { src: preview.source, type: `video/${container}` }
            : preview.source
        }
        title={title}
      >
        <MediaProvider>
          {poster ? (
            <Poster
              alt={`${title}封面`}
              className="vds-poster size-full object-cover"
              src={poster}
            />
          ) : null}
        </MediaProvider>
        <DefaultVideoLayout icons={defaultLayoutIcons} />
      </MediaPlayer>
    </AspectRatio>
  );
}
