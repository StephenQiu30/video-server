'use client';

import { SpinnerGapIcon } from '@phosphor-icons/react';
import { usePathname, useRouter } from 'next/navigation';
import { type ReactNode, useEffect } from 'react';

import { useAuth } from '@/components/auth-provider';

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

  if (loading) return <RouteStatus label="正在恢复登录状态" />;
  if (!user || (requireAdmin && user.role !== 'admin')) {
    return <RouteStatus label="正在前往可访问页面" />;
  }

  return children;
}

function RouteStatus({ label }: { label: string }) {
  return (
    <div
      aria-live="polite"
      className="flex min-h-[60vh] items-center justify-center gap-2 text-sm text-muted-foreground"
      role="status"
    >
      <SpinnerGapIcon
        aria-hidden
        className="size-5 animate-spin text-primary motion-reduce:animate-none"
      />
      <span>{label}</span>
    </div>
  );
}

export default ProtectedRoute;
