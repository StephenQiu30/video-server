'use client';

import { cn } from 'cn';
import Link from 'next/link';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { Button } from '@/components/ui/button';
import { displayError } from '@/lib/request-error';

export function RouteErrorView({
  className,
  error,
  reset,
}: {
  className?: string;
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div
      className={cn(
        'flex min-h-[calc(100svh-9rem)] items-center py-14 sm:py-20',
        className,
      )}
      data-slot="route-error"
    >
      <PageErrorNotice
        className="min-h-0 flex-1 py-0"
        message={displayError(error)}
        onRetry={reset}
        retryLabel="重新尝试"
        secondaryAction={
          <Button asChild variant="outline">
            <Link href="/">回到首页</Link>
          </Button>
        }
        title="页面暂时无法打开。"
        titleAs="h1"
      />
    </div>
  );
}
