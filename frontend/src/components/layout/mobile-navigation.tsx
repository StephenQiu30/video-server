'use client';

import { ListIcon, SignOutIcon } from '@phosphor-icons/react';
import { useRef } from 'react';

import { MobileNavigationItems } from '@/components/layout/mobile-navigation-items';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { NavigationMenu } from '@/components/ui/navigation-menu';
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
import { Spinner } from '@/components/ui/spinner';

type MobileNavigationProps = {
  loading: boolean;
  onSignOut: () => Promise<void>;
  pathname: string;
  signingOut: boolean;
  user?: API.UserResponse;
};

export function MobileNavigation({
  loading,
  onSignOut,
  pathname,
  signingOut,
  user,
}: MobileNavigationProps) {
  const navigationTitleRef = useRef<HTMLHeadingElement>(null);

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
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          navigationTitleRef.current?.focus();
        }}
        side="right"
      >
        <SheetHeader>
          <SheetTitle ref={navigationTitleRef} tabIndex={-1}>
            导航
          </SheetTitle>
          <SheetDescription>
            从首页导入内容，或查看解析记录、下载记录与其他工作区内容。
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
        <NavigationMenu
          aria-label="移动导航"
          className="block max-w-none flex-none px-3"
          orientation="vertical"
          viewport={false}
        >
          <MobileNavigationItems pathname={pathname} user={user} />
        </NavigationMenu>
        {user ? (
          <SheetFooter>
            <SheetClose asChild>
              <Button
                className="w-full justify-start text-destructive hover:text-destructive"
                disabled={signingOut}
                onClick={() => void onSignOut()}
                variant="ghost"
              >
                {signingOut ? (
                  <Spinner aria-hidden data-icon="inline-start" />
                ) : (
                  <SignOutIcon aria-hidden data-icon="inline-start" />
                )}
                {signingOut ? '正在退出…' : '退出登录'}
              </Button>
            </SheetClose>
          </SheetFooter>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
