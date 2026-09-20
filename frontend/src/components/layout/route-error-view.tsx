'use client';

import { cn } from 'cn';
import Link from 'next/link';

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
      role="alert"
    >
      <div className="w-full max-w-3xl">
        <p className="font-mono text-sm text-muted-foreground">ERROR</p>
        <h1 className="mt-5 text-[clamp(2.75rem,7vw,5rem)] font-medium leading-[0.96] tracking-[-0.06em]">
          页面暂时无法打开。
        </h1>
        <p className="mt-5 max-w-xl text-base leading-7 text-muted-foreground">
          {displayError(error)}
        </p>
        <div className="mt-8 flex flex-col items-start gap-2 sm:flex-row">
          <Button onClick={reset}>重新尝试</Button>
          <Button asChild variant="outline">
            <Link href="/">回到首页</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
