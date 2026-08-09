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
        'focus-ring inline-flex min-h-11 items-center gap-2.5 rounded-lg text-[21px] font-semibold tracking-[-0.03em]',
        className,
      )}
      href="/"
    >
      <span className="flex size-8 items-center justify-center rounded-[9px] bg-primary text-white">
        <DownloadSimpleIcon aria-hidden className="size-5" weight="bold" />
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
    <header className="relative z-40 bg-white">
      <div className="flex h-[68px] w-full items-center justify-between px-4 sm:px-7">
        <BrandLink />
        <nav aria-label="主要导航" className="flex items-center gap-1 sm:gap-2">
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
              <span className="hidden sm:inline">下载历史</span>
              <span className="sr-only sm:hidden">下载历史</span>
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
                  <UserCircleIcon aria-hidden className="size-5" />
                  <span className="hidden sm:inline">账户</span>
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
                <span className="hidden sm:inline">账户</span>
                <span className="sr-only sm:hidden">登录账户</span>
              </Link>
            </Button>
          )}
        </nav>
      </div>
    </header>
  );
}

export default SiteHeader;
