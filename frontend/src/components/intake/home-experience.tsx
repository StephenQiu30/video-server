'use client';

import type { ReactNode } from 'react';

import { useAuth } from '@/components/auth/auth-provider';
import { HomeStartup } from '@/components/intake/home-startup';
import { WorkspaceHome } from '@/components/intake/workspace-home';

type ResolvedHome = 'public' | 'workspace';

export function HomeExperience({ publicHome }: { publicHome: ReactNode }) {
  const { loading, user } = useAuth();
  const resolvedView: ResolvedHome | undefined = loading
    ? undefined
    : user
      ? 'workspace'
      : 'public';

  return (
    <div
      aria-busy={loading || undefined}
      className="relative flex min-h-[60vh] flex-1 flex-col"
      data-auth-pending={loading || undefined}
      data-home-phase={loading ? 'resolving' : 'ready'}
      data-slot="home-experience"
    >
      {resolvedView ? (
        <div data-home-view={resolvedView} data-slot="home-auth-content">
          {resolvedView === 'workspace' ? <WorkspaceHome /> : publicHome}
        </div>
      ) : (
        <HomeStartup />
      )}
    </div>
  );
}
