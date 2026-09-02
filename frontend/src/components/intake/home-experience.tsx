'use client';

import { type ReactNode, useEffect, useRef, useState } from 'react';

import { useAuth } from '@/components/auth/auth-provider';
import DownloadWorkspace from '@/components/intake/download-workspace';
import { HomeStartup } from '@/components/intake/home-startup';
import { useGSAP } from '@/lib/gsap-client';
import {
  createHomeResolutionTimeline,
  createSessionRestoreTimeline,
} from '@/lib/home-transition-motion';

type ResolvedHome = 'public' | 'workspace';

export function HomeExperience({ publicHome }: { publicHome: ReactNode }) {
  const { loading, user } = useAuth();
  const rootRef = useRef<HTMLDivElement>(null);
  const targetView: ResolvedHome | undefined = loading
    ? undefined
    : user
      ? 'workspace'
      : 'public';
  const [resolvedView, setResolvedView] = useState<ResolvedHome>();
  const [transitioning, setTransitioning] = useState(true);

  useEffect(() => {
    if (!targetView || targetView === resolvedView) return;
    setTransitioning(true);
    setResolvedView(targetView);
  }, [resolvedView, targetView]);

  useGSAP(
    () => {
      const root = rootRef.current;
      if (!root) return;

      if (!resolvedView) return createSessionRestoreTimeline(root);

      return createHomeResolutionTimeline(root, () => {
        setTransitioning(false);
      });
    },
    {
      dependencies: [resolvedView],
      revertOnUpdate: true,
      scope: rootRef,
    },
  );

  const authPending = resolvedView === undefined;
  const busy = authPending || transitioning;

  return (
    <div
      aria-busy={busy || undefined}
      className="relative flex min-h-[60vh] flex-1 flex-col"
      data-auth-pending={authPending || undefined}
      data-home-phase={
        authPending ? 'resolving' : transitioning ? 'entering' : 'ready'
      }
      data-slot="home-experience"
      ref={rootRef}
    >
      {transitioning ? <HomeStartup /> : null}
      {resolvedView ? (
        <div
          aria-hidden={transitioning || undefined}
          data-home-view={resolvedView}
          data-slot="home-auth-content"
          inert={transitioning || undefined}
        >
          {resolvedView === 'workspace' ? <DownloadWorkspace /> : publicHome}
        </div>
      ) : null}
    </div>
  );
}
