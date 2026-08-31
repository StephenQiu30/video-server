import {
  ArrowUpRightIcon,
  ClockCounterClockwiseIcon,
  FileTextIcon,
  GithubLogoIcon,
  HouseIcon,
  PulseIcon,
} from '@phosphor-icons/react';
import Link from 'next/link';
import type { ReactNode } from 'react';

import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  navigationMenuTriggerStyle,
} from '@/components/ui/navigation-menu';
import { cn } from '@/lib/utils';

type DesktopNavigationProps = {
  documentsActive: boolean;
  historyActive: boolean;
  homeActive: boolean;
  providersActive: boolean;
  publicView: boolean;
};

export function DesktopNavigation({
  documentsActive,
  historyActive,
  homeActive,
  providersActive,
  publicView,
}: DesktopNavigationProps) {
  return (
    <NavigationMenu
      aria-label="主要导航"
      className="hidden max-w-none flex-none lg:flex"
      viewport={false}
    >
      <NavigationMenuList className="gap-2">
        {publicView ? (
          <>
            <NavigationLink href="/#capabilities">产品能力</NavigationLink>
            <NavigationLink href="/#architecture">自托管架构</NavigationLink>
            <NavigationLink href="https://github.com/StephenQiu30/video-server">
              <GithubLogoIcon aria-hidden className="size-5" />
              GitHub
              <ArrowUpRightIcon aria-hidden className="size-4" />
            </NavigationLink>
          </>
        ) : (
          <>
            <NavigationLink active={homeActive} href="/">
              <HouseIcon aria-hidden className="size-5" />
              首页
            </NavigationLink>
            <NavigationLink active={historyActive} href="/history">
              <ClockCounterClockwiseIcon aria-hidden className="size-5" />
              下载记录
            </NavigationLink>
            <NavigationLink active={documentsActive} href="/documents">
              <FileTextIcon aria-hidden className="size-5" />
              剧本文档
            </NavigationLink>
            <NavigationLink active={providersActive} href="/providers">
              <PulseIcon aria-hidden className="size-5" />
              平台状态
            </NavigationLink>
          </>
        )}
      </NavigationMenuList>
    </NavigationMenu>
  );
}

function NavigationLink({
  active = false,
  children,
  href,
}: {
  active?: boolean;
  children: ReactNode;
  href: string;
}) {
  const external = href.startsWith('https://');

  return (
    <NavigationMenuItem>
      <NavigationMenuLink
        active={active}
        asChild
        className={cn(
          navigationMenuTriggerStyle(),
          'h-11 min-h-11 rounded-md px-3.5 text-[15px] text-foreground',
          active && 'bg-muted',
        )}
      >
        <Link
          aria-current={active ? 'page' : undefined}
          href={href}
          rel={external ? 'noreferrer' : undefined}
          target={external ? '_blank' : undefined}
        >
          {children}
        </Link>
      </NavigationMenuLink>
    </NavigationMenuItem>
  );
}
