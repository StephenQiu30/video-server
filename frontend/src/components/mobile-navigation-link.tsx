import Link from 'next/link';
import type { ReactNode } from 'react';

import { Button } from '@/components/ui/button';
import { SheetClose } from '@/components/ui/sheet';
import { cn } from '@/lib/utils';

export function MobileNavigationLink({
  active = false,
  children,
  href,
}: {
  active?: boolean;
  children: ReactNode;
  href: string;
}) {
  return (
    <SheetClose asChild>
      <Button
        asChild
        className={cn(
          'h-11 justify-start',
          active && 'bg-accent text-accent-foreground',
        )}
        variant="ghost"
      >
        <Link aria-current={active ? 'page' : undefined} href={href}>
          {children}
        </Link>
      </Button>
    </SheetClose>
  );
}
