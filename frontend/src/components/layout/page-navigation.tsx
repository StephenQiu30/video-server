import Link from 'next/link';
import type { ReactNode } from 'react';
import { Fragment } from 'react';
import { BackLink } from '@/components/layout/back-link';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';

/** Shared page-level return row, including loading and error states. */
export function PageNavigation({
  action,
  breadcrumbs,
  fallbackHref,
}: {
  action?: ReactNode;
  fallbackHref: string;
  breadcrumbs?: { label: string; href?: string }[];
}) {
  const className = 'mb-6 flex h-8 items-center justify-between gap-4';
  if (breadcrumbs)
    return (
      <Breadcrumb
        aria-label="面包屑"
        className={className}
        data-slot="page-navigation"
      >
        <BreadcrumbList>
          {breadcrumbs.map((item, index) => (
            <Fragment key={item.label}>
              {index > 0 ? <BreadcrumbSeparator /> : null}
              <BreadcrumbItem>
                {item.href ? (
                  <BreadcrumbLink asChild>
                    <Link href={item.href}>{item.label}</Link>
                  </BreadcrumbLink>
                ) : (
                  <BreadcrumbPage>{item.label}</BreadcrumbPage>
                )}
              </BreadcrumbItem>
            </Fragment>
          ))}
        </BreadcrumbList>
        {action}
      </Breadcrumb>
    );
  return (
    <nav
      aria-label="页面导航"
      className={className}
      data-slot="page-navigation"
    >
      <BackLink className="-ml-2" fallbackHref={fallbackHref} />
      {action}
    </nav>
  );
}
