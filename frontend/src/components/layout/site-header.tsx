'use client';

import { GithubLogoIcon } from '@phosphor-icons/react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

import { useAuth } from '@/components/auth/auth-provider';
import { DesktopNavigation } from '@/components/layout/desktop-navigation';
import { HeaderAccount } from '@/components/layout/header-account';
import { MobileNavigation } from '@/components/layout/mobile-navigation';
import { ThemeToggle } from '@/components/layout/theme-toggle';
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
  const homeActive = pathname === '/';
  const authView = pathname.startsWith('/user/');
  const historyActive = pathname.startsWith('/history');
  const documentsActive = pathname.startsWith('/documents');
  const providersActive = pathname.startsWith('/providers');
  const analyticsActive = pathname.startsWith('/admin/analytics');
  const filesActive = pathname.startsWith('/admin/files');
  const aiProvidersActive = pathname.startsWith('/admin/ai-providers');
  const catalogActive = pathname.startsWith('/admin/providers');
  const usersActive = pathname.startsWith('/admin/users');
  const headerAuthPending = (homeActive || authView) && loading;
  const publicView = homeActive && !loading && !user;

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
        <div
          aria-busy={headerAuthPending || undefined}
          className="flex w-[192px] shrink-0 items-center justify-end gap-2 lg:w-[606px]"
          data-slot="header-actions"
        >
          {headerAuthPending ? (
            <div
              aria-hidden
              className="h-11 w-full"
              data-slot="header-auth-pending"
            />
          ) : authView ? (
            <ThemeToggle />
          ) : (
            <>
              <div
                className="hidden min-w-0 flex-1 items-center justify-end lg:flex"
                data-slot="header-navigation"
              >
                <DesktopNavigation
                  documentsActive={documentsActive}
                  historyActive={historyActive}
                  homeActive={homeActive}
                  providersActive={providersActive}
                  publicView={publicView}
                />
              </div>
              {publicView ? (
                <Button
                  asChild
                  className="size-11 lg:hidden"
                  size="icon-lg"
                  variant="ghost"
                >
                  <a
                    aria-label="在 GitHub 查看 FrameFetch 源代码"
                    href="https://github.com/StephenQiu30/video-server"
                    rel="noreferrer"
                    target="_blank"
                  >
                    <GithubLogoIcon aria-hidden className="size-5" />
                  </a>
                </Button>
              ) : null}
              <ThemeToggle />
              {publicView ? (
                <div className="flex w-[88px] shrink-0 justify-end">
                  <Button
                    asChild
                    className="min-h-11 w-[74px] px-3.5 text-[15px]"
                  >
                    <Link href="/user/login">登录</Link>
                  </Button>
                </div>
              ) : (
                <>
                  <div className="hidden lg:block">
                    <HeaderAccount
                      analyticsActive={analyticsActive}
                      aiProvidersActive={aiProvidersActive}
                      catalogActive={catalogActive}
                      filesActive={filesActive}
                      loading={loading}
                      onSignOut={() => void handleSignOut()}
                      pathname={pathname}
                      signingOut={signingOut}
                      user={user}
                      usersActive={usersActive}
                    />
                  </div>
                  <MobileNavigation
                    loading={loading}
                    onSignOut={handleSignOut}
                    pathname={pathname}
                    signingOut={signingOut}
                    user={user}
                  />
                </>
              )}
            </>
          )}
        </div>
      </div>
    </header>
  );
}

export default SiteHeader;
