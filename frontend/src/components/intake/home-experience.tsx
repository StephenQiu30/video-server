'use client';

import type { ReactNode } from 'react';

import { useAuth } from '@/components/auth/auth-provider';
import DownloadWorkspace from '@/components/intake/download-workspace';

export function HomeExperience({ publicHome }: { publicHome: ReactNode }) {
  const { user } = useAuth();

  if (user) return <DownloadWorkspace />;

  return publicHome;
}
