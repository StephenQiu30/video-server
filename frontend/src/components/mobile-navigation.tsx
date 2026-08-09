'use client';

import {
  ClockCounterClockwiseIcon,
  LinkSimpleIcon,
  ListIcon,
  SignOutIcon,
  UserCircleIcon,
  UsersThreeIcon,
} from '@phosphor-icons/react';
import Link from 'next/link';
import { useState } from 'react';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Sheet,
  SheetContent,
  SheetDescription,
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
  const [open, setOpen] = useState(false);

  async function signOut() {
    setOpen(false);
    await onSignOut();
  }

  return (
    <Sheet onOpenChange={setOpen} open={open}>
      <SheetTrigger asChild>
        <Button
          aria-label="打开导航菜单"
          className="size-11 sm:hidden"
          disabled={loading}
          size="icon"
          variant="ghost"
        >
          <ListIcon aria-hidden className="size-5" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-[min(88vw,360px)] bg-card" side="right">
        <SheetHeader className="border-b px-5 py-5">
          <SheetTitle>导航</SheetTitle>
          <SheetDescription>
            访问视频解析、下载任务与账户设置。
          </SheetDescription>
        </SheetHeader>
        {user ? (
          <div className="flex items-center gap-3 px-5 py-4">
            <Avatar size="lg">
              <AvatarFallback className="bg-accent text-accent-foreground">
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
          <MobileLink
            active={pathname === '/'}
            href="/"
            onNavigate={() => setOpen(false)}
          >
            <LinkSimpleIcon aria-hidden />
            视频解析
          </MobileLink>
          <MobileLink
            active={pathname.startsWith('/history')}
            href="/history"
            onNavigate={() => setOpen(false)}
          >
            <ClockCounterClockwiseIcon aria-hidden />
            下载历史
          </MobileLink>
          {user ? (
            <>
              <MobileLink href="/account" onNavigate={() => setOpen(false)}>
                <UserCircleIcon aria-hidden />
                个人资料
              </MobileLink>
              {user.role === 'admin' ? (
                <MobileLink
                  href="/admin/users"
                  onNavigate={() => setOpen(false)}
                >
                  <UsersThreeIcon aria-hidden />
                  用户管理
                </MobileLink>
              ) : null}
            </>
          ) : (
            <MobileLink
              href={`/user/login?redirect=${encodeURIComponent(pathname)}`}
              onNavigate={() => setOpen(false)}
            >
              <UserCircleIcon aria-hidden />
              登录账户
            </MobileLink>
          )}
        </nav>
        {user ? (
          <div className="mt-auto px-3 pb-4">
            <Separator className="mb-3" />
            <Button
              className="w-full justify-start text-destructive hover:text-destructive"
              disabled={signingOut}
              onClick={() => void signOut()}
              variant="ghost"
            >
              <SignOutIcon aria-hidden />
              {signingOut ? '正在退出…' : '退出登录'}
            </Button>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

function MobileLink({
  active = false,
  children,
  href,
  onNavigate,
}: {
  active?: boolean;
  children: React.ReactNode;
  href: string;
  onNavigate: () => void;
}) {
  return (
    <Button
      asChild
      className={cn(
        'h-11 justify-start',
        active && 'bg-accent text-accent-foreground',
      )}
      variant="ghost"
    >
      <Link
        aria-current={active ? 'page' : undefined}
        href={href}
        onClick={onNavigate}
      >
        {children}
      </Link>
    </Button>
  );
}
