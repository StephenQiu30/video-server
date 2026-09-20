'use client';

import { useEffect } from 'react';

import { RouteErrorView } from '@/components/layout/route-error-view';

export default function RouteSegmentError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return <RouteErrorView error={error} reset={reset} />;
}
