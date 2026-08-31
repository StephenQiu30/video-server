import {
  ChartLineUpIcon,
  ClockCounterClockwiseIcon,
  FileTextIcon,
  HardDrivesIcon,
  HouseIcon,
  PulseIcon,
  RobotIcon,
  StackIcon,
  UserCircleIcon,
  UsersThreeIcon,
} from '@phosphor-icons/react';

import { MobileNavigationLink as MobileLink } from '@/components/layout/mobile-navigation-link';
import { NavigationMenuList } from '@/components/ui/navigation-menu';
import type { AuthUser } from '@/services/auth';

export function MobileNavigationItems({
  pathname,
  user,
}: {
  pathname: string;
  user?: AuthUser;
}) {
  return (
    <NavigationMenuList className="grid w-full flex-none justify-stretch gap-1">
      <MobileLink active={pathname === '/'} href="/">
        <HouseIcon aria-hidden />
        首页
      </MobileLink>
      <MobileLink active={pathname.startsWith('/history')} href="/history">
        <ClockCounterClockwiseIcon aria-hidden />
        下载记录
      </MobileLink>
      <MobileLink active={pathname.startsWith('/documents')} href="/documents">
        <FileTextIcon aria-hidden />
        剧本文档
      </MobileLink>
      <MobileLink active={pathname.startsWith('/providers')} href="/providers">
        <PulseIcon aria-hidden />
        平台状态
      </MobileLink>
      {user ? (
        <>
          <MobileLink active={pathname.startsWith('/account')} href="/account">
            <UserCircleIcon aria-hidden />
            个人资料
          </MobileLink>
          {user.role === 'admin' ? (
            <>
              <MobileLink
                active={pathname.startsWith('/admin/ai-providers')}
                href="/admin/ai-providers"
              >
                <RobotIcon aria-hidden />
                AI 服务
              </MobileLink>
              <MobileLink
                active={pathname.startsWith('/admin/analytics')}
                href="/admin/analytics"
              >
                <ChartLineUpIcon aria-hidden />
                下载分析
              </MobileLink>
              <MobileLink
                active={pathname.startsWith('/admin/files')}
                href="/admin/files"
              >
                <HardDrivesIcon aria-hidden />
                文件管理
              </MobileLink>
              <MobileLink
                active={pathname.startsWith('/admin/providers')}
                href="/admin/providers"
              >
                <StackIcon aria-hidden />
                平台目录
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
    </NavigationMenuList>
  );
}
