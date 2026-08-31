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

import { Button } from '@/components/ui/button';
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
    <nav aria-label="主要导航" className="hidden items-center gap-2 lg:flex">
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
    </nav>
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
    <Button
      asChild
      className={cn(
        'min-h-11 px-3.5 text-[15px] text-foreground',
        active && 'bg-muted',
      )}
      variant="ghost"
    >
      <Link
        aria-current={active ? 'page' : undefined}
        href={href}
        rel={external ? 'noreferrer' : undefined}
        target={external ? '_blank' : undefined}
      >
        {children}
      </Link>
    </Button>
  );
}
