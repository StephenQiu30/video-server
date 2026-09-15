'use client';

import type { ComponentProps } from 'react';
import { triggerBrowserDownload } from '@/services/download';

export default function AnalysisReportDownloadLink({
  href,
  onClick,
  ...props
}: ComponentProps<'a'>) {
  return (
    <a
      {...props}
      href={href}
      onClick={(event) => {
        onClick?.(event);
        if (event.defaultPrevented) return;
        event.preventDefault();
        triggerBrowserDownload(
          event.currentTarget.href,
          event.currentTarget.download,
        );
      }}
    />
  );
}
