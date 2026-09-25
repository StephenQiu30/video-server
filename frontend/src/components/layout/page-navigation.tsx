import type { ReactNode } from 'react';
import { BackLink } from '@/components/layout/back-link';

/** Shared page-level return row, including loading and error states. */
export function PageNavigation({
  action,
  fallbackHref,
}: {
  action?: ReactNode;
  fallbackHref: string;
}) {
  return (
    <nav
      aria-label="页面导航"
      className="mb-6 flex h-8 items-center justify-between gap-4"
      data-slot="page-navigation"
    >
      <BackLink className="-ml-2" fallbackHref={fallbackHref} />
      {action}
    </nav>
  );
}
