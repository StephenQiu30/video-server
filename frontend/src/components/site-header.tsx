'use client';

import {
  CaretDownIcon,
  ClockCounterClockwiseIcon,
  DownloadSimpleIcon,
  LinkSimpleIcon,
  SignOutIcon,
  UserCircleIcon,
  UsersThreeIcon,
} from '@phosphor-icons/react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

import { useAuth } from '@/components/auth-provider';
import { MobileNavigation } from '@/components/mobile-navigation';
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
        'focus-ring inline-flex min-h-11 items-center gap-2.5 rounded-lg text-[19px] font-semibold tracking-[-0.03em]',
        className,
      )}
      href="/"
    >
      <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-white">
        <DownloadSimpleIcon aria-hidden className="size-[18px]" weight="bold" />
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
  const parserActive = pathname === '/';
  const historyActive = pathname.startsWith('/history');

  async function handleSignOut() {
    setSigningOut(true);
    await signOut();
    router.replace('/user/login');
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/85">
      <div className="page-shell flex h-14 items-center justify-between sm:h-16">
        <BrandLink />
        <nav
          aria-label="主要导航"
          className="hidden items-center gap-1 sm:flex"
        >
          <Button
            asChild
            className={cn(
              'min-h-11 px-2.5 text-muted-foreground sm:px-3.5',
              parserActive && 'bg-accent text-accent-foreground',
            )}
            variant="ghost"
          >
            <Link aria-current={parserActive ? 'page' : undefined} href="/">
              <LinkSimpleIcon aria-hidden className="size-[19px]" />
              <span>视频解析</span>
            </Link>
          </Button>
          <Button
            asChild
            className={cn(
              'min-h-11 px-2.5 text-muted-foreground sm:px-3.5',
              historyActive && 'bg-accent text-accent-foreground',
            )}
            variant="ghost"
          >
            <Link
              aria-current={historyActive ? 'page' : undefined}
              href="/history"
            >
              <ClockCounterClockwiseIcon aria-hidden className="size-[19px]" />
              <span>下载历史</span>
            </Link>
          </Button>
          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  aria-label="打开账户菜单"
                  className="min-h-11 px-2.5 text-muted-foreground sm:px-3.5"
                  disabled={loading}
                  variant="ghost"
                >
                  <Avatar size="sm">
                    <AvatarFallback>
                      {user.username.slice(0, 1).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <span>账户</span>
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
            <Button asChild className="min-h-11 px-3" variant="ghost">
              <Link
                href={`/user/login?redirect=${encodeURIComponent(pathname)}`}
              >
                <UserCircleIcon aria-hidden className="size-5" />
                <span>账户</span>
              </Link>
            </Button>
          )}
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
