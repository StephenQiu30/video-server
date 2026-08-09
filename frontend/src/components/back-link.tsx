'use client';

import { ArrowLeftIcon } from '@phosphor-icons/react';
import Link from 'next/link';
import type { MouseEvent } from 'react';

import {
  markNavigationPush,
  useCanNavigateBack,
} from '@/components/navigation-history';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type BackLinkProps = {
  className?: string;
  fallbackHref: string;
  label?: string;
};

export function BackLink({
  className,
  fallbackHref,
  label = '返回上一步',
}: BackLinkProps) {
  const canGoBack = useCanNavigateBack();

  function navigateBack(event: MouseEvent<HTMLAnchorElement>) {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }

    if (!canGoBack || window.history.length <= 1) {
      markNavigationPush(fallbackHref);
      return;
    }

    event.preventDefault();
    window.history.back();
  }

  return (
    <Button
      asChild
      className={cn(
        '-ml-3 min-h-11 text-muted-foreground hover:text-foreground',
        className,
      )}
      variant="ghost"
    >
      <Link data-navigation-back="" href={fallbackHref} onClick={navigateBack}>
        <ArrowLeftIcon aria-hidden size={17} />
        {label}
      </Link>
    </Button>
  );
}
