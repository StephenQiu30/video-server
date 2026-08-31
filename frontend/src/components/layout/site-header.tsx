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
import { ThemeMenu } from '@/components/layout/theme-menu';
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
  const historyActive = pathname.startsWith('/history');
  const documentsActive = pathname.startsWith('/documents');
  const providersActive = pathname.startsWith('/providers');
  const analyticsActive = pathname.startsWith('/admin/analytics');
  const filesActive = pathname.startsWith('/admin/files');
  const aiProvidersActive = pathname.startsWith('/admin/ai-providers');
  const catalogActive = pathname.startsWith('/admin/providers');
  const usersActive = pathname.startsWith('/admin/users');
  const publicView = pathname === '/' && !loading && !user;

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
        <div className="flex items-center gap-2">
          <DesktopNavigation
            documentsActive={documentsActive}
            historyActive={historyActive}
            homeActive={homeActive}
            providersActive={providersActive}
            publicView={publicView}
          />
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
          <ThemeMenu />
          {publicView ? (
            <Button asChild className="min-h-11 px-4 text-[15px]">
              <Link href="/user/login">登录</Link>
            </Button>
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
        </div>
      </div>
    </header>
  );
}

export default SiteHeader;
