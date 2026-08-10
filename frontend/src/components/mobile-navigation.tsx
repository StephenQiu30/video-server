'use client';

import {
  ChartLineUpIcon,
  ClockCounterClockwiseIcon,
  LinkSimpleIcon,
  ListIcon,
  PulseIcon,
  SignOutIcon,
  UserCircleIcon,
  UsersThreeIcon,
} from '@phosphor-icons/react';
import Link from 'next/link';

import { ThemeToggle } from '@/components/theme-toggle';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { cn } from '@/lib/utils';
import type { AuthUser } from '@/services/auth';

type MobileNavigationProps = {
  loading: boolean;
  onSignOut: () => Promise<void>;
  pathname: string;
  signingOut: boolean;
  user?: AuthUser;
};

export function MobileNavigation({
  loading,
  onSignOut,
  pathname,
  signingOut,
  user,
}: MobileNavigationProps) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          aria-label="打开导航菜单"
          className="size-11 lg:hidden"
          disabled={loading}
          size="icon"
          variant="ghost"
        >
          <ListIcon aria-hidden className="size-5" />
        </Button>
      </SheetTrigger>
      <SheetContent
        className="w-[min(88vw,360px)] overflow-y-auto overscroll-contain"
        side="right"
      >
        <SheetHeader>
          <SheetTitle>导航</SheetTitle>
          <SheetDescription>
            访问视频解析、下载任务与账户设置。
          </SheetDescription>
        </SheetHeader>
        {user ? (
          <div className="flex items-center gap-3 px-5 py-4">
            <Avatar size="lg">
              <AvatarFallback className="bg-muted text-foreground">
                {user.username.slice(0, 1).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="truncate font-medium">{user.username}</p>
              <p className="truncate text-xs text-muted-foreground">
                {user.email}
              </p>
            </div>
          </div>
        ) : null}
        <nav aria-label="移动导航" className="grid gap-1 px-3">
          <MobileLink active={pathname === '/'} href="/">
            <LinkSimpleIcon aria-hidden />
            视频解析
          </MobileLink>
          <MobileLink active={pathname.startsWith('/history')} href="/history">
            <ClockCounterClockwiseIcon aria-hidden />
            下载记录
          </MobileLink>
          <MobileLink
            active={pathname.startsWith('/providers')}
            href="/providers"
          >
            <PulseIcon aria-hidden />
            平台状态
          </MobileLink>
          {user ? (
            <>
              <MobileLink
                active={pathname.startsWith('/account')}
                href="/account"
              >
                <UserCircleIcon aria-hidden />
                个人资料
              </MobileLink>
              {user.role === 'admin' ? (
                <>
                  <MobileLink
                    active={pathname.startsWith('/admin/analytics')}
                    href="/admin/analytics"
                  >
                    <ChartLineUpIcon aria-hidden />
                    下载分析
                  </MobileLink>
                  <MobileLink
                    active={pathname.startsWith('/admin/users')}
                    href="/admin/users"
                  >
                    <UsersThreeIcon aria-hidden />
                    用户管理
                  </MobileLink>
                </>
              ) : null}
            </>
          ) : (
            <MobileLink
              href={`/user/login?redirect=${encodeURIComponent(pathname)}`}
            >
              <UserCircleIcon aria-hidden />
              登录账户
            </MobileLink>
          )}
        </nav>
        <div className="mt-2 flex items-center justify-between px-5 py-3">
          <span className="text-sm text-muted-foreground">外观</span>
          <ThemeToggle />
        </div>
        {user ? (
          <SheetFooter>
            <Separator />
            <SheetClose asChild>
              <Button
                className="w-full justify-start text-destructive hover:text-destructive"
                disabled={signingOut}
                onClick={() => void onSignOut()}
                variant="ghost"
              >
                <SignOutIcon aria-hidden />
                {signingOut ? '正在退出…' : '退出登录'}
              </Button>
            </SheetClose>
          </SheetFooter>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

function MobileLink({
  active = false,
  children,
  href,
}: {
  active?: boolean;
  children: React.ReactNode;
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
