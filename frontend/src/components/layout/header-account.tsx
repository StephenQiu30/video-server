'use client';

import {
  CaretDownIcon,
  ChartLineUpIcon,
  HardDrivesIcon,
  RobotIcon,
  SignOutIcon,
  StackIcon,
  UserCircleIcon,
  UsersThreeIcon,
} from '@phosphor-icons/react';
import Link from 'next/link';

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
import { Skeleton } from '@/components/ui/skeleton';
import type { AuthUser } from '@/services/auth';

type HeaderAccountProps = {
  analyticsActive: boolean;
  aiProvidersActive: boolean;
  catalogActive: boolean;
  filesActive: boolean;
  loading: boolean;
  onSignOut: () => void;
  pathname: string;
  signingOut: boolean;
  user?: AuthUser;
  usersActive: boolean;
};

export function HeaderAccount({
  analyticsActive,
  aiProvidersActive,
  catalogActive,
  filesActive,
  loading,
  onSignOut,
  pathname,
  signingOut,
  user,
  usersActive,
}: HeaderAccountProps) {
  return (
    <div
      className="flex w-[88px] shrink-0 items-center justify-end"
      data-slot="header-account"
    >
      {loading ? (
        <Skeleton aria-hidden className="h-11 w-[74px]" />
      ) : user ? (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              aria-label="打开账户菜单"
              className="min-h-11 w-[74px] px-2.5 text-foreground"
              variant="ghost"
            >
              <Avatar>
                <AvatarFallback>
                  {user.username.slice(0, 1).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <CaretDownIcon aria-hidden className="size-4" />
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
              <>
                <DropdownMenuItem asChild>
                  <Link
                    aria-current={filesActive ? 'page' : undefined}
                    href="/admin/files"
                  >
                    <HardDrivesIcon aria-hidden className="size-4" />
                    文件管理
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link
                    aria-current={aiProvidersActive ? 'page' : undefined}
                    href="/admin/ai-providers"
                  >
                    <RobotIcon aria-hidden className="size-4" />
                    AI 服务
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link
                    aria-current={analyticsActive ? 'page' : undefined}
                    href="/admin/analytics"
                  >
                    <ChartLineUpIcon aria-hidden className="size-4" />
                    下载分析
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link
                    aria-current={catalogActive ? 'page' : undefined}
                    href="/admin/providers"
                  >
                    <StackIcon aria-hidden className="size-4" />
                    平台目录
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link
                    aria-current={usersActive ? 'page' : undefined}
                    href="/admin/users"
                  >
                    <UsersThreeIcon aria-hidden className="size-4" />
                    用户管理
                  </Link>
                </DropdownMenuItem>
              </>
            ) : null}
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled={signingOut} onSelect={onSignOut}>
              <SignOutIcon aria-hidden className="size-4" />
              {signingOut ? '正在退出…' : '退出登录'}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ) : (
        <Button
          asChild
          className="min-h-11 w-full px-3.5 text-[15px]"
          variant="ghost"
        >
          <Link href={`/user/login?redirect=${encodeURIComponent(pathname)}`}>
            <UserCircleIcon aria-hidden className="size-[21px]" />
            <span>账户</span>
          </Link>
        </Button>
      )}
    </div>
  );
}
