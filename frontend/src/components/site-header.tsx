'use client';

import {
  CaretDownIcon,
  ClockCounterClockwiseIcon,
  DownloadSimpleIcon,
  SignOutIcon,
  UserCircleIcon,
  UsersThreeIcon,
} from '@phosphor-icons/react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

import { useAuth } from '@/components/auth-provider';
import { MobileNavigation } from '@/components/mobile-navigation';
import { ThemeToggle } from '@/components/theme-toggle';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

export function BrandLink({ className }: { className?: string }) {
  return (
    <Link
      aria-label="帧取首页"
      className={cn(
        'focus-ring inline-flex min-h-11 items-center gap-2.5 rounded-md text-[15px] font-semibold tracking-[-0.02em]',
        className,
      )}
      href="/"
    >
      <span className="flex size-6 items-center justify-center rounded-[4px] bg-primary text-primary-foreground">
        <DownloadSimpleIcon aria-hidden className="size-3.5" weight="bold" />
      </span>
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

  async function handleSignOut() {
    setSigningOut(true);
    await signOut();
    router.replace('/user/login');
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-40 bg-background">
      <div className="content-shell flex h-[72px] items-center justify-between">
        <BrandLink />
        <nav
          aria-label="主要导航"
          className="hidden items-center gap-1 sm:flex"
        >
          <Button
            asChild
            className={cn(
              'min-h-10 px-3 text-foreground',
              historyActive && 'bg-muted',
            )}
            variant="ghost"
          >
            <Link
              aria-current={historyActive ? 'page' : undefined}
              href="/history"
            >
              <ClockCounterClockwiseIcon aria-hidden className="size-[19px]" />
              <span>下载记录</span>
            </Link>
          </Button>
          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  aria-label="打开账户菜单"
                  className="min-h-10 px-2 text-foreground"
                  disabled={loading}
                  variant="ghost"
                >
                  <Avatar size="sm">
                    <AvatarFallback>
                      {user.username.slice(0, 1).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <CaretDownIcon
                    aria-hidden
                    className="hidden size-3.5 sm:block"
                  />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent aria-label="账户菜单" className="w-56">
                <DropdownMenuLabel>
                  <span className="block truncate font-medium text-foreground">
                    {user.username}
                  </span>
                  <span className="mt-0.5 block truncate normal-case">
                    {user.email}
                  </span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/account">
                    <UserCircleIcon aria-hidden className="size-4" />
                    个人资料
                  </Link>
                </DropdownMenuItem>
                {user.role === 'admin' ? (
                  <DropdownMenuItem asChild>
                    <Link href="/admin/users">
                      <UsersThreeIcon aria-hidden className="size-4" />
                      用户管理
                    </Link>
                  </DropdownMenuItem>
                ) : null}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  disabled={signingOut}
                  onSelect={() => void handleSignOut()}
                >
                  <SignOutIcon aria-hidden className="size-4" />
                  {signingOut ? '正在退出…' : '退出登录'}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button asChild className="min-h-10 px-3" variant="ghost">
              <Link
                href={`/user/login?redirect=${encodeURIComponent(pathname)}`}
              >
                <UserCircleIcon aria-hidden className="size-5" />
                <span>账户</span>
              </Link>
            </Button>
          )}
          <span aria-hidden className="mx-1 h-5 w-px bg-border" />
          <ThemeToggle />
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
