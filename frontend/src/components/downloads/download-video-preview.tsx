'use client';

import { MediaPlayer, MediaProvider, Poster } from '@vidstack/react';
import {
  DefaultVideoLayout,
  defaultLayoutIcons,
} from '@vidstack/react/player/layouts/default';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useVideoPreviewSource } from '@/hooks/useVideoPreviewSource';

type Props = {
  container?: 'mp4' | 'webm';
  downloadId: string;
  poster?: string | null;
  title: string;
};

export default function DownloadVideoPreview({
  container,
  downloadId,
  poster,
  title,
}: Props) {
  const preview = useVideoPreviewSource(downloadId);

  if (preview.loading) {
    return (
      <Skeleton aria-label="正在准备视频预览" className="h-40 rounded-none" />
    );
  }

  if (preview.error || !preview.source) {
    return (
      <div className="flex min-h-40 items-center bg-muted p-5 sm:p-8">
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
    );
  }

  return (
    <MediaPlayer
      ariaLabel={`${title}视频预览`}
      aspectRatio="auto"
      className="w-full overflow-hidden rounded-none bg-black"
      crossOrigin="anonymous"
      key={preview.source}
      load="eager"
      onError={preview.reportPlaybackError}
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
            className="vds-poster object-contain"
            src={poster}
          />
        ) : null}
      </MediaProvider>
      <DefaultVideoLayout icons={defaultLayoutIcons} />
    </MediaPlayer>
  );
}
