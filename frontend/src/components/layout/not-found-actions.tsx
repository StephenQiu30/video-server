'use client';

import Link from 'next/link';

import { BackLink } from '@/components/layout/back-link';
import { Button } from '@/components/ui/button';

export function NotFoundActions() {
  return (
    <div className="flex flex-col items-start gap-2 sm:flex-row">
      <BackLink className="ml-0" fallbackHref="/" />
      <Button asChild variant="outline">
        <Link href="/">回到首页</Link>
      </Button>
    </div>
  );
}
