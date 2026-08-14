'use client';

import {
  ClockCounterClockwiseIcon,
  FileTextIcon,
  PulseIcon,
} from '@phosphor-icons/react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

import { useAuth } from '@/components/auth-provider';
import { HeaderAccount } from '@/components/header-account';
import { MobileNavigation } from '@/components/mobile-navigation';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export function BrandLink({ className }: { className?: string }) {
  return (
    <Link
      aria-label="帧取首页"
      className={cn(
        'focus-ring inline-flex min-h-11 items-center gap-3 rounded-md text-[17px] font-semibold tracking-[-0.02em]',
        className,
      )}
      href="/"
    >
      <Image
        alt=""
        aria-hidden
        className="size-8 shrink-0"
        height={32}
        src="/logo.svg"
        width={32}
      />
      <span>帧取</span>
    </Link>
  );
}

export function SiteHeader() {
  const { user, loading, signOut } = useAuth();
  const [signingOut, setSigningOut] = useState(false);
  const pathname = usePathname() ?? '/';
  const router = useRouter();
  const historyActive = pathname.startsWith('/history');
  const documentsActive = pathname.startsWith('/documents');
  const providersActive = pathname.startsWith('/providers');
  const analyticsActive = pathname.startsWith('/admin/analytics');
  const aiProvidersActive = pathname.startsWith('/admin/ai-providers');
  const catalogActive = pathname.startsWith('/admin/providers');
  const usersActive = pathname.startsWith('/admin/users');

  async function handleSignOut() {
    setSigningOut(true);
    await signOut();
    router.replace('/user/login');
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-40 bg-background">
      <div className="content-shell flex h-20 items-center justify-between">
        <BrandLink />
        <nav
          aria-label="主要导航"
          className="hidden items-center gap-2 lg:flex"
        >
          <Button
            asChild
            className={cn(
              'min-h-11 px-3.5 text-[15px] text-foreground',
              historyActive && 'bg-muted',
            )}
            variant="ghost"
          >
            <Link
              aria-current={historyActive ? 'page' : undefined}
              href="/history"
            >
              <ClockCounterClockwiseIcon aria-hidden className="size-5" />
              <span>下载记录</span>
            </Link>
          </Button>
          <Button
            asChild
            className={cn(
              'min-h-11 px-3.5 text-[15px] text-foreground',
              documentsActive && 'bg-muted',
            )}
            variant="ghost"
          >
            <Link
              aria-current={documentsActive ? 'page' : undefined}
              href="/documents"
            >
              <FileTextIcon aria-hidden className="size-5" />
              <span>剧本文档</span>
            </Link>
          </Button>
          <Button
            asChild
            className={cn(
              'min-h-11 px-3.5 text-[15px] text-foreground',
              providersActive && 'bg-muted',
            )}
            variant="ghost"
          >
            <Link
              aria-current={providersActive ? 'page' : undefined}
              href="/providers"
            >
              <PulseIcon aria-hidden className="size-5" />
              <span>平台状态</span>
            </Link>
          </Button>
          <HeaderAccount
            analyticsActive={analyticsActive}
            aiProvidersActive={aiProvidersActive}
            catalogActive={catalogActive}
            loading={loading}
            onSignOut={() => void handleSignOut()}
            pathname={pathname}
            signingOut={signingOut}
            user={user}
            usersActive={usersActive}
          />
        </nav>
        <MobileNavigation
          loading={loading}
          onSignOut={handleSignOut}
          pathname={pathname}
          signingOut={signingOut}
          user={user}
        />
      </div>
    </header>
  );
}

export default SiteHeader;
