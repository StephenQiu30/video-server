import type { ReactNode } from 'react';

// The media column and frame position stay the same from inspection through
// download and playback. Only the content inside the 16:9 frame changes.
export const mediaResultGridClassName =
  'grid items-start gap-10 lg:grid-cols-[minmax(0,1.55fr)_minmax(320px,1fr)] lg:gap-14';

export function MediaResult({
  actions,
  headingLevel,
  media,
  metadata,
  title,
}: {
  actions: ReactNode;
  headingLevel: 1 | 2;
  media: ReactNode;
  metadata: ReactNode;
  title: string;
}) {
  const Heading = headingLevel === 1 ? 'h1' : 'h2';

  return (
    <div className={mediaResultGridClassName} data-slot="media-result">
      <div className="min-w-0">
        <div className="w-full" data-slot="media-result-frame">
          {media}
        </div>
        <Heading className="mt-5 break-words text-pretty text-xl font-semibold leading-7 tracking-[-0.03em] sm:text-2xl sm:leading-8">
          {title}
        </Heading>
        {metadata}
      </div>
      <div className="min-w-0 lg:pt-1">{actions}</div>
    </div>
  );
}
