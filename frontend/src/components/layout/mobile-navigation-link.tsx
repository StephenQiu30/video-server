import { cn } from 'cn';
import Link from 'next/link';
import type { ReactNode } from 'react';
import {
  NavigationMenuItem,
  NavigationMenuLink,
} from '@/components/ui/navigation-menu';
import { SheetClose } from '@/components/ui/sheet';

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
    <NavigationMenuItem className="w-full">
      <SheetClose asChild>
        <NavigationMenuLink
          active={active}
          asChild
          className={cn(
            'h-control-lg w-full justify-start rounded-md px-4 py-2 text-sm font-medium',
            active && 'bg-accent text-accent-foreground',
          )}
        >
          <Link aria-current={active ? 'page' : undefined} href={href}>
            {children}
          </Link>
        </NavigationMenuLink>
      </SheetClose>
    </NavigationMenuItem>
  );
}
