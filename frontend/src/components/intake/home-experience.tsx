'use client';

import type { ReactNode } from 'react';

import { useAuth } from '@/components/auth/auth-provider';
import DownloadWorkspace from '@/components/intake/download-workspace';
import { Spinner } from '@/components/ui/spinner';

export function HomeExperience({ publicHome }: { publicHome: ReactNode }) {
  const { loading, user } = useAuth();
  const authPending = loading;

  return (
    <div
      aria-busy={authPending || undefined}
      className="relative"
      data-auth-pending={authPending || undefined}
      data-slot="home-experience"
    >
      {authPending ? (
        <div
          aria-live="polite"
          className="absolute inset-x-0 top-0 z-10 flex min-h-[60vh] items-center justify-center gap-2 text-sm text-muted-foreground"
          data-slot="home-auth-pending"
          role="status"
        >
          <Spinner
            aria-hidden
            className="size-5 text-primary"
            role="presentation"
          />
          <span>正在恢复登录状态</span>
        </div>
      ) : null}
      <div
        aria-hidden={authPending || undefined}
        className={authPending ? 'invisible' : undefined}
        data-slot="home-auth-content"
      >
        {user ? <DownloadWorkspace /> : publicHome}
      </div>
    </div>
  );
}
