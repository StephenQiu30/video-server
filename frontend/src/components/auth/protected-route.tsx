'use client';

import { usePathname, useRouter } from 'next/navigation';
import { type ReactNode, useEffect } from 'react';

import { useAuth } from '@/components/auth/auth-provider';
import { RouteLoading } from '@/components/layout/route-loading';

type ProtectedRouteProps = {
  children: ReactNode;
  requireAdmin?: boolean;
};

export function ProtectedRoute({
  children,
  requireAdmin = false,
}: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;

    if (!user) {
      const currentPath = `${pathname ?? '/'}${window.location.search}`;
      router.replace(`/user/login?redirect=${encodeURIComponent(currentPath)}`);
      return;
    }

    if (requireAdmin && user.role !== 'admin') router.replace('/');
  }, [loading, pathname, requireAdmin, router, user]);

  if (loading) return <RouteLoading label="正在恢复登录状态" />;
  if (!user || (requireAdmin && user.role !== 'admin')) {
    return <RouteLoading label="正在前往可访问页面" />;
  }

  return children;
}

export default ProtectedRoute;
