'use client';

import dynamic from 'next/dynamic';

const ProAppShell = dynamic(() => import('@/components/pro-app-shell'), {
  ssr: false,
});

export default function AppShell({ children }: { children: React.ReactNode }) {
  return <ProAppShell>{children}</ProAppShell>;
}
